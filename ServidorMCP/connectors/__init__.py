"""
Capa 3 — Conectores hacia sistemas externos.

Cada conector aísla un sistema concreto detrás de una API estable:
- `GitHubConnector`  / `LocalGitConnector` → historial de commits y PRs.
- `RepoSource` (+ `resolve_repo` / `resolve_repo_auto`) → fuente uniforme de
  repositorio, sea un clon local o un repo de GitHub.
- `OpenAIConnector` → chat y embeddings.
- `scrape_library` / `read_markdown` → recuperación de documentación.
"""
from ServidorMCP.connectors.github import GitHubConnector
from ServidorMCP.connectors.localgit import LocalGitConnector, LocalGitError
from ServidorMCP.connectors.markdown import read_markdown
from ServidorMCP.connectors.openai import OpenAIConnector
from ServidorMCP.connectors.repo import (
    RepoSource,
    resolve_repo,
    resolve_repo_auto,
)
from ServidorMCP.connectors.scraper import scrape_library

__all__ = [
    "GitHubConnector",
    "LocalGitConnector",
    "LocalGitError",
    "OpenAIConnector",
    "RepoSource",
    "resolve_repo",
    "resolve_repo_auto",
    "read_markdown",
    "scrape_library",
]
