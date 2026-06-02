from mcp.server.fastmcp import FastMCP

from ServidorMCP.logic.MarkdownProcessor import MarkdownProcessor
from ServidorMCP.logic.OpenAICliente import OpenAICliente
from ServidorMCP.models.GitHubModels.ExplicacionCommit import ExplicacionCommit
from ServidorMCP.models.SemanticText.Fragmento import Fragmento
from ServidorMCP.setting.conf import get_github_client, get_openai_client, get_openai_model

def _cliente():
    return get_github_client()


def register(mcp: FastMCP) -> None:

    # ------------------------------------------------------------------ #
    #  Prompts                                                             #
    # ------------------------------------------------------------------ #

    @mcp.prompt()
    def analizar_pull_requests(
        owner: str,
        repo: str,
        estado: str = "all",
    ) -> str:
        """
        Genera un prompt para analizar los pull requests de un repositorio.
        Guía al LLM a obtener los PRs y presentar un análisis estructurado.
        """
        return f"""Analiza los pull requests del repositorio `{owner}/{repo}`.

        Pasos:
        1. Usa `obtener_pull_requests` con owner="{owner}", repo="{repo}", estado="{estado}".
        2. Con los resultados, presenta:
           - Resumen general: total de PRs, cuántos están abiertos / cerrados / mergeados.
           - Top PRs por impacto: los que tienen más archivos cambiados, adiciones o eliminaciones.
           - PRs potencialmente bloqueados: abiertos con fecha de creación antigua.
           - Distribución por autor: agrupa y cuenta PRs por contribuidor.
           - Línea de tiempo: ordena por fecha de creación y destaca períodos de mayor actividad.
        3. Usa fechas en formato legible (DD/MM/AAAA).
        4. Si hay PRs sin merge después de 7 días, márcalos como ⚠️ posible bloqueo."""

    @mcp.prompt()
    def analizar_historial_commits(
        owner: str,
        repo: str,
        rama: str = "",
        desde: str = "",
        hasta: str = "",
    ) -> str:
        """
        Genera un prompt para analizar el historial de commits de un repositorio.
        """
        rango = f" entre {desde or '...'} y {hasta or '...'}" if (desde or hasta) else ""
        nota_rama = "(rama principal si está vacío)" if not rama else ""
        linea_desde = f'- desde="{desde}"' if desde else ""
        linea_hasta = f'- hasta="{hasta}"' if hasta else ""

        return f"""Analiza el historial de commits del repositorio `{owner}/{repo}`{rango}.

        Pasos:
        1. Usa `obtener_commits` con:
           - owner="{owner}", repo="{repo}"
           - rama="{rama}" {nota_rama}
           {linea_desde}
           {linea_hasta}
        2. Con los resultados, presenta:
           - Total de commits en el período.
           - Contribuidores: lista de autores con cantidad de commits de cada uno.
           - Frecuencia: días con mayor actividad de commits.
           - Mensajes relevantes: agrupa commits por temática (feat, fix, refactor, etc.)
             si siguen Conventional Commits; si no, resume los más significativos.
           - SHA corto de cada commit para referencia rápida.
        3. Ordena la presentación del más reciente al más antiguo."""

    @mcp.prompt()
    def comparar_commits(
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> str:
        """
        Genera un prompt para analizar las diferencias entre dos commits
        (o ramas/tags) de un repositorio, destacando cambios en código
        y documentación por separado.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            base: SHA, rama o tag del commit base (punto de partida).
            head: SHA, rama o tag del commit destino (punto final).
        """
        return f"""Analiza las diferencias entre `{base}` y `{head}` en el repositorio `{owner}/{repo}`.

Pasos:
1. Usa `obtener_diferencia_commits` con owner="{owner}", repo="{repo}",
   base="{base}", head="{head}".

2. Presenta un resumen ejecutivo:
   - Rango comparado: {base} → {head}
   - Total de commits intermedios y autores involucrados.
   - Estadísticas globales: archivos modificados, líneas añadidas (+) y eliminadas (-).

3. Clasifica los archivos cambiados en dos grupos:
   A) Código fuente (.py, .ts, .js, .java, .go, etc.)
      - Para cada archivo: ruta, estado (added/modified/removed/renamed) y estadísticas.
      - Si el patch está disponible, extrae los cambios más significativos:
        · Nuevas funciones o clases añadidas (líneas que empiezan con `+def `, `+class `).
        · Funciones o clases eliminadas (líneas que empiezan con `-def `, `-class `).
        · Cambios en imports o dependencias.
   B) Documentación (.md, .rst, .txt, .yaml, .json de config)
      - Para cada archivo: ruta, estado y resumen de qué secciones cambiaron.

4. Indica los commits intermedios en orden cronológico:
   - SHA corto, autor, fecha y mensaje de cada commit.

5. Concluye con:
   - ¿Qué funcionalidad fue añadida, modificada o eliminada?
   - ¿Hubo cambios en la documentación que reflejen los cambios de código?
   - Archivos con mayor impacto (más líneas cambiadas)."""

#     @mcp.prompt()
#     def analizar_commit_con_docs(
#         owner: str,
#         repo: str,
#         sha: str,
#         fuente_docs: str = "",
#     ) -> str:
#         """
#         Genera un prompt para explicar un commit correlacionando su diff con
#         documentación técnica relevante usando OpenAI.

#         Args:
#             owner: Propietario del repositorio.
#             repo: Nombre del repositorio.
#             sha: SHA del commit a explicar.
#             fuente_docs: Descripción de la fuente de documentación (ruta local,
#                          directorio, URL o repo de GitHub).
#         """
#         nota_docs = (
#             f"La documentación se encuentra en: {fuente_docs}"
#             if fuente_docs
#             else "No se especificó fuente de documentación (se explicará solo con el diff)."
#         )
#         return f"""Explica el commit `{sha[:7]}` del repositorio `{owner}/{repo}` \
# correlacionando su diff con la documentación técnica relevante.

# {nota_docs}

# Pasos:
# 1. Usa `explicar_commit` con:
#    - owner="{owner}", repo="{repo}", sha="{sha}"
#    - Añade el parámetro de fuente de documentación según corresponda:
#      · ruta_doc_local    → archivo .md local
#      · directorio_doc_local → carpeta con archivos .md
#      · url_doc           → URL de documentación online
#      · owner_doc + repo_doc + ruta_doc_github → archivo .md en GitHub

# 2. Presenta la explicación generada respetando sus secciones:
#    - **Resumen**: qué hace el commit en una oración.
#    - **Cambios principales**: archivos y funciones modificadas.
#    - **Contexto de la documentación**: cómo los fragmentos de docs justifican los cambios.
#    - **Impacto técnico**: consecuencias en el sistema.

# 3. Al final indica cuántos fragmentos de documentación fueron utilizados y el modelo empleado."""

    @mcp.prompt()
    def inspeccionar_estructura(
        owner: str,
        repo: str,
        ref: str = "HEAD",
    ) -> str:
        """
        Genera un prompt para inspeccionar y explicar la estructura del proyecto
        en un commit específico.
        """
        return f"""Inspecciona la estructura del repositorio `{owner}/{repo}` en `{ref}`.

        Pasos:
        1. Usa `obtener_estructura_proyecto` con owner="{owner}", repo="{repo}", ref="{ref}".
        2. Con los resultados, presenta:
           - Metadatos del commit: SHA, autor, fecha y mensaje.
           - Árbol de directorios: muestra la jerarquía de carpetas principales (máx. 2 niveles).
           - Archivos raíz: lista los archivos en el nivel superior y su propósito probable.
           - Estadísticas: total de archivos y directorios.
           - Tecnologías detectadas: infiere el stack a partir de extensiones de archivo
             (ej: .py → Python, .ts → TypeScript, Dockerfile → Docker).
           - Puntos de entrada probables: busca main.py, index.ts, app.py, etc.
        3. Presenta el árbol usando sangría para reflejar la jerarquía."""

    # ------------------------------------------------------------------ #
    #  Tools                                                               #
    # ------------------------------------------------------------------ #

    
    
    # @mcp.tool()
    # async def explicar_commit(
    #     owner: str,
    #     repo: str,
    #     sha: str,
    #     ruta_doc_local: str | None = None,
    #     directorio_doc_local: str | None = None,
    #     url_doc: str | None = None,
    #     owner_doc: str | None = None,
    #     repo_doc: str | None = None,
    #     ruta_doc_github: str | None = None,
    # ) -> dict:
    #     """
    #     Explica un commit en lenguaje natural correlacionando su diff con
    #     documentación técnica relevante mediante la API de OpenAI.

    #     Implementa dos mejoras sobre la búsqueda básica:
    #     - [B] Correlación temporal: si la fuente es un archivo en GitHub, busca
    #       automáticamente la versión del documento vigente al momento del commit
    #       (no la versión actual), evitando correlacionar con documentación futura.
    #     - [A] Búsqueda semántica: usa embeddings (text-embedding-3-small) para
    #       rankear los fragmentos por similitud semántica al diff, no por coincidencia
    #       de palabras. Fallback automático a búsqueda léxica si falla la API.

    #     Args:
    #         owner: Propietario del repositorio (usuario u organización).
    #         repo: Nombre del repositorio.
    #         sha: SHA completo o corto del commit a explicar.
    #         ruta_doc_local: Ruta absoluta a un archivo .md local (fuente 1).
    #         directorio_doc_local: Ruta absoluta a un directorio con archivos .md (fuente 2).
    #         url_doc: URL de una página de documentación online (fuente 3).
    #         owner_doc: Propietario del repo de documentación en GitHub (fuente 4, aplica B).
    #         repo_doc: Nombre del repo de documentación en GitHub (fuente 4, aplica B).
    #         ruta_doc_github: Ruta al archivo .md en el repo de documentación (fuente 4, aplica B).
    #         modelo: Modelo de OpenAI a usar. Si se omite, usa la variable OPENAI_MODEL.

    #     Returns:
    #         ExplicacionCommit con: sha, sha_corto, mensaje_commit, explicacion,
    #         fragmentos_usados, modelo, metodo_busqueda y version_doc_sha (SHA del
    #         doc histórico usado, solo cuando aplica correlación temporal).
    #     """
    #     modelo = get_openai_model()
    #     gh = _cliente()
    #     ia = OpenAICliente(get_openai_client())

    #     # 1. Diff del commit
    #     sha_padre = await gh.get_sha_padre(owner, repo, sha)
    #     diferencia = await gh.get_diferencia_commits(owner, repo, sha_padre, sha)

    #     primer_commit = diferencia.commits_intermedios[0] if diferencia.commits_intermedios else None
    #     mensaje = primer_commit.mensaje if primer_commit else sha[:7]
    #     fecha_commit = primer_commit.fecha if primer_commit else None

    #     # 2. Recolectar fragmentos de documentación
    #     fragmentos: list[Fragmento] = []
    #     version_doc_sha: str | None = None
    #     metodo_busqueda = "ninguno"

    #     tiene_fuente = any([
    #         ruta_doc_local,
    #         directorio_doc_local,
    #         url_doc,
    #         (owner_doc and repo_doc and ruta_doc_github),
    #     ])

    #     if tiene_fuente:
    #         terminos = OpenAICliente.extraer_terminos(diferencia)
    #         termino_busqueda = " ".join(terminos[:3]) if terminos else mensaje[:60]
    #         processor = MarkdownProcessor()

    #         # Obtener TODOS los fragmentos según la fuente (sin filtrar aún)
    #         todos_fragmentos: list[Fragmento] = []

    #         if url_doc:
    #             todos_fragmentos = await processor.fragmentar_desde_url(url_doc)

    #         elif owner_doc and repo_doc and ruta_doc_github:
    #             # [B] Correlación temporal: buscar la versión del doc vigente al momento del commit
    #             ref_doc = "HEAD"
    #             if fecha_commit:
    #                 sha_historico = await gh.get_sha_doc_en_fecha(
    #                     owner_doc, repo_doc, ruta_doc_github, fecha_commit
    #                 )
    #                 if sha_historico:
    #                     ref_doc = sha_historico
    #                     version_doc_sha = sha_historico

    #             contenido, url_fuente = await gh.get_archivo_markdown(
    #                 owner_doc, repo_doc, ruta_doc_github, ref=ref_doc
    #             )
    #             todos_fragmentos = processor.fragmentar(contenido, url_fuente)

    #         elif directorio_doc_local:
    #             todos_fragmentos = processor.fragmentar_directorio(directorio_doc_local)

    #         else:
    #             todos_fragmentos = processor.indexar_archivo(ruta_doc_local).fragmentos

    #         # [A] Búsqueda semántica con embeddings; fallback léxico si falla
    #         if todos_fragmentos:
    #             try:
    #                 fragmentos = await ia.buscar_con_embeddings(todos_fragmentos, termino_busqueda, 5)
    #                 metodo_busqueda = "embeddings"
    #             except Exception as exc:
    #                 fragmentos = processor._top_fragmentos(todos_fragmentos, termino_busqueda, 5)
    #                 metodo_busqueda = "lexica"

    #     # 3. Llamar a OpenAI para generar la explicación
    #     explicacion = await ia.explicar_commit(diferencia, mensaje, fragmentos, modelo)

    #     return ExplicacionCommit(
    #         sha=sha,
    #         sha_corto=sha[:7],
    #         mensaje_commit=mensaje,
    #         explicacion=explicacion,
    #         fragmentos_usados=len(fragmentos),
    #         modelo=modelo,
    #         metodo_busqueda=metodo_busqueda,
    #         version_doc_sha=version_doc_sha,
    #     ).model_dump()

    @mcp.tool()
    async def obtener_archivo(
        owner: str,
        repo: str,
        ruta: str,
        ref: str = "HEAD",
    ) -> dict:
        """
        Descarga el contenido de cualquier archivo de texto de un repositorio
        de GitHub (código fuente, configuración, documentación, etc.).

        Args:
            owner: Propietario del repositorio (usuario u organización).
            repo: Nombre del repositorio.
            ruta: Ruta al archivo dentro del repositorio (ej: 'src/main.py',
                  'docs/guia.md', 'requirements.txt').
            ref: SHA, rama o tag desde donde leer el archivo.
                 Por defecto 'HEAD' (último commit de la rama principal).

        Returns:
            Dict con: ruta, sha, tamanio en bytes, html_url y contenido del archivo.
        """
        client = _cliente()
        return await client.get_archivo(owner, repo, ruta, ref)

    @mcp.tool()
    async def obtener_diferencia_commits(
        owner: str,
        repo: str,
        base: str,
        head: str,
        incluir_patch: bool = True,
    ) -> dict:
        """
        Compara dos commits, ramas o tags de un repositorio y devuelve los
        archivos cambiados con su diff unificado.

        Args:
            owner: Propietario del repositorio (usuario u organización).
            repo: Nombre del repositorio.
            base: SHA, nombre de rama o tag del punto de partida (commit más antiguo).
            head: SHA, nombre de rama o tag del punto de llegada (commit más reciente).
            incluir_patch: Si True (por defecto) incluye el diff unificado de cada
                           archivo. Usa False para obtener solo estadísticas sin el
                           contenido del diff.

        Returns:
            DiferenciaCommits con: SHAs base y head, lista de commits intermedios,
            estadísticas globales (adiciones/eliminaciones totales) y lista de
            archivos cambiados con ruta, estado, estadísticas y patch opcional.
        """
        client = _cliente()
        diferencia = await client.get_diferencia_commits(owner, repo, base, head, incluir_patch)
        return diferencia.model_dump()

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
