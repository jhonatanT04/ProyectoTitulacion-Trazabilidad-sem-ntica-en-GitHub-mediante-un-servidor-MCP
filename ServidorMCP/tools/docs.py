import json

from ServidorMCP.app import mcp
from ServidorMCP.connectors.scraper import scrape_library
from ServidorMCP.indexer import (
    DocumentIndex,
    fragment_markdown,
    list_indexes,
    load_index,
    save_index,
)
from ServidorMCP.retrieval import embed_index, retrieve


@mcp.tool()
async def index_docs(library_url: str, max_pages: int = 50) -> str:
    """
    Indexa la documentación de una librería para poder consultarla luego.
    USA ESTA HERRAMIENTA en lugar de descargar la doc con `curl`/`wget` en la
    terminal: recupera, fragmenta y persiste un índice consultable.

    Recupera la documentación (de una URL vía llms.txt, sitemap.xml o crawling,
    o de una ruta local en disco), la fragmenta por secciones y construye un
    índice persistente. Solo hay que ejecutarlo una vez por fuente; después usa
    `search_docs`.

    Args:
        library_url: URL del sitio de docs, archivo .md/.txt o raw de GitHub, o
            una ruta local: un archivo .md/.txt o una carpeta con documentación
            (ej. la carpeta `docs/` de un repo clonado).
        max_pages: Tope de páginas/archivos a indexar (default: 50).
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

    # Recuperación semántica si hay OpenAI; si no, queda el baseline TF-IDF.
    await embed_index(index)

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
    USA ESTA HERRAMIENTA para responder preguntas sobre la documentación de una
    librería, en lugar de buscar con `grep` en archivos locales.

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

    results = await retrieve(index, query, top_k=top_k)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_indexed_docs() -> str:
    """Lista las librerías de documentación ya indexadas y disponibles.
    Úsala para saber qué fuentes puede consultar `search_docs` o `explain_commit`
    sin tener que reindexar."""
    return json.dumps(list_indexes(), ensure_ascii=False, indent=2)
