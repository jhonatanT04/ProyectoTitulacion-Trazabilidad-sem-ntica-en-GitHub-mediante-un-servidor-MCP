from mcp.server.fastmcp import FastMCP

from ServidorMCP.setting.conf import get_github_client


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
