import logging
import re
import unicodedata
from glob import glob
from html.parser import HTMLParser
from pathlib import Path

log = logging.getLogger(__name__)

from ServidorMCP.models.SemanticText.Fragmento import Fragmento
from ServidorMCP.models.SemanticText.IndiceDocumento import IndiceDocumento
from ServidorMCP.models.SemanticText.ResultadoBusqueda import ResultadoBusqueda

# Encabezados que NO estén dentro de bloques de código
_RE_HEADER = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#+)?$', re.MULTILINE)
# Bloques de código cercados (``` ... ```)
_RE_CODE_BLOCK = re.compile(r'^```(\w*)\s*\n(.*?)^```', re.MULTILINE | re.DOTALL)
_RE_BLANK_LINES = re.compile(r'\n{3,}')


# --------------------------------------------------------------------------- #
#  Utilidades                                                                  #
# --------------------------------------------------------------------------- #

def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^\w\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


class _HTMLTextExtractor(HTMLParser):
    """Extrae texto plano de HTML descartando scripts, estilos y navegación."""

    _IGNORAR = {'script', 'style', 'nav', 'footer', 'head', 'aside', 'noscript'}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self._partes: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._IGNORAR:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self._IGNORAR:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            texto = data.strip()
            if texto:
                self._partes.append(texto)

    def texto(self) -> str:
        return '\n'.join(self._partes)


# --------------------------------------------------------------------------- #
#  Procesador principal                                                         #
# --------------------------------------------------------------------------- #

class MarkdownProcessor:

    # ----------------------------------------------------------------------- #
    #  Fragmentación                                                            #
    # ----------------------------------------------------------------------- #

    def _bloques_codigo(self, contenido: str) -> list[tuple[int, int, str, str]]:
        """Devuelve lista de (inicio, fin, lenguaje, código) de cada bloque ```."""
        bloques = [
            (m.start(), m.end(), m.group(1).strip() or "text", m.group(2).strip())
            for m in _RE_CODE_BLOCK.finditer(contenido)
        ]
        log.debug("Bloques de código detectados: %d", len(bloques))
        return bloques

    def _en_bloque_codigo(self, pos: int, bloques: list) -> bool:
        return any(s <= pos < e for s, e, *_ in bloques)

    def fragmentar(self, contenido: str, fuente: str) -> list[Fragmento]:
        """
        Divide el contenido Markdown en fragmentos semánticos:
        - Una sección por encabezado (sin el código que contiene)
        - Un fragmento independiente por cada bloque de código
        La jerarquía de encabezados se preserva como breadcrumb.
        """
        log.info("Fragmentando fuente: %s (%d caracteres)", fuente, len(contenido))
        bloques = self._bloques_codigo(contenido)

        # Solo headers fuera de bloques de código
        headers = [
            m for m in _RE_HEADER.finditer(contenido)
            if not self._en_bloque_codigo(m.start(), bloques)
        ]
        log.debug("Encabezados detectados fuera de código: %d", len(headers))

        fragmentos: list[Fragmento] = []
        # Pila de (nivel, titulo) para construir la jerarquía
        pila: list[tuple[int, str]] = []
        posicion = 0

        def _breadcrumb(nivel_actual: int) -> list[str]:
            return [t for n, t in pila if n < nivel_actual]

        def _actualizar_pila(nivel: int, titulo: str) -> None:
            while pila and pila[-1][0] >= nivel:
                pila.pop()
            pila.append((nivel, titulo))

        # Contenido anterior al primer header
        inicio_primer_header = headers[0].start() if headers else len(contenido)
        intro = contenido[:inicio_primer_header].strip()
        # Eliminar bloques de código del intro
        intro_limpio = self._quitar_codigo(intro, bloques, 0)
        if intro_limpio:
            log.debug("Intro detectada (%d caracteres)", len(intro_limpio))
            fragmentos.append(Fragmento(
                id=f"{fuente}#intro",
                titulo="Introducción",
                nivel=0,
                tipo="intro",
                jerarquia=[],
                lenguaje=None,
                contenido=intro_limpio,
                ruta_archivo=fuente,
                posicion=posicion,
            ))
            posicion += 1

        for i, header in enumerate(headers):
            nivel = len(header.group(1))
            titulo = header.group(2).strip()
            jerarquia = _breadcrumb(nivel)
            _actualizar_pila(nivel, titulo)

            inicio_cuerpo = header.end()
            fin_cuerpo = headers[i + 1].start() if i + 1 < len(headers) else len(contenido)
            cuerpo_raw = contenido[inicio_cuerpo:fin_cuerpo]

            # Bloques de código dentro de esta sección
            bloques_seccion = [
                (s, e, lang, code) for s, e, lang, code in bloques
                if inicio_cuerpo <= s < fin_cuerpo
            ]
            log.debug(
                "[%s] H%d '%s' | jerarquía=%s | bloques_código=%d",
                fuente, nivel, titulo, jerarquia, len(bloques_seccion),
            )

            # Texto de la sección sin los bloques de código
            cuerpo_texto = self._quitar_codigo(cuerpo_raw, bloques_seccion, inicio_cuerpo)

            if cuerpo_texto:
                fragmentos.append(Fragmento(
                    id=f"{fuente}#{i}",
                    titulo=titulo,
                    nivel=nivel,
                    tipo="seccion",
                    jerarquia=jerarquia,
                    lenguaje=None,
                    contenido=cuerpo_texto,
                    ruta_archivo=fuente,
                    posicion=posicion,
                ))
                posicion += 1

            # Fragmento independiente por cada bloque de código
            for j, (_, _, lang, code) in enumerate(bloques_seccion):
                if not code.strip():
                    continue
                log.debug("  Bloque código %d: lang=%s (%d líneas)", j, lang, code.count('\n') + 1)
                fragmentos.append(Fragmento(
                    id=f"{fuente}#{i}_code{j}",
                    titulo=f"{titulo} — ejemplo {'(' + lang + ')' if lang and lang != 'text' else '(código)'}",
                    nivel=nivel,
                    tipo="codigo",
                    jerarquia=jerarquia + [titulo],
                    lenguaje=lang if lang and lang != 'text' else None,
                    contenido=code,
                    ruta_archivo=fuente,
                    posicion=posicion,
                ))
                posicion += 1

        log.info("Fragmentación completa: %d fragmentos generados", len(fragmentos))
        return fragmentos

    def _quitar_codigo(
        self,
        texto: str,
        bloques: list,
        offset: int,
    ) -> str:
        """Elimina bloques de código de un fragmento de texto."""
        for s, e, *_ in reversed(bloques):
            rel_s = s - offset
            rel_e = e - offset
            if 0 <= rel_s and rel_e <= len(texto):
                texto = texto[:rel_s] + texto[rel_e:]
        return _RE_BLANK_LINES.sub('\n\n', texto).strip()

    # ----------------------------------------------------------------------- #
    #  Búsqueda y puntuación                                                   #
    # ----------------------------------------------------------------------- #

    def _puntuar(self, fragmento: Fragmento, termino: str) -> int:
        """
        Calcula la relevancia de un fragmento para el término dado.

        Pesos:
          - Frase exacta en título      → +30
          - Frase exacta en jerarquía   → +15
          - Frase exacta en contenido   → +10
          - Palabra individual en título → +5 por ocurrencia
          - Palabra individual en jerarquía → +3 por ocurrencia
          - Palabra individual en contenido → +1 por ocurrencia
          - Fragmento de código con match → +5 adicional
        """
        t_norm = _normalizar(termino)
        palabras = [p for p in t_norm.split() if len(p) > 1]

        titulo_n = _normalizar(fragmento.titulo)
        contenido_n = _normalizar(fragmento.contenido)
        jerarquia_n = ' '.join(_normalizar(j) for j in fragmento.jerarquia)

        puntuacion = 0

        # Frase exacta
        puntuacion += titulo_n.count(t_norm) * 30
        puntuacion += jerarquia_n.count(t_norm) * 15
        puntuacion += contenido_n.count(t_norm) * 10

        # Palabras individuales
        for palabra in palabras:
            puntuacion += titulo_n.count(palabra) * 5
            puntuacion += jerarquia_n.count(palabra) * 3
            puntuacion += contenido_n.count(palabra) * 1

        # Bonus para fragmentos de código con match
        if fragmento.tipo == "codigo" and t_norm in contenido_n:
            puntuacion += 5

        return puntuacion

    def _top_fragmentos(
        self,
        fragmentos: list[Fragmento],
        termino: str,
        max_resultados: int,
    ) -> list[Fragmento]:
        log.info("Puntuando %d fragmentos para término '%s'", len(fragmentos), termino)
        puntuados = [(self._puntuar(f, termino), f) for f in fragmentos]
        puntuados = [(p, f) for p, f in puntuados if p > 0]
        puntuados.sort(key=lambda x: x[0], reverse=True)
        for puntuacion, f in puntuados[:max_resultados]:
            log.debug("  [%d pts] %s (tipo=%s)", puntuacion, f.titulo, f.tipo)
        log.info("Fragmentos relevantes encontrados: %d (máx solicitado: %d)", len(puntuados), max_resultados)
        return [f for _, f in puntuados[:max_resultados]]

    # ----------------------------------------------------------------------- #
    #  Fuentes                                                                 #
    # ----------------------------------------------------------------------- #

    def indexar_archivo(self, ruta_archivo: str) -> IndiceDocumento:
        log.info("Indexando archivo: %s", ruta_archivo)
        ruta = Path(ruta_archivo)
        if not ruta.exists():
            log.error("Archivo no encontrado: %s", ruta_archivo)
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_archivo}")
        if ruta.suffix.lower() not in ('.md', '.markdown'):
            log.error("El archivo no es Markdown: %s", ruta_archivo)
            raise ValueError(f"El archivo no es Markdown: {ruta_archivo}")
        contenido = ruta.read_text(encoding='utf-8')
        log.debug("Archivo leído: %d caracteres", len(contenido))
        fragmentos = self.fragmentar(contenido, ruta_archivo)
        return IndiceDocumento(
            ruta_archivo=ruta_archivo,
            total_fragmentos=len(fragmentos),
            fragmentos=fragmentos,
        )

    def buscar(self, termino: str, ruta_archivo: str, max_resultados: int = 5) -> ResultadoBusqueda:
        """Busca en un archivo Markdown local."""
        log.info("Búsqueda en archivo | término='%s' | archivo=%s", termino, ruta_archivo)
        indice = self.indexar_archivo(ruta_archivo)
        relevantes = self._top_fragmentos(indice.fragmentos, termino, max_resultados)
        return ResultadoBusqueda(termino=termino, total=len(relevantes), fragmentos=relevantes)

    def buscar_en_directorio(self, termino: str, directorio: str, max_resultados: int = 5) -> ResultadoBusqueda:
        """Busca recursivamente en todos los archivos Markdown de un directorio."""
        log.info("Búsqueda en directorio | término='%s' | directorio=%s", termino, directorio)
        archivos = (
            glob(f"{directorio}/**/*.md", recursive=True)
            + glob(f"{directorio}/**/*.markdown", recursive=True)
        )
        log.debug("Archivos Markdown encontrados: %d", len(archivos))
        if not archivos:
            log.warning("No se encontraron archivos Markdown en: %s", directorio)
            return ResultadoBusqueda(termino=termino, total=0, fragmentos=[])

        todos: list[Fragmento] = []
        for archivo in archivos:
            try:
                todos.extend(self.indexar_archivo(archivo).fragmentos)
            except Exception as exc:
                log.warning("Error al indexar '%s': %s", archivo, exc)
                continue

        log.debug("Total de fragmentos acumulados de todos los archivos: %d", len(todos))
        relevantes = self._top_fragmentos(todos, termino, max_resultados)
        return ResultadoBusqueda(termino=termino, total=len(relevantes), fragmentos=relevantes)

    def buscar_en_contenido(self, termino: str, contenido: str, fuente: str, max_resultados: int = 5) -> ResultadoBusqueda:
        """Busca en contenido Markdown ya cargado en memoria."""
        log.info("Búsqueda en contenido en memoria | término='%s' | fuente=%s", termino, fuente)
        fragmentos = self.fragmentar(contenido, fuente)
        relevantes = self._top_fragmentos(fragmentos, termino, max_resultados)
        return ResultadoBusqueda(termino=termino, total=len(relevantes), fragmentos=relevantes)

    async def buscar_en_url(self, termino: str, url: str, max_resultados: int = 5) -> ResultadoBusqueda:
        """
        Descarga documentación desde una URL y busca el término.
        Soporta páginas HTML (ReadTheDocs, GitHub Pages, etc.) y
        archivos Markdown crudos (raw.githubusercontent.com).
        """
        import httpx

        log.info("Búsqueda en URL | término='%s' | url=%s", termino, url)
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "ANIA-MCP/1.0"})
            response.raise_for_status()
            contenido_raw = response.text

        log.debug("Respuesta recibida: %d caracteres | content-type=%s",
                  len(contenido_raw), response.headers.get('content-type', ''))

        es_markdown = (
            url.endswith(('.md', '.markdown'))
            or 'raw.githubusercontent.com' in url
            or response.headers.get('content-type', '').startswith('text/plain')
        )

        if es_markdown:
            log.debug("Fuente detectada como Markdown crudo")
            return self.buscar_en_contenido(termino, contenido_raw, url, max_resultados)

        log.debug("Fuente detectada como HTML — extrayendo texto")
        extractor = _HTMLTextExtractor()
        extractor.feed(contenido_raw)
        texto = extractor.texto()
        log.debug("Texto extraído del HTML: %d caracteres", len(texto))
        return self.buscar_en_contenido(termino, texto, url, max_resultados)
