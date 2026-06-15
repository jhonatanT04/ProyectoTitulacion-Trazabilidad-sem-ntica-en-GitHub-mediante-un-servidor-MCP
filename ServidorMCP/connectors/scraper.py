"""
Conector de scraping de documentación de librerías.

Estrategia de recuperación (de más fácil a más costosa):
  1. Fuente Markdown directa (.md/.txt o raw.githubusercontent.com / llms.txt).
  2. `llms-full.txt` / `llms.txt` en la raíz del sitio (Markdown ya listo para LLMs).
  3. `sitemap.xml` para descubrir todas las páginas sin crawlear enlaces.
  4. Crawler BFS limitado al mismo dominio/subruta como último recurso.

El contenido HTML se reduce a su contenido principal con trafilatura y se
convierte a Markdown, de modo que reutiliza `fragment_markdown` aguas abajo.
"""
import asyncio
import re
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura

from ServerMCP.config import (
    SCRAPE_CONCURRENCY,
    SCRAPE_DELAY,
    SCRAPE_MAX_PAGES,
    SCRAPER_USER_AGENT,
)

HEADERS = {"User-Agent": SCRAPER_USER_AGENT}


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _is_markdown_source(source: str) -> bool:
    """True si la fuente ya es Markdown/texto plano y no requiere extracción HTML."""
    low = source.lower()
    return (
        low.endswith((".md", ".markdown", ".txt"))
        or "raw.githubusercontent.com" in low
        or low.rstrip("/").endswith(("llms.txt", "llms-full.txt"))
    )


def _same_scope(url: str, base: str) -> bool:
    """True si `url` pertenece al mismo dominio y cuelga de la ruta base."""
    u, b = urlparse(url), urlparse(base)
    if u.netloc != b.netloc:
        return False
    base_path = b.path.rsplit("/", 1)[0] or "/"
    return u.path.startswith(base_path)


def _looks_like_page(url: str) -> bool:
    """Descarta recursos que no son páginas de documentación (assets, binarios)."""
    bad = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js",
           ".pdf", ".zip", ".ico", ".woff", ".woff2")
    return not url.lower().split("?")[0].endswith(bad)


# --------------------------------------------------------------------------- #
# Robots.txt
# --------------------------------------------------------------------------- #
async def _load_robots(client: httpx.AsyncClient, base: str) -> RobotFileParser:
    """Carga robots.txt del sitio (best-effort). Si no existe, permite todo."""
    rp = RobotFileParser()
    robots_url = urljoin(base, "/robots.txt")
    try:
        resp = await client.get(robots_url)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            rp.allow_all = True
    except httpx.HTTPError:
        rp.allow_all = True
    return rp


def _allowed(rp: RobotFileParser, url: str) -> bool:
    try:
        return rp.can_fetch(SCRAPER_USER_AGENT, url)
    except Exception:
        return True


# --------------------------------------------------------------------------- #
# Descubrimiento de URLs
# --------------------------------------------------------------------------- #
async def _fetch_text(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await client.get(url)
        if resp.status_code == 200 and resp.text.strip():
            return resp.text
    except httpx.HTTPError:
        return None
    return None


async def _try_llms_txt(client: httpx.AsyncClient, base: str) -> str | None:
    """Intenta el atajo llms-full.txt / llms.txt en la raíz del sitio."""
    root = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    for name in ("llms-full.txt", "llms.txt"):
        text = await _fetch_text(client, urljoin(root + "/", name))
        if text and len(text) > 200:
            return text
    return None


async def _discover_from_sitemap(client: httpx.AsyncClient, base: str) -> list[str]:
    """Descubre URLs a partir de sitemap.xml (soporta sitemap-index anidado)."""
    root = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    xml = await _fetch_text(client, urljoin(root + "/", "sitemap.xml"))
    if not xml:
        return []

    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    # Si es un índice de sitemaps, expandir un nivel.
    if any(loc.endswith(".xml") for loc in locs):
        expanded: list[str] = []
        for sm in locs:
            if sm.endswith(".xml"):
                sub = await _fetch_text(client, sm)
                if sub:
                    expanded += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sub)
            else:
                expanded.append(sm)
        locs = expanded

    return [u for u in dict.fromkeys(locs)
            if _same_scope(u, base) and _looks_like_page(u)]


async def _crawl(client: httpx.AsyncClient, base: str, rp: RobotFileParser,
                 max_pages: int) -> dict[str, str]:
    """Crawler BFS de respaldo. Devuelve {url: html} del mismo dominio/subruta."""
    from bs4 import BeautifulSoup

    seen: set[str] = set()
    pages: dict[str, str] = {}
    queue: list[str] = [base]

    while queue and len(pages) < max_pages:
        url = urldefrag(queue.pop(0)).url
        if url in seen or not _allowed(rp, url):
            continue
        seen.add(url)

        html = await _fetch_text(client, url)
        await asyncio.sleep(SCRAPE_DELAY)
        if not html:
            continue
        pages[url] = html

        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            link = urldefrag(urljoin(url, a["href"])).url
            if (link not in seen and _same_scope(link, base)
                    and _looks_like_page(link)):
                queue.append(link)

    return pages


# --------------------------------------------------------------------------- #
# Extracción
# --------------------------------------------------------------------------- #
def _extract_markdown(html: str) -> str | None:
    """Reduce el HTML a su contenido principal y lo devuelve como Markdown."""
    md = trafilatura.extract(
        html,
        output_format="markdown",
        include_tables=True,
        include_links=False,
        include_comments=False,
        favor_recall=True,
    )
    return md.strip() if md and md.strip() else None


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #
async def scrape_library(source: str, max_pages: int | None = None) -> list[dict]:
    """
    Recupera la documentación de una librería y la devuelve como páginas Markdown.

    Args:
        source: URL base del sitio de docs, archivo .md/.txt o raw de GitHub.
        max_pages: Tope de páginas (default: SCRAPE_MAX_PAGES de config).

    Returns:
        Lista de {"url": str, "markdown": str}.
    """
    max_pages = max_pages or SCRAPE_MAX_PAGES

    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=30
    ) as client:
        # 1. Fuente Markdown directa: sin scraping HTML.
        if _is_markdown_source(source):
            text = await _fetch_text(client, source)
            return [{"url": source, "markdown": text}] if text else []

        # 2. Atajo llms.txt.
        llms = await _try_llms_txt(client, source)
        if llms:
            root = f"{urlparse(source).scheme}://{urlparse(source).netloc}"
            return [{"url": urljoin(root + "/", "llms-full.txt"), "markdown": llms}]

        # 3 + cortesía: respetar robots.txt.
        rp = await _load_robots(client, source)

        # 3. Sitemap.
        urls = await _discover_from_sitemap(client, source)
        urls = [u for u in urls if _allowed(rp, u)][:max_pages]

        if urls:
            sem = asyncio.Semaphore(SCRAPE_CONCURRENCY)

            async def _grab(u: str) -> dict | None:
                async with sem:
                    html = await _fetch_text(client, u)
                    await asyncio.sleep(SCRAPE_DELAY)
                if not html:
                    return None
                md = _extract_markdown(html)
                return {"url": u, "markdown": md} if md else None

            results = await asyncio.gather(*[_grab(u) for u in urls])
            return [r for r in results if r]

        # 4. Crawler BFS de respaldo.
        raw_pages = await _crawl(client, source, rp, max_pages)
        pages: list[dict] = []
        for url, html in raw_pages.items():
            md = _extract_markdown(html)
            if md:
                pages.append({"url": url, "markdown": md})
        return pages
