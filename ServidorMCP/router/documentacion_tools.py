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
        Genera un prompt para buscar un término en documentación local o de GitHub
        y presentar los fragmentos de forma estructurada.

        Args:
            termino: Concepto o término técnico a buscar.
            fuente: Descripción de la fuente (ruta local, directorio o repo de GitHub).
        """
        return f"""Busca información sobre "{termino}" en la documentación ({fuente}).

Pasos:
1. Elige la tool según la fuente:
   - Archivo .md local  → `buscar_en_documentacion` con ruta_local="..."
   - Carpeta local      → `buscar_en_documentacion` con directorio_local="..."
   - Repo GitHub        → `buscar_en_documentacion` con owner, repo y ruta_github
   Usa termino="{termino}" en todos los casos.

2. Cada fragmento retornado tiene: titulo, tipo, jerarquia, lenguaje y contenido.
   Presenta los resultados así:
   - Fragmentos tipo "seccion": muestra la jerarquía completa como ruta
     (ej: Instalación › Configuración › titulo) y cita el contenido relevante.
   - Fragmentos tipo "codigo": muestra el lenguaje (si existe) y el bloque
     de código completo en un bloque de formato adecuado.
   - Fragmentos tipo "intro": preséntalo como contexto general del documento.

3. Si hay varios fragmentos relacionados, sintetiza primero en prosa y luego
   muestra los ejemplos de código agrupados.
4. Si no hay resultados, sugiere términos alternativos o sinónimos técnicos.
5. Al final indica la jerarquía de secciones donde aparece la información."""

    @mcp.prompt()
    def resumir_seccion(
        termino: str,
        fuente: str,
        max_fragmentos: int = 3,
    ) -> str:
        """
        Genera un prompt para obtener un resumen ejecutivo de las secciones
        de la documentación relacionadas con un término, separando teoría de ejemplos.

        Args:
            termino: Concepto o término técnico a resumir.
            fuente: Descripción de la fuente de documentación.
            max_fragmentos: Cantidad máxima de fragmentos a considerar.
        """
        return f"""Resume la documentación ({fuente}) sobre "{termino}".

Pasos:
1. Usa `buscar_en_documentacion` con termino="{termino}", max_resultados={max_fragmentos}
   y la fuente correspondiente.

2. Separa los fragmentos por tipo:
   - "seccion" / "intro" → son explicaciones teóricas o conceptuales.
   - "codigo"            → son ejemplos prácticos; incluye el lenguaje ({termino}).

3. Estructura la respuesta así:
   ## Concepto
   Resumen ejecutivo en 2-3 párrafos usando el vocabulario exacto del documento.

   ## Puntos clave
   - Lista de conceptos o propiedades importantes.

   ## Ejemplos de uso
   Muestra los bloques de código encontrados, indicando el lenguaje y qué demuestra
   cada uno según la sección a la que pertenecen (campo jerarquia).

4. Si no hay fragmentos de código, indícalo explícitamente."""

    @mcp.prompt()
    def consultar_documentacion_url(
        termino: str,
        url: str,
    ) -> str:
        """
        Genera un prompt para buscar un término en documentación online
        (ReadTheDocs, GitHub Pages, MkDocs, Markdown crudo) y presentar
        los resultados distinguiendo secciones de ejemplos de código.

        Args:
            termino: Concepto o término técnico a buscar.
            url: URL de la página o archivo de documentación.
        """
        return f"""Busca información sobre "{termino}" en la documentación de: {url}

Pasos:
1. Usa `buscar_en_url` con termino="{termino}" y url="{url}".
   - Si la URL apunta a un .md o raw.githubusercontent.com, se procesa como Markdown.
   - Si es HTML (ReadTheDocs, MkDocs, etc.), se extrae el texto automáticamente.

2. Con los fragmentos retornados (cada uno tiene tipo, jerarquia, lenguaje, contenido):
   - Fragmentos tipo "seccion": presenta la ruta jerárquica completa y cita
     las partes más relevantes para "{termino}".
   - Fragmentos tipo "codigo": muestra el ejemplo con su lenguaje y explica
     qué ilustra según la sección padre (campo jerarquia).

3. Sintetiza la información en una respuesta coherente:
   - Primero la explicación conceptual (fragmentos de sección).
   - Luego los ejemplos prácticos (fragmentos de código).

4. Cierra indicando en qué URL y secciones se encontró la información."""

    # ------------------------------------------------------------------ #
    #  Tools                                                               #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def buscar_en_url(
        termino: str,
        url: str,
        max_resultados: int = 5,
    ) -> dict:
        """
        Descarga documentación desde una URL y busca fragmentos relevantes
        dado un término o concepto técnico.

        Soporta:
        - Páginas HTML de documentación (ReadTheDocs, GitHub Pages, MkDocs, etc.)
        - Archivos Markdown crudos (raw.githubusercontent.com, enlaces directos a .md)

        Los bloques de código dentro de la documentación se extraen como
        fragmentos independientes, lo que permite recuperar ejemplos de uso
        directamente.

        Args:
            termino: Término o concepto técnico a buscar.
            url: URL de la página o archivo de documentación.
            max_resultados: Número máximo de fragmentos a retornar. Por defecto 5.

        Returns:
            Resultado con el término buscado, total de fragmentos encontrados y
            la lista de fragmentos relevantes ordenados por relevancia, cada uno
            con título, jerarquía de sección, tipo (seccion/codigo), lenguaje
            (si aplica) y contenido.
        """
        processor = MarkdownProcessor()
        resultado = await processor.buscar_en_url(termino, url, max_resultados)
        return resultado.model_dump()

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
