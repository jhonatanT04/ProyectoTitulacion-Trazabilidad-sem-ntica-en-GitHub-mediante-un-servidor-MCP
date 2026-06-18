"""
Test Sprint 4 — Integración end-to-end con protocolo MCP real

Valida los 4 objetivos específicos de la tesis usando el cliente MCP
para comunicarse con el servidor a través de JSON-RPC 2.0 sobre stdio:

  OE1 — Conector GitHub: get_commits, get_pull_requests
  OE2 — Documentación Markdown: search_docs
  OE3 — Interfaz MCP: inicialización, listado de tools, protocolo
  OE4 — Integración semántica: explain_commit
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

TOOLS_ESPERADAS = {"get_commits", "get_pull_requests", "search_docs", "explain_commit"}


def separador(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


def resultado(r) -> str:
    """Extrae el texto del resultado de una tool MCP."""
    if hasattr(r, "content") and r.content:
        return r.content[0].text
    return str(r)


async def run_tests(session: ClientSession):
    passed = 0
    failed = 0

    # ─────────────────────────────────────────────
    # SETUP — Indexar la documentación una sola vez.
    # search_docs y explain_commit requieren un índice previo
    # construido con index_docs (misma URL/fuente).
    # ─────────────────────────────────────────────
    separador("SETUP — index_docs: indexando documentación")
    r = await session.call_tool("index_docs", {
        "library_url": DOC,
        "max_pages": 5,
    })
    meta = json.loads(resultado(r))
    if "error" in meta:
        print(f"\n  ADVERTENCIA — no se pudo indexar {DOC}: {meta['error']}")
    else:
        print(f"  Indexado: {meta.get('fragments', '?')} fragmentos desde {DOC}")

    # ─────────────────────────────────────────────
    # OE3 — Interfaz MCP: inicialización y tools
    # ─────────────────────────────────────────────
    separador("OE3 — Interfaz MCP: inicialización y protocolo")
    try:
        tools_resp = await session.list_tools()
        tools_names = {t.name for t in tools_resp.tools}

        assert TOOLS_ESPERADAS.issubset(tools_names), \
            f"Faltan tools: {TOOLS_ESPERADAS - tools_names}"

        print(f"  Tools expuestas al IDE: {sorted(tools_names)}")
        print(f"  Protocolo: JSON-RPC 2.0 sobre stdio")
        print(f"\n  OK — OE3 validado: servidor MCP operativo y tools registradas")
        passed += 1
    except Exception as e:
        print(f"\n  FALLO OE3 — {e}")
        failed += 1

    # ─────────────────────────────────────────────
    # OE1 — Conector GitHub: commits
    # ─────────────────────────────────────────────
    separador("OE1a — Conector GitHub: get_commits")
    try:
        r = await session.call_tool("get_commits", {
            "repo": REPO,
            "branch": "main",
            "limit": 5,
        })
        commits = json.loads(resultado(r))

        assert isinstance(commits, list)
        assert len(commits) > 0
        assert all("sha" in c and "message" in c for c in commits)

        print(f"  Commits obtenidos: {len(commits)}")
        for c in commits[:3]:
            print(f"    [{c['sha_short']}] {c['date']} — {c['message'].splitlines()[0]}")

        print(f"\n  OK — OE1a validado: extracción de commits funciona")
        passed += 1
    except Exception as e:
        print(f"\n  FALLO OE1a — {e}")
        failed += 1

    # ─────────────────────────────────────────────
    # OE1 — Conector GitHub: pull requests
    # ─────────────────────────────────────────────
    separador("OE1b — Conector GitHub: get_pull_requests")
    try:
        r = await session.call_tool("get_pull_requests", {
            "repo": REPO,
            "state": "closed",
            "limit": 5,
        })
        prs = json.loads(resultado(r))

        assert isinstance(prs, list)
        assert len(prs) > 0
        assert all("number" in pr and "title" in pr for pr in prs)

        print(f"  Pull Requests obtenidos: {len(prs)}")
        for pr in prs[:3]:
            print(f"    #{pr['number']} [{pr['state']}] {pr['title']}")
            print(f"             Autor: {pr['author']} | Merged: {pr['merged_at'] or 'no'}")

        print(f"\n  OK — OE1b validado: extracción de PRs con metadatos funciona")
        passed += 1
    except Exception as e:
        print(f"\n  FALLO OE1b — {e}")
        failed += 1

    # ─────────────────────────────────────────────
    # OE2 — Documentación Markdown: search_docs
    # ─────────────────────────────────────────────
    separador("OE2 — Documentación Markdown: search_docs")
    try:
        r = await session.call_tool("search_docs", {
            "library_url": DOC,
            "query": "api key authentication header",
            "top_k": 3,
        })
        fragments = json.loads(resultado(r))

        assert isinstance(fragments, list)
        assert len(fragments) > 0
        assert all("title" in f and "content" in f and "score" in f for f in fragments)

        print(f"  Fuente: {DOC}")
        print(f"  Query: 'api key authentication header'")
        print(f"  Fragmentos encontrados: {len(fragments)}")
        for f in fragments:
            print(f"    [{f['score']:.4f}] {f['section_path']}")
            print(f"             {f['content'][:80].strip()}...")

        print(f"\n  OK — OE2 validado: indexación y búsqueda de documentación funciona")
        passed += 1
    except Exception as e:
        print(f"\n  FALLO OE2 — {e}")
        failed += 1

    # ─────────────────────────────────────────────
    # OE4 — Integración semántica: explain_commit
    # ─────────────────────────────────────────────
    separador("OE4 — Integración semántica: explain_commit")
    try:
        r = await session.call_tool("explain_commit", {
            "repo": REPO,
            "sha": SHA,
            "library_url": DOC,
            "top_k": 3,
        })
        result = json.loads(resultado(r))

        assert "commit" in result
        assert "explanation" in result
        assert len(result["explanation"]) > 100

        print(f"  Commit analizado: [{result['commit']['sha']}] {result['commit']['message']}")
        print(f"  Fragmentos de docs usados: {result['doc_fragments_used']}")
        print(f"\n  --- Explicación (primeras 10 líneas) ---")
        for line in result["explanation"].splitlines()[:10]:
            print(f"  {line}")
        print(f"  ...")

        print(f"\n  OK — OE4 validado: prompt dinámico y explicación semántica funciona")
        passed += 1
    except Exception as e:
        print(f"\n  FALLO OE4 — {e}")
        failed += 1

    return passed, failed


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
            passed, failed = await run_tests(session)

    print(f"\n{'='*60}")
    print(f"  RESULTADO FINAL: {passed} objetivos validados / {failed} fallidos")
    print(f"\n  Objetivos de la tesis:")
    status = lambda ok: "VALIDADO" if ok else "FALLO"
    print(f"    OE1 (GitHub connector):      {status(passed >= 3)}")
    print(f"    OE2 (Docs Markdown):         {status(passed >= 4)}")
    print(f"    OE3 (Interfaz MCP):          {status(passed >= 1)}")
    print(f"    OE4 (Integración semántica): {status(passed >= 5)}")
    print(f"{'='*60}\n")


asyncio.run(main())
