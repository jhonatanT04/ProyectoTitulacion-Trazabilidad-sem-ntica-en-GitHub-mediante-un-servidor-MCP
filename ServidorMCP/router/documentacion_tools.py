from mcp.server.fastmcp import FastMCP

from ServidorMCP.logic.MarkdownProcessor import MarkdownProcessor
from ServidorMCP.setting.conf import get_github_client


def _cliente():
    return get_github_client()


def register(mcp: FastMCP) -> None:

    # ------------------------------------------------------------------ #
    #  Prompts                                                             #
    # ------------------------------------------------------------------ #

    @mcp.prompt()
    def consultar_documentacion(
        termino: str,
        fuente: str,
    ) -> str:
        """
        Genera un prompt para buscar un término en la documentación y presentar
        los fragmentos relevantes de forma clara.

        Args:
            termino: Concepto o término técnico a buscar.
            fuente: Descripción de la fuente (ej: ruta local, URL de GitHub, directorio).
        """
        return f"""Busca información sobre "{termino}" en la documentación ({fuente}).

Pasos:
1. Usa `buscar_en_documentacion` con termino="{termino}" y la fuente correspondiente.
2. Con los fragmentos encontrados:
   - Presenta cada fragmento indicando su título de sección y nivel de encabezado.
   - Cita textualmente las partes más relevantes.
   - Si hay varios fragmentos relacionados, sintetiza la información en una respuesta
     coherente en lugar de listarlos por separado.
   - Si no se encuentra el término, sugiere términos alternativos relacionados.
3. Al final, indica en qué secciones del documento aparece la información."""

    @mcp.prompt()
    def resumir_seccion(
        termino: str,
        fuente: str,
        max_fragmentos: int = 3,
    ) -> str:
        """
        Genera un prompt para obtener un resumen ejecutivo de las secciones
        de la documentación relacionadas con un término.

        Args:
            termino: Concepto o término técnico a resumir.
            fuente: Descripción de la fuente de documentación.
            max_fragmentos: Cantidad máxima de fragmentos a considerar.
        """
        return f"""Resume las secciones de la documentación ({fuente}) relacionadas
con "{termino}".

Pasos:
1. Usa `buscar_en_documentacion` con termino="{termino}", max_resultados={max_fragmentos}
   y la fuente correspondiente.
2. Con los fragmentos:
   - Escribe un resumen ejecutivo de máximo 3 párrafos.
   - Incluye los conceptos clave definidos en la documentación.
   - Menciona ejemplos o casos de uso si la documentación los incluye.
   - Usa el vocabulario exacto del documento para términos técnicos.
3. Cierra con una lista de puntos clave (bullet points) para referencia rápida."""

    # ------------------------------------------------------------------ #
    #  Tools                                                               #
    # ------------------------------------------------------------------ #

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
