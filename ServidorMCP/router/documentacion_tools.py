from mcp.server.fastmcp import FastMCP

from ServidorMCP.logic.MarkdownProcessor import MarkdownProcessor
from ServidorMCP.setting.conf import get_github_client


def _cliente():
    return get_github_client()


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def buscar_en_documentacion(
        termino: str,
        ruta_local: str | None = None,
        directorio_local: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        ruta_github: str | None = None,
        max_resultados: int = 5,
    ) -> dict:
        """
        Busca fragmentos relevantes en documentación Markdown dado un término o
        concepto técnico. Soporta tres fuentes de datos (usar solo una por llamada):

        FUENTE 1 — Archivo local:
            ruta_local: Ruta absoluta a un archivo .md o .markdown.

        FUENTE 2 — Directorio local:
            directorio_local: Ruta absoluta a una carpeta; busca en todos los .md
                              que contenga de forma recursiva.

        FUENTE 3 — GitHub:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            ruta_github: Ruta al archivo .md dentro del repositorio
                         (ej: 'docs/guia.md').

        Args:
            termino: Término o concepto técnico a buscar.
            max_resultados: Número máximo de fragmentos a retornar. Por defecto 5.

        Returns:
            Resultado con el término buscado, total de fragmentos encontrados y
            la lista de fragmentos relevantes ordenados por relevancia, cada uno
            con título, nivel de encabezado, contenido y posición en el documento.
        """
        processor = MarkdownProcessor()

        if owner and repo and ruta_github:
            client = _cliente()
            contenido, url = await client.get_archivo_markdown(owner, repo, ruta_github)
            resultado = processor.buscar_en_contenido(termino, contenido, url, max_resultados)

        elif directorio_local:
            resultado = processor.buscar_en_directorio(termino, directorio_local, max_resultados)

        elif ruta_local:
            resultado = processor.buscar(termino, ruta_local, max_resultados)

        else:
            raise ValueError(
                "Debes indicar una fuente: 'ruta_local', 'directorio_local' "
                "o los parámetros 'owner' + 'repo' + 'ruta_github'."
            )

        return resultado.model_dump()
