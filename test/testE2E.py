"""
Test Sprint 4 — Integración end-to-end con protocolo MCP real

Recorre las 6 herramientas del servidor a través del protocolo MCP (JSON-RPC 2.0
sobre stdio), tal como las invocaría un IDE. Cada tool se prueba de forma
explícita y el resultado se agrega por objetivo específico de la tesis:

  OE1 — Conector GitHub:        get_commits, get_pull_requests
  OE2 — Documentación Markdown: index_docs, search_docs, list_indexed_docs
  OE3 — Interfaz MCP:           inicialización, listado de tools, protocolo
  OE4 — Integración semántica:  explain_commit
"""
import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# `REPO` acepta tanto un slug de GitHub 'owner/repo' como una ruta local a un
# clon git (ej: "/home/user/proyecto"). El servidor autodetecta la fuente.
REPO  = "anthropics/anthropic-sdk-python"
SHA   = "49c5395"
DOC   = "https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/CONTRIBUTING.md"

# Las 6 tools que el servidor debe exponer al IDE.
TOOLS_ESPERADAS = {
    "get_commits",
    "get_pull_requests",
    "index_docs",
    "search_docs",
    "list_indexed_docs",
    "explain_commit",
}

# Qué tools sustentan cada objetivo específico (para el resumen final).
OBJETIVOS = {
    "OE1 (Conector GitHub)":        ["get_commits", "get_pull_requests"],
    "OE2 (Documentación Markdown)": ["index_docs", "search_docs", "list_indexed_docs"],
    "OE3 (Interfaz MCP)":           ["protocolo"],
    "OE4 (Integración semántica)":  ["explain_commit"],
}

# Registro de resultados por tool: nombre -> bool
resultados: dict[str, bool] = {}


def separador(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


def resultado(r) -> str:
    """Extrae el texto del resultado de una tool MCP."""
    if hasattr(r, "content") and r.content:
        return r.content[0].text
    return str(r)


async def check(clave: str, titulo: str, cuerpo):
    """Ejecuta una prueba, imprime su salida y registra OK/FALLO en `resultados`."""
    separador(titulo)
    try:
        await cuerpo()
        print(f"\n  OK — {clave} validado")
        resultados[clave] = True
    except Exception as e:
        print(f"\n  FALLO {clave} — {e}")
        resultados[clave] = False


async def run_tests(session: ClientSession):
    # ─────────────────────────────────────────────
    # OE3 — Interfaz MCP: inicialización y listado de tools
    # ─────────────────────────────────────────────
    async def _protocolo():
        tools_resp = await session.list_tools()
        nombres = {t.name for t in tools_resp.tools}
        assert TOOLS_ESPERADAS.issubset(nombres), \
            f"Faltan tools: {TOOLS_ESPERADAS - nombres}"
        print(f"  Tools expuestas al IDE: {sorted(nombres)}")
        print(f"  Protocolo: JSON-RPC 2.0 sobre stdio")

    await check("protocolo", "OE3 — Interfaz MCP: inicialización y protocolo", _protocolo)

    # ─────────────────────────────────────────────
    # OE2 — index_docs: construir el índice de documentación
    # (search_docs, list_indexed_docs y explain_commit dependen de esto)
    # ─────────────────────────────────────────────
    async def _index_docs():
        r = await session.call_tool("index_docs", {"library_url": DOC, "max_pages": 5})
        meta = json.loads(resultado(r))
        assert "error" not in meta, meta.get("error")
        assert meta.get("fragments", 0) > 0, "el índice quedó vacío"
        print(f"  Fuente: {DOC}")
        print(f"  Páginas: {meta.get('pages', '?')} | Fragmentos: {meta['fragments']}")

    await check("index_docs", "OE2 — index_docs: indexación de documentación", _index_docs)

    # ─────────────────────────────────────────────
    # OE2 — list_indexed_docs: la librería indexada aparece en el catálogo
    # ─────────────────────────────────────────────
    async def _list_indexed():
        r = await session.call_tool("list_indexed_docs", {})
        catalogo = json.loads(resultado(r))
        assert isinstance(catalogo, list) and catalogo, "no hay documentación indexada"
        libs = {entry.get("library") for entry in catalogo}
        assert DOC in libs, f"{DOC} no aparece en el catálogo: {libs}"
        print(f"  Librerías indexadas: {len(catalogo)}")
        for entry in catalogo:
            print(f"    - {entry.get('slug')} ({entry.get('fragments')} fragmentos)")

    await check("list_indexed_docs", "OE2 — list_indexed_docs: catálogo de índices", _list_indexed)

    # ─────────────────────────────────────────────
    # OE2 — search_docs: recuperación de fragmentos por término
    # ─────────────────────────────────────────────
    async def _search_docs():
        r = await session.call_tool("search_docs", {
            "library_url": DOC,
            "query": "api key authentication header",
            "top_k": 3,
        })
        fragments = json.loads(resultado(r))
        assert isinstance(fragments, list) and fragments
        assert all("title" in f and "content" in f and "score" in f for f in fragments)
        print(f"  Query: 'api key authentication header'")
        print(f"  Fragmentos encontrados: {len(fragments)}")
        for f in fragments:
            print(f"    [{f['score']:.4f}] {f['section_path']}")
            print(f"             {f['content'][:80].strip()}...")

    await check("search_docs", "OE2 — search_docs: búsqueda en documentación", _search_docs)

    # ─────────────────────────────────────────────
    # OE1 — get_commits: historial de commits
    # ─────────────────────────────────────────────
    async def _get_commits():
        r = await session.call_tool("get_commits", {
            "repo": REPO,
            "branch": "main",
            "limit": 5,
        })
        commits = json.loads(resultado(r))
        assert isinstance(commits, list) and commits
        assert all("sha" in c and "message" in c for c in commits)
        print(f"  Repositorio: {REPO}")
        print(f"  Commits obtenidos: {len(commits)}")
        for c in commits[:3]:
            print(f"    [{c['sha_short']}] {c['date']} — {c['message'].splitlines()[0]}")

    await check("get_commits", "OE1 — get_commits: historial de commits", _get_commits)

    # ─────────────────────────────────────────────
    # OE1 — get_pull_requests: PRs con metadatos
    # ─────────────────────────────────────────────
    async def _get_prs():
        r = await session.call_tool("get_pull_requests", {
            "repo": REPO,
            "state": "closed",
            "limit": 5,
        })
        prs = json.loads(resultado(r))
        assert isinstance(prs, list) and prs
        assert all("number" in pr and "title" in pr for pr in prs)
        print(f"  Pull Requests obtenidos: {len(prs)}")
        for pr in prs[:3]:
            print(f"    #{pr['number']} [{pr['state']}] {pr['title']}")
            print(f"             Autor: {pr['author']} | Merged: {pr['merged_at'] or 'no'}")

    await check("get_pull_requests", "OE1 — get_pull_requests: PRs con metadatos", _get_prs)

    # ─────────────────────────────────────────────
    # OE4 — explain_commit: cruce commit + documentación vía OpenAI
    # ─────────────────────────────────────────────
    async def _explain():
        r = await session.call_tool("explain_commit", {
            "repo": REPO,
            "sha": SHA,
            "library_url": DOC,
            "top_k": 3,
        })
        result = json.loads(resultado(r))
        assert "commit" in result and "explanation" in result
        assert len(result["explanation"]) > 100
        print(f"  Commit analizado: [{result['commit']['sha']}] {result['commit']['message']}")
        print(f"  Fragmentos de docs usados: {result['doc_fragments_used']}")
        print(f"\n  --- Explicación (primeras 10 líneas) ---")
        for line in result["explanation"].splitlines()[:10]:
            print(f"  {line}")
        print(f"  ...")

    await check("explain_commit", "OE4 — explain_commit: integración semántica", _explain)


async def main():
    print("\nINICIANDO TEST E2E — Sprint 4: Integración MCP con IDE")
    print(f"Repositorio: {REPO}")
    print(f"Protocolo: JSON-RPC 2.0 sobre stdio")

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "tesis-mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await run_tests(session)

    # ── Resumen por tool ──
    separador("RESUMEN — herramientas MCP")
    estado = lambda ok: "OK     " if ok else "FALLO  "
    for nombre in sorted(resultados):
        print(f"    [{estado(resultados[nombre])}] {nombre}")

    ok_tools = sum(resultados.values())
    print(f"\n  Tools OK: {ok_tools}/{len(resultados)}")

    # ── Resumen por objetivo específico ──
    print(f"\n  Objetivos de la tesis:")
    todos_ok = True
    for objetivo, tools in OBJETIVOS.items():
        ok = all(resultados.get(t, False) for t in tools)
        todos_ok = todos_ok and ok
        print(f"    {'VALIDADO' if ok else 'FALLO   '} — {objetivo}")

    print(f"\n{'='*60}")
    print(f"  RESULTADO FINAL: {'TODOS LOS OBJETIVOS VALIDADOS' if todos_ok else 'HAY FALLOS'}")
    print(f"{'='*60}\n")


asyncio.run(main())
