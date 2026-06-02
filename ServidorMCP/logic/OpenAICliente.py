import re

import openai

from ServidorMCP.models.GitHubModels.DiferenciaCommits import DiferenciaCommits
from ServidorMCP.models.SemanticText.Fragmento import Fragmento

EMBEDDING_MODEL = "text-embedding-3-small"

MAX_DIFF_CHARS = 6_000

SYSTEM_PROMPT = """Eres un analista senior de software especializado en trazabilidad semántica.
Tu tarea es analizar los cambios de un commit de Git y generar una explicación técnica
en lenguaje natural, correlacionando el diff con la documentación técnica relevante disponible.

Estructura siempre tu respuesta en estas secciones:
## Resumen
## Cambios principales
## Contexto de la documentación
## Impacto técnico"""


class OpenAICliente:
    def __init__(self, client: openai.AsyncOpenAI) -> None:
        self._client = client

    @staticmethod
    def extraer_terminos(diferencia: DiferenciaCommits) -> list[str]:
        """
        Extrae términos clave del diff para guiar la búsqueda en documentación.
        Incluye nombres de archivos modificados y funciones/clases detectadas en los patches.
        """
        terminos: set[str] = set()

        for archivo in diferencia.archivos_cambiados:
            nombre = archivo.ruta.split("/")[-1]
            sin_ext = nombre.rsplit(".", 1)[0]
            if sin_ext and sin_ext not in ("__init__", "index", "mod"):
                terminos.add(sin_ext)

        patron = re.compile(r'^[+-]\s*(?:def|class)\s+(\w+)', re.MULTILINE)
        for archivo in diferencia.archivos_cambiados:
            if archivo.patch:
                for m in patron.finditer(archivo.patch):
                    terminos.add(m.group(1))

        return list(terminos)[:5]

    @staticmethod
    def _formatear_diff(diferencia: DiferenciaCommits) -> str:
        partes: list[str] = []
        total = 0

        for archivo in diferencia.archivos_cambiados:
            if total >= MAX_DIFF_CHARS:
                partes.append("\n... (archivos restantes omitidos por longitud)")
                break

            encabezado = (
                f"### {archivo.ruta} [{archivo.estado}]"
                f" (+{archivo.adiciones}/-{archivo.eliminaciones})\n"
            )
            partes.append(encabezado)
            total += len(encabezado)

            if archivo.patch and total < MAX_DIFF_CHARS:
                espacio = MAX_DIFF_CHARS - total
                patch = archivo.patch
                if len(patch) > espacio:
                    patch = patch[:espacio] + "\n... (patch truncado)"
                bloque = f"```diff\n{patch}\n```\n"
                partes.append(bloque)
                total += len(patch)

        return "\n".join(partes) if partes else "Sin cambios de código disponibles."

    @staticmethod
    def _formatear_fragmentos(fragmentos: list[Fragmento]) -> str:
        if not fragmentos:
            return "No se encontró documentación relevante para los cambios de este commit."

        partes: list[str] = []
        for i, f in enumerate(fragmentos, 1):
            jerarquia = " › ".join(f.jerarquia) if f.jerarquia else ""
            ubicacion = f"{jerarquia} › {f.titulo}" if jerarquia else f.titulo

            if f.tipo == "codigo":
                lang = f.lenguaje or ""
                partes.append(
                    f"**Fragmento {i} — Código ({ubicacion}):**\n```{lang}\n{f.contenido}\n```"
                )
            else:
                partes.append(f"**Fragmento {i} — {ubicacion}:**\n{f.contenido}")

        return "\n\n".join(partes)

    async def buscar_con_embeddings(
        self,
        fragmentos: list[Fragmento],
        termino: str,
        max_resultados: int = 5,
    ) -> list[Fragmento]:
        """
        Clasifica fragmentos por similitud semántica al término usando embeddings.

        Genera embeddings para todos los fragmentos y la query en una sola
        llamada a la API (batch). Usa cosine similarity para rankear.

        Args:
            fragmentos: Lista completa de fragmentos a clasificar.
            termino: Término o frase de búsqueda (normalmente extraído del diff).
            max_resultados: Número máximo de fragmentos a retornar.

        Returns:
            Lista de fragmentos ordenados por similitud semántica descendente.
        """
        if not fragmentos:
            return []

        # Texto representativo de cada fragmento: título + primeros 400 chars de contenido
        textos = [
            f"{f.titulo}. {f.contenido}"[:500]
            for f in fragmentos
        ]

        response = await self._client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=textos + [termino],
        )

        data = response.data
        query_emb: list[float] = data[-1].embedding
        frag_embs: list[list[float]] = [item.embedding for item in data[:-1]]

        def _cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x ** 2 for x in a) ** 0.5
            nb = sum(x ** 2 for x in b) ** 0.5
            return dot / (na * nb) if na and nb else 0.0

        scores = sorted(
            zip(frag_embs, fragmentos),
            key=lambda t: _cosine(query_emb, t[0]),
            reverse=True,
        )

        resultado = [f for _, f in scores[:max_resultados]]
        return resultado

    async def explicar_commit(
        self,
        diferencia: DiferenciaCommits,
        mensaje_commit: str,
        fragmentos: list[Fragmento],
        modelo: str = "gpt-4o-mini",
    ) -> str:
        """
        Construye el prompt de correlación semántica y llama a la API de OpenAI
        para generar una explicación en lenguaje natural del commit.

        Args:
            diferencia: Resultado de get_diferencia_commits con el diff del commit.
            mensaje_commit: Mensaje del commit a explicar.
            fragmentos: Fragmentos de documentación relevante (puede ser lista vacía).
            modelo: Modelo de OpenAI a utilizar. Por defecto 'gpt-4o'.

        Returns:
            Texto de explicación generado por el modelo.
        """
        archivos_lista = "\n".join(
            f"- {a.ruta} [{a.estado}] (+{a.adiciones}/-{a.eliminaciones})"
            for a in diferencia.archivos_cambiados
        )

        diff_formateado = self._formatear_diff(diferencia)
        docs_formateadas = self._formatear_fragmentos(fragmentos)

        user_prompt = f"""## Commit
SHA: {diferencia.head_sha}
Mensaje: {mensaje_commit}

## Archivos modificados
{archivos_lista}

## Diff (cambios en el código)
{diff_formateado}

## Documentación relevante
{docs_formateadas}

Explica este commit de forma técnica y precisa siguiendo las secciones indicadas."""

        respuesta = await self._client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        return respuesta.choices[0].message.content or ""
