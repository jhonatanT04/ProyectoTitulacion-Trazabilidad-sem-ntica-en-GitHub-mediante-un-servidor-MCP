from openai import AsyncOpenAI

from ServerMCP.config import OPENAI_API_KEY, OPENAI_MODEL


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
