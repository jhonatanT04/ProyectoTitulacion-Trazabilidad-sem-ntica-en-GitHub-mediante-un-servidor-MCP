import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from ServidorMCP.logic.GitHubCliente import GitHubClient

# Permite importar github_client tanto al ejecutar directamente
# como al invocar como módulo (python -m ServidorMCP.main)
sys.path.insert(0, os.path.dirname(__file__))


load_dotenv()

mcp = FastMCP("ania-github")


def _cliente() -> GitHubClient:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError(
            "GITHUB_TOKEN no está configurado. "
            "Crea un archivo .env con tu token de GitHub."
        )
    return GitHubClient(token)


@mcp.tool()
async def obtener_pull_requests(
    owner: str,
    repo: str,
    estado: str = "open",
    cantidad: int = 30,
) -> list[dict]:
    """
    Obtiene los pull requests de un repositorio de GitHub.

    Args:
        owner: Propietario del repositorio (usuario u organización).
        repo: Nombre del repositorio.
        estado: Estado de los PRs: 'open', 'closed' o 'all'. Por defecto 'open'.
        cantidad: Número máximo de PRs a retornar (máx 100). Por defecto 30.

    Returns:
        Lista de pull requests con número, título, estado, autor, ramas,
        fechas, estadísticas de cambios y URL.
    """
    if estado not in ("open", "closed", "all"):
        raise ValueError("El parámetro 'estado' debe ser 'open', 'closed' o 'all'.")

    client = _cliente()
    pull_requests = await client.get_pull_requests(owner, repo, estado, cantidad)  # type: ignore[arg-type]
    return [pr.model_dump() for pr in pull_requests]


@mcp.tool()
async def obtener_commits(
    owner: str,
    repo: str,
    rama: str = "main",
    cantidad: int = 30,
) -> list[dict]:
    """
    Obtiene los commits de un repositorio de GitHub.

    Args:
        owner: Propietario del repositorio (usuario u organización).
        repo: Nombre del repositorio.
        rama: Rama o SHA desde donde extraer commits. Por defecto 'main'.
        cantidad: Número máximo de commits a retornar (máx 100). Por defecto 30.

    Returns:
        Lista de commits con SHA, mensaje (primera línea), autor, fecha y URL.
    """
    client = _cliente()
    commits = await client.get_commits(owner, repo, rama, cantidad)
    return [c.model_dump() for c in commits]


if __name__ == "__main__":
    mcp.run()
