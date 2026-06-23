"""
Orquestación de la recuperación de documentación.

Decide entre recuperación semántica (embeddings de OpenAI) y el baseline TF-IDF:
si hay OPENAI_API_KEY y la API responde, se usan embeddings; ante cualquier
fallo o ausencia de clave, se recae en TF-IDF de forma transparente.
"""
import logging

from ServidorMCP.config import OPENAI_API_KEY
from ServidorMCP.connectors.openai import OpenAIConnector
from ServidorMCP.indexer import DocumentIndex

logger = logging.getLogger(__name__)


async def embed_index(index: DocumentIndex) -> str:
    """
    Calcula y adjunta los embeddings del corpus al índice (best-effort).

    Devuelve el modo resultante: 'embeddings' si se generaron, 'tfidf' si no
    había clave o la API falló (el índice queda con su matriz TF-IDF).
    """
    if not OPENAI_API_KEY or index.size == 0:
        return "tfidf"
    try:
        vectors = await OpenAIConnector().embed(index.corpus_texts())
        index.set_embeddings(vectors)
        return "embeddings"
    except Exception as exc:  # red/clave/cuota: degradamos a TF-IDF
        logger.warning("Embeddings no disponibles, usando TF-IDF: %s", exc)
        return "tfidf"


async def retrieve(index: DocumentIndex, query: str, top_k: int) -> list[dict]:
    """
    Recupera los fragmentos más relevantes para `query`.

    Si el índice tiene embeddings, embebe la consulta y busca por similitud
    semántica; si falla o no hay embeddings, usa TF-IDF.
    """
    if index.has_embeddings and OPENAI_API_KEY:
        try:
            query_embedding = (await OpenAIConnector().embed([query]))[0]
            return index.search(query, top_k=top_k, query_embedding=query_embedding)
        except Exception as exc:
            logger.warning("Embedding de consulta falló, usando TF-IDF: %s", exc)
    return index.search(query, top_k=top_k)
