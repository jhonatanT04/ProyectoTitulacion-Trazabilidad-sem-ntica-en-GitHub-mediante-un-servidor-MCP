from openai import AsyncOpenAI

from ServidorMCP.config import EMBEDDING_MODEL, OPENAI_API_KEY, OPENAI_MODEL

# Tope de textos por petición de embeddings (la API admite más, pero lotear
# acota el tamaño del payload y la latencia por request).
_EMBED_BATCH = 256


class OpenAIConnector:
    def __init__(self):
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def complete(self, system: str, user: str) -> str:
        """Envía un prompt a OpenAI y retorna la respuesta en texto."""
        response = await self._client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Genera embeddings para una lista de textos (lotea peticiones grandes).
        Devuelve un vector por texto, en el mismo orden de entrada.
        """
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH):
            batch = texts[start:start + _EMBED_BATCH]
            response = await self._client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            vectors.extend(item.embedding for item in response.data)
        return vectors
