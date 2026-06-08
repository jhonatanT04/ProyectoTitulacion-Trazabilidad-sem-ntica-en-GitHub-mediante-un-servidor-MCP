import json

from ServerMCP.app import mcp
from ServerMCP.config import GITHUB_TOKEN
from ServerMCP.connectors.github import GitHubConnector


def _github() -> GitHubConnector:
    return GitHubConnector(GITHUB_TOKEN)


@mcp.tool()
async def get_commits(
    owner: str,
    repo: str,
    branch: str = "main",
    since: str = "",
    until: str = "",
    limit: int = 30,
) -> str:
    """
    Obtiene el historial de commits de un repositorio de GitHub.

    Args:
        owner: Propietario del repositorio (usuario u organización).
        repo: Nombre del repositorio.
        branch: Rama a consultar (default: main).
        since: Fecha de inicio ISO 8601, ej: 2024-01-01T00:00:00Z (opcional).
        until: Fecha de fin ISO 8601 (opcional).
        limit: Número máximo de commits a retornar, máx 100 (default: 30).
    """
    connector = _github()
    commits = await connector.get_commits(
        owner=owner,
        repo=repo,
        branch=branch or None,
        since=since or None,
        until=until or None,
        limit=limit,
    )
    return json.dumps(commits, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_pull_requests(
    owner: str,
    repo: str,
    state: str = "all",
    limit: int = 30,
) -> str:
    """
    Obtiene los pull requests de un repositorio de GitHub con sus metadatos.

    Args:
        owner: Propietario del repositorio.
        repo: Nombre del repositorio.
        state: Estado de los PRs: 'open', 'closed' o 'all' (default: all).
        limit: Número máximo de PRs a retornar, máx 100 (default: 30).
    """
    connector = _github()
    prs = await connector.get_pull_requests(
        owner=owner,
        repo=repo,
        state=state,
        limit=limit,
    )
    return json.dumps(prs, ensure_ascii=False, indent=2)
