import re
from pathlib import Path
from glob import glob

from ServidorMCP.models.SemanticText.Fragmento import Fragmento
from ServidorMCP.models.SemanticText.IndiceDocumento import IndiceDocumento
from ServidorMCP.models.SemanticText.ResultadoBusqueda import ResultadoBusqueda

_PATRON_HEADER = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownProcessor:

    def fragmentar(self, contenido: str, ruta_archivo: str) -> list[Fragmento]:
        """Divide el contenido Markdown en fragmentos semánticos por sección."""
        matches = list(_PATRON_HEADER.finditer(contenido))
        fragmentos: list[Fragmento] = []

        if not matches:
            return [
                Fragmento(
                    id=f"{ruta_archivo}#0",
                    titulo="(sin título)",
                    nivel=0,
                    contenido=contenido.strip(),
                    ruta_archivo=ruta_archivo,
                    posicion=0,
                )
            ]

        # Contenido previo al primer encabezado
        intro = contenido[: matches[0].start()].strip()
        if intro:
            fragmentos.append(
                Fragmento(
                    id=f"{ruta_archivo}#intro",
                    titulo="Introducción",
                    nivel=0,
                    contenido=intro,
                    ruta_archivo=ruta_archivo,
                    posicion=0,
                )
            )

        for i, match in enumerate(matches):
            nivel = len(match.group(1))
            titulo = match.group(2).strip()
            inicio = match.end()
            fin = matches[i + 1].start() if i + 1 < len(matches) else len(contenido)
            cuerpo = contenido[inicio:fin].strip()

            fragmentos.append(
                Fragmento(
                    id=f"{ruta_archivo}#{i}",
                    titulo=titulo,
                    nivel=nivel,
                    contenido=cuerpo,
                    ruta_archivo=ruta_archivo,
                    posicion=i + 1,
                )
            )

        return fragmentos

    def indexar_archivo(self, ruta_archivo: str) -> IndiceDocumento:
        """Lee un archivo Markdown y devuelve su índice de fragmentos."""
        ruta = Path(ruta_archivo)

        if not ruta.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_archivo}")
        if ruta.suffix.lower() not in (".md", ".markdown"):
            raise ValueError(f"El archivo no es Markdown: {ruta_archivo}")

        contenido = ruta.read_text(encoding="utf-8")
        fragmentos = self.fragmentar(contenido, ruta_archivo)

        return IndiceDocumento(
            ruta_archivo=ruta_archivo,
            total_fragmentos=len(fragmentos),
            fragmentos=fragmentos,
        )

    def _puntuar_fragmentos(
        self,
        fragmentos: list[Fragmento],
        termino: str,
        max_resultados: int,
    ) -> list[Fragmento]:
        termino_lower = termino.lower()
        puntuados: list[tuple[int, Fragmento]] = []
        for fragmento in fragmentos:
            puntuacion = (
                fragmento.titulo.lower().count(termino_lower) * 3
                + fragmento.contenido.lower().count(termino_lower)
            )
            if puntuacion > 0:
                puntuados.append((puntuacion, fragmento))
        puntuados.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in puntuados[:max_resultados]]

    def buscar(
        self,
        termino: str,
        ruta_archivo: str,
        max_resultados: int = 5,
    ) -> ResultadoBusqueda:
        """Busca en un archivo Markdown local dado su ruta."""
        indice = self.indexar_archivo(ruta_archivo)
        relevantes = self._puntuar_fragmentos(indice.fragmentos, termino, max_resultados)
        return ResultadoBusqueda(termino=termino, total=len(relevantes), fragmentos=relevantes)

    def buscar_en_directorio(
        self,
        termino: str,
        directorio: str,
        max_resultados: int = 5,
    ) -> ResultadoBusqueda:
        """Busca en todos los archivos Markdown (.md / .markdown) de un directorio local."""
        archivos = glob(f"{directorio}/**/*.md", recursive=True) + \
                   glob(f"{directorio}/**/*.markdown", recursive=True)

        if not archivos:
            return ResultadoBusqueda(termino=termino, total=0, fragmentos=[])

        todos: list[Fragmento] = []
        for archivo in archivos:
            try:
                indice = self.indexar_archivo(archivo)
                todos.extend(indice.fragmentos)
            except Exception:
                continue

        relevantes = self._puntuar_fragmentos(todos, termino, max_resultados)
        return ResultadoBusqueda(termino=termino, total=len(relevantes), fragmentos=relevantes)

    def buscar_en_contenido(
        self,
        termino: str,
        contenido: str,
        fuente: str,
        max_resultados: int = 5,
    ) -> ResultadoBusqueda:
        """Busca en contenido Markdown ya cargado en memoria (ej: descargado de GitHub)."""
        fragmentos = self.fragmentar(contenido, fuente)
        relevantes = self._puntuar_fragmentos(fragmentos, termino, max_resultados)
        return ResultadoBusqueda(termino=termino, total=len(relevantes), fragmentos=relevantes)
