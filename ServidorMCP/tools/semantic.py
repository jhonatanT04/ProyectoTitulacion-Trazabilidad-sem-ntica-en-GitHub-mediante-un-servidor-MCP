import json

from ServerMCP.app import mcp
from ServerMCP.config import GITHUB_TOKEN
from ServerMCP.connectors.github import GitHubConnector
from ServerMCP.connectors.openai import OpenAIConnector
from ServerMCP.indexer import load_index
from ServerMCP.prompt_builder import SYSTEM_PROMPT, build_explain_prompt


def _github() -> GitHubConnector:
    return GitHubConnector(GITHUB_TOKEN)


@mcp.tool()
async def explain_commit(
    owner: str,
    repo: str,
    sha: str,
    library_url: str,
    top_k: int = 3,
) -> str:
    """
    Explica un commit específico cruzando sus cambios con la documentación técnica.
    Usa OpenAI para generar una explicación en lenguaje natural.

    Args:
        owner: Propietario del repositorio de GitHub.
        repo: Nombre del repositorio.
        sha: SHA del commit a explicar (completo o los primeros 7 caracteres).
        library_url: Librería ya indexada con `index_docs` (misma URL/fuente).
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
    gh = _github()
    commit = await gh.get_commit(owner, repo, sha)

    # 3. Buscar fragmentos de documentación relevantes al mensaje del commit
    query = commit["message"].splitlines()[0]
    doc_fragments = index.search(query, top_k=top_k)

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
