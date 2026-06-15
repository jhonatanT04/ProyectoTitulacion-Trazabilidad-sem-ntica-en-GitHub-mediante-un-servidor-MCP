"""
Test — Scraping e indexación persistente de documentación.
Prueba: estrategias de recuperación del scraper (Markdown directo, llms.txt,
sitemap+trafilatura), las tools MCP (index_docs, search_docs, list_indexed_docs)
y la persistencia del índice en disco.
"""
import asyncio
import shutil
from pathlib import Path

# --- Aislar la persistencia en una carpeta de prueba ANTES de usar el store ---
import ServidorMCP.indexer.store as store

TEST_INDEX_DIR = "test/.docs_index_test"
store.INDEX_DIR = TEST_INDEX_DIR

import httpx

from ServidorMCP.connectors.scraper import (
    HEADERS,
    _discover_from_sitemap,
    _extract_markdown,
    _is_markdown_source,
    _same_scope,
    scrape_library,
)
from ServidorMCP.tools.docs import index_docs, list_indexed_docs, search_docs

# Fuentes de prueba
MD_DIRECT = "https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md"
LLMS_SITE = "https://mcp-framework.com/docs/"   # publica llms-full.txt
HTML_SITE = "https://www.attrs.org/en/stable/"  # docs HTML con sitemap.xml


def separador(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


def test_helpers():
    """Verifica las utilidades puras del scraper (sin red)."""
    separador("TEST 1 — Utilidades del scraper (detección de fuentes y scope)")

    assert _is_markdown_source("docs/guia.md")
    assert _is_markdown_source(MD_DIRECT)
    assert _is_markdown_source("https://x.com/llms-full.txt")
    assert not _is_markdown_source("https://www.attrs.org/en/stable/")

    base = "https://www.attrs.org/en/stable/"
    assert _same_scope("https://www.attrs.org/en/stable/api.html", base)
    assert not _same_scope("https://otro.com/en/stable/api.html", base)
    assert not _same_scope("https://www.attrs.org/en/24.0/api.html", base)

    print("  _is_markdown_source y _same_scope se comportan correctamente")
    print("\n  OK — Utilidades del scraper válidas")


async def test_markdown_directo():
    """Estrategia 1: fuente Markdown directa (raw de GitHub), sin parseo HTML."""
    separador("TEST 2 — Scraping de fuente Markdown directa")
    pages = await scrape_library(MD_DIRECT)

    assert isinstance(pages, list) and len(pages) == 1
    assert pages[0]["url"] == MD_DIRECT
    assert len(pages[0]["markdown"]) > 200

    print(f"  Fuente: {MD_DIRECT}")
    print(f"  Páginas: {len(pages)} | chars: {len(pages[0]['markdown'])}")
    print("\n  OK — Markdown directo recuperado sin extracción HTML")


async def test_llms_txt():
    """Estrategia 2: atajo llms-full.txt / llms.txt en la raíz del sitio."""
    separador("TEST 3 — Atajo llms.txt")
    pages = await scrape_library(LLMS_SITE, max_pages=5)

    assert len(pages) >= 1
    assert "llms" in pages[0]["url"].lower()
    assert len(pages[0]["markdown"]) > 1000

    print(f"  Sitio: {LLMS_SITE}")
    print(f"  Detectado: {pages[0]['url']} | chars: {len(pages[0]['markdown'])}")
    print("\n  OK — llms.txt detectado y usado como atajo")


async def test_sitemap_y_extraccion():
    """Estrategia 3: descubrimiento por sitemap + extracción HTML con trafilatura."""
    separador("TEST 4 — Sitemap + extracción HTML (trafilatura)")
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as c:
        urls = await _discover_from_sitemap(c, HTML_SITE)
        assert len(urls) >= 1, "El sitemap debería aportar al menos una URL en scope"

        resp = await c.get(urls[0])
        md = _extract_markdown(resp.text)
        assert md and len(md) > 200, "trafilatura debe extraer contenido en Markdown"

    print(f"  Sitio: {HTML_SITE}")
    print(f"  URLs en scope (sitemap): {len(urls)}")
    print(f"  Extraído de {urls[0]}: {len(md)} chars de Markdown")
    print("\n  OK — Sitemap + trafilatura funcionan")


async def test_index_docs_y_persistencia():
    """Tool index_docs: scrapea, fragmenta, indexa y persiste en disco."""
    separador("TEST 5 — index_docs (indexado + persistencia)")
    import json

    result = json.loads(await index_docs(MD_DIRECT, max_pages=5))
    assert result.get("status") == "indexado", f"index_docs falló: {result}"
    assert result["fragments"] > 0
    assert result["pages"] >= 1

    # Verificar archivos persistidos en disco
    pkl = list(Path(TEST_INDEX_DIR).glob("*.pkl"))
    js = list(Path(TEST_INDEX_DIR).glob("*.json"))
    assert len(pkl) == 1 and len(js) == 1, "Deben existir un .pkl y un .json"

    print(f"  Slug: {result['slug']}")
    print(f"  Páginas: {result['pages']} | Fragmentos: {result['fragments']}")
    print(f"  Persistido: {pkl[0].name} + {js[0].name}")
    print("\n  OK — index_docs indexó y persistió correctamente")


async def test_search_docs():
    """Tool search_docs: consulta el índice persistido (sin re-scrapear)."""
    separador("TEST 6 — search_docs sobre índice persistido")
    import json

    results = json.loads(await search_docs(MD_DIRECT, "installation", top_k=3))
    assert isinstance(results, list)

    print(f"  Query: 'installation' → {len(results)} resultado(s)")
    for r in results:
        print(f"    [{r['score']:.4f}] {r['section_path']}")

    # Búsqueda sobre librería no indexada → error controlado
    err = json.loads(await search_docs("https://no-indexada.example", "x"))
    assert "error" in err, "Debe avisar si la librería no está indexada"
    print("  Librería no indexada → error controlado OK")

    print("\n  OK — search_docs consulta el índice persistido")


async def test_list_indexed_docs():
    """Tool list_indexed_docs: lista las librerías indexadas."""
    separador("TEST 7 — list_indexed_docs")
    import json

    items = json.loads(await list_indexed_docs())
    assert isinstance(items, list) and len(items) >= 1
    assert any(it["library"] == MD_DIRECT for it in items)

    print(f"  Librerías indexadas: {len(items)}")
    for it in items:
        print(f"    - {it['slug']} ({it['fragments']} frags, {it['pages']} págs)")

    print("\n  OK — list_indexed_docs reporta lo indexado")


async def main():
    print("\nINICIANDO TESTS — Scraping e indexación persistente")

    # Limpiar estado previo del directorio de prueba
    shutil.rmtree(TEST_INDEX_DIR, ignore_errors=True)

    passed = 0
    failed = 0

    sync_tests = [("Utilidades", test_helpers)]
    async_tests = [
        ("Markdown directo", test_markdown_directo),
        ("llms.txt", test_llms_txt),
        ("Sitemap + trafilatura", test_sitemap_y_extraccion),
        ("index_docs", test_index_docs_y_persistencia),
        ("search_docs", test_search_docs),
        ("list_indexed_docs", test_list_indexed_docs),
    ]

    for nombre, test in sync_tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n  FALLO en '{nombre}' — {e}")
            failed += 1

    for nombre, test in async_tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n  FALLO en '{nombre}' — {e}")
            failed += 1

    # Limpieza del directorio de prueba
    shutil.rmtree(TEST_INDEX_DIR, ignore_errors=True)

    print(f"\n{'='*60}")
    print(f"  RESULTADO: {passed} pasados / {failed} fallidos")
    print(f"{'='*60}\n")


asyncio.run(main())
