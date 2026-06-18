import json

from mcp.server.fastmcp import Context

from ServidorMCP.app import mcp
from ServidorMCP.connectors.repo import resolve_repo_auto


@mcp.tool()
async def get_commits(
    repo: str = "",
    branch: str = "",
    since: str = "",
    until: str = "",
    limit: int = 30,
    ctx: Context = None,
) -> str:
    """
    Obtiene el historial de commits de un repositorio (local o de GitHub).

    Args:
        repo: Opcional. Ruta local a un clon git o slug 'owner/repo' de GitHub.
            Si se deja vacío, se usa el repositorio abierto en el IDE.
        branch: Rama a consultar (vacío = rama actual / por defecto).
        since: Fecha de inicio ISO 8601, ej: 2024-01-01T00:00:00Z (opcional).
        until: Fecha de fin ISO 8601 (opcional).
        limit: Número máximo de commits a retornar, máx 100 (default: 30).
    """
    source = await resolve_repo_auto(repo, ctx)
    commits = await source.get_commits(
        branch=branch or None,
        since=since or None,
        until=until or None,
        limit=limit,
    )
    return json.dumps(commits, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_pull_requests(
    repo: str = "",
    state: str = "all",
    limit: int = 30,
    ctx: Context = None,
) -> str:
    """
    Obtiene los pull requests de un repositorio con sus metadatos.

    Los PRs son un concepto de GitHub: si `repo` es una ruta local, se usa el
    remoto 'origin' del clon para consultarlos en GitHub.

    Args:
        repo: Opcional. Ruta local a un clon git o slug 'owner/repo' de GitHub.
            Si se deja vacío, se usa el repositorio abierto en el IDE.
        state: Estado de los PRs: 'open', 'closed' o 'all' (default: all).
        limit: Número máximo de PRs a retornar, máx 100 (default: 30).
    """
    source = await resolve_repo_auto(repo, ctx)
    prs = await source.get_pull_requests(state=state, limit=limit)
    return json.dumps(prs, ensure_ascii=False, indent=2)
