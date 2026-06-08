import httpx
from pathlib import Path


async def read_markdown(source: str) -> str:
    """
    Lee contenido Markdown desde una URL o ruta local.

    Args:
        source: URL (http/https) o ruta absoluta/relativa a un archivo .md
    """
    if source.startswith("http://") or source.startswith("https://"):
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(source)
            response.raise_for_status()
            return response.text
    else:
        return Path(source).read_text(encoding="utf-8")
