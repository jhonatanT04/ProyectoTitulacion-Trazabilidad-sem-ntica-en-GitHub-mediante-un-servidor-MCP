from mcp.server.fastmcp import FastMCP

from ServidorMCP.setting.conf import get_github_client


def _cliente():
    return get_github_client()


def register(mcp: FastMCP) -> None:

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
    async def obtener_estructura_proyecto(
        owner: str,
        repo: str,
        ref: str = "HEAD",
    ) -> dict:
        """
        Extrae la estructura completa de archivos y directorios de un repositorio
        en un commit específico.

        Args:
            owner: Propietario del repositorio (usuario u organización).
            repo: Nombre del repositorio.
            ref: SHA del commit, nombre de rama o tag desde donde extraer la
                 estructura. Por defecto 'HEAD' (último commit de la rama
                 principal).

        Returns:
            Estructura del proyecto con metadatos del commit (SHA, mensaje,
            autor, fecha) y la lista completa de entradas del árbol, cada una
            con su ruta, tipo (archivo o directorio), SHA y tamaño en bytes.
        """
        client = _cliente()
        estructura = await client.get_estructura_proyecto(owner, repo, ref)
        return estructura.model_dump()

    @mcp.tool()
    async def obtener_commits(
        owner: str,
        repo: str,
        rama: str = "",
        cantidad: int = 30,
        desde: str | None = None,
        hasta: str | None = None,
    ) -> list[dict]:
        """
        Obtiene los commits de un repositorio de GitHub.

        Args:
            owner: Propietario del repositorio (usuario u organización).
            repo: Nombre del repositorio.
            rama: Rama o SHA desde donde extraer commits. Vacío para la rama principal.
            cantidad: Número máximo de commits a retornar (máx 100). Por defecto 30.
            desde: Fecha de inicio en formato ISO 8601 (ej: '2024-01-01' o
                   '2024-01-01T00:00:00Z'). Solo retorna commits posteriores a esta fecha.
            hasta: Fecha de fin en formato ISO 8601 (ej: '2024-12-31' o
                   '2024-12-31T23:59:59Z'). Solo retorna commits anteriores a esta fecha.

        Returns:
            Lista de commits con SHA, mensaje (primera línea), autor, fecha y URL.
        """
        client = _cliente()
        commits = await client.get_commits(owner, repo, rama, cantidad, desde, hasta)
        return [c.model_dump() for c in commits]
