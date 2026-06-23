import json

from mcp.server.fastmcp import Context

from ServidorMCP.app import mcp
from ServidorMCP.connectors.openai import OpenAIConnector
from ServidorMCP.connectors.repo import resolve_repo_auto
from ServidorMCP.indexer import load_index
from ServidorMCP.prompt_builder import SYSTEM_PROMPT, build_explain_prompt
from ServidorMCP.retrieval import retrieve


@mcp.tool()
async def explain_commit(
    sha: str,
    library_url: str,
    repo: str = "",
    top_k: int = 3,
    ctx: Context = None,
) -> str:
    """
    Explica POR QUÉ cambió un commit cruzando sus diffs con la documentación
    técnica de una librería. USA ESTA HERRAMIENTA para preguntas del tipo "por
    qué se hizo este cambio" o "qué relación tiene este commit con la doc"; no
    intentes reconstruir la explicación leyendo `git show` en la terminal.
    Genera la explicación en lenguaje natural con OpenAI.

    Args:
        sha: SHA del commit a explicar (completo o los primeros 7 caracteres).
        library_url: Librería ya indexada con `index_docs` (misma URL/fuente).
        repo: Opcional. Ruta local a un clon git o slug 'owner/repo' de GitHub.
            Si se deja vacío, se usa el repositorio abierto en el IDE.
        top_k: Número de fragmentos de documentación a incluir en el contexto (default: 3).
    """
    # 1. Cargar el índice de documentación persistido
    index = load_index(library_url)
    if index is None:
        import json as _json
        return _json.dumps(
            {"error": f"'{library_url}' no está indexada. Ejecuta primero index_docs."},
            ensure_ascii=False,
        )

    # 2. Obtener detalles del commit (mensaje + diffs)
    source = await resolve_repo_auto(repo, ctx)
    commit = await source.get_commit(sha)

    # 3. Buscar fragmentos de documentación relevantes al mensaje del commit
    query = commit["message"].splitlines()[0]
    doc_fragments = await retrieve(index, query, top_k=top_k)

    # 4. Construir prompt dinámico
    prompt = build_explain_prompt(commit, doc_fragments)

    # 5. Llamar a OpenAI para generar la explicación
    openai = OpenAIConnector()
    explanation = await openai.complete(system=SYSTEM_PROMPT, user=prompt)

    result = {
        "commit": {
            "sha": commit["sha_short"],
            "message": commit["message"].splitlines()[0],
            "author": commit["author"],
            "date": commit["date"],
        },
        "doc_fragments_used": len(doc_fragments),
        "explanation": explanation,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)
