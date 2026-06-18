import re
from pathlib import Path
from typing import Any, Optional, Protocol
from urllib.parse import unquote, urlparse

from ServidorMCP.config import GITHUB_TOKEN
from ServidorMCP.connectors.github import GitHubConnector
from ServidorMCP.connectors.localgit import LocalGitConnector

# owner/repo: dos segmentos sin barras ni espacios internos (ej: anthropics/anthropic-sdk-python)
_SLUG_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


class RepoSource(Protocol):
    """Interfaz uniforme sobre un repositorio, sea local o de GitHub.

    Ambos conectores quedan ya ligados a un repo concreto, por eso los
    métodos no reciben owner/repo.
    """

    async def get_commits(
        self,
        branch: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 30,
    ) -> list[dict]: ...

    async def get_commit(self, sha: str) -> dict: ...

    async def get_pull_requests(self, state: str = "all", limit: int = 30) -> list[dict]: ...


class _GitHubRepoSource:
    """Adapta GitHubConnector (stateless) a la interfaz RepoSource ligando
    owner/repo a la instancia."""

    def __init__(self, owner: str, repo: str):
        self._gh = GitHubConnector(GITHUB_TOKEN)
        self._owner = owner
        self._repo = repo

    async def get_commits(self, branch=None, since=None, until=None, limit=30) -> list[dict]:
        return await self._gh.get_commits(
            owner=self._owner,
            repo=self._repo,
            branch=branch,
            since=since,
            until=until,
            limit=limit,
        )

    async def get_commit(self, sha: str) -> dict:
        return await self._gh.get_commit(self._owner, self._repo, sha)

    async def get_pull_requests(self, state="all", limit=30) -> list[dict]:
        return await self._gh.get_pull_requests(
            owner=self._owner, repo=self._repo, state=state, limit=limit
        )


def resolve_repo(repo: str) -> RepoSource:
    """Devuelve el conector adecuado según la forma de `repo`:

    - Ruta a un directorio existente con git → LocalGitConnector (git local).
    - Formato 'owner/repo'                   → GitHubConnector (API REST).

    Args:
        repo: Ruta local a un clon (ej: '/home/user/proyecto' o '~/proyecto')
              o slug de GitHub (ej: 'anthropics/anthropic-sdk-python').
    """
    path = Path(repo).expanduser()
    if path.is_dir():
        if not (path / ".git").exists():
            raise ValueError(
                f"'{repo}' es un directorio pero no es un repositorio git "
                f"(no contiene .git). Clona o inicializa el repo primero."
            )
        return LocalGitConnector(str(path))

    if _SLUG_RE.match(repo):
        owner, name = repo.split("/", 1)
        return _GitHubRepoSource(owner, name)

    raise ValueError(
        f"No se reconoce '{repo}' como repositorio. Usa una ruta local a un "
        f"clon git, o el formato 'owner/repo' de GitHub."
    )


def _uri_to_path(uri: str) -> Optional[str]:
    """Convierte una URI 'file://' (la que envía el IDE) en una ruta local."""
    if not uri.startswith("file://"):
        return None
    return unquote(urlparse(uri).path) or None


async def _workspace_root(ctx: Any) -> Optional[str]:
    """Pregunta al IDE qué carpeta(s) tiene abiertas (protocolo MCP roots) y
    devuelve la primera que sea un repositorio git. Devuelve None si el cliente
    no soporta roots o no expone ninguna."""
    if ctx is None:
        return None
    try:
        result = await ctx.session.list_roots()
    except Exception:
        return None

    roots = getattr(result, "roots", None) or []
    paths = [p for r in roots if (p := _uri_to_path(str(r.uri)))]

    # Preferir una carpeta abierta que realmente sea un clon git.
    for p in paths:
        if (Path(p) / ".git").exists():
            return p
    # Si ninguna tiene .git, usar la primera de todas formas.
    return paths[0] if paths else None


async def resolve_repo_auto(repo: str, ctx: Any = None) -> RepoSource:
    """Resuelve la fuente del repositorio sin obligar a pasar la ruta.

    - Si `repo` viene con valor → se usa tal cual (ruta local o 'owner/repo').
    - Si `repo` está vacío → se deduce del workspace abierto en el IDE (roots)
      y, como último recurso, del directorio de trabajo del servidor.
    """
    if repo and repo.strip():
        return resolve_repo(repo.strip())

    root = await _workspace_root(ctx)
    if root:
        return resolve_repo(root)

    # Último recurso: el cwd del servidor (útil al correrlo dentro del repo).
    cwd = Path.cwd()
    if (cwd / ".git").exists():
        return resolve_repo(str(cwd))

    raise ValueError(
        "No se indicó 'repo' y no se pudo deducir el repositorio del workspace "
        "abierto. Abre una carpeta que sea un clon git en el IDE, o pasa la "
        "ruta/owner-repo explícitamente."
    )
