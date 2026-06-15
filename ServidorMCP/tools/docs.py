import json

from ServerMCP.app import mcp
from ServerMCP.connectors.scraper import scrape_library
from ServerMCP.indexer import (
    DocumentIndex,
    fragment_markdown,
    list_indexes,
    load_index,
    save_index,
)


@mcp.tool()
async def index_docs(library_url: str, max_pages: int = 50) -> str:
    """
    Indexa la documentación de una librería para poder consultarla luego.

    Recupera la documentación (vía llms.txt, sitemap.xml o crawling), la
    fragmenta por secciones y construye un índice persistente en disco. Solo
    hay que ejecutarlo una vez por librería; después usa `search_docs`.

    Args:
        library_url: URL base del sitio de docs, archivo .md/.txt o raw de GitHub.
        max_pages: Tope de páginas a descargar (default: 50).
    """
    pages = await scrape_library(library_url, max_pages=max_pages)
    if not pages:
        return json.dumps(
            {"error": f"No se pudo recuperar documentación de: {library_url}"},
            ensure_ascii=False,
        )

    index = DocumentIndex()
    for page in pages:
        index.add(fragment_markdown(page["markdown"], page["url"]))

    meta = save_index(library_url, index, pages=len(pages))
    return json.dumps(
        {"status": "indexado", **meta, "sources": [p["url"] for p in pages][:20]},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
async def search_docs(library_url: str, query: str, top_k: int = 5) -> str:
    """
    Busca fragmentos relevantes en una librería ya indexada con `index_docs`.

    Args:
        library_url: La misma URL/fuente usada al ejecutar `index_docs`.
        query: Término o concepto técnico a buscar.
        top_k: Número de fragmentos más relevantes a retornar (default: 5).
    """
    index = load_index(library_url)
    if index is None:
        return json.dumps(
            {"error": f"'{library_url}' no está indexada. Ejecuta primero index_docs."},
            ensure_ascii=False,
        )

    results = index.search(query, top_k=top_k)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_indexed_docs() -> str:
    """Lista las librerías de documentación ya indexadas y disponibles."""
    return json.dumps(list_indexes(), ensure_ascii=False, indent=2)
