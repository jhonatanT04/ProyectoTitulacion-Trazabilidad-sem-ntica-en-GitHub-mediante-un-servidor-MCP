import json

from ServerMCP.app import mcp
from ServerMCP.connectors.markdown import read_markdown
from ServerMCP.indexer import DocumentIndex, fragment_markdown


@mcp.tool()
async def search_docs(
    source: str,
    query: str,
    top_k: int = 5,
) -> str:
    """
    Busca fragmentos relevantes en documentación Markdown dado un término o concepto.

    Args:
        source: URL o ruta local a un archivo Markdown (.md).
        query: Término o concepto a buscar en la documentación.
        top_k: Número de fragmentos más relevantes a retornar (default: 5).
    """
    content = await read_markdown(source)
    fragments = fragment_markdown(content, source)

    index = DocumentIndex()
    index.add(fragments)

    results = index.search(query, top_k=top_k)
    return json.dumps(results, ensure_ascii=False, indent=2)
