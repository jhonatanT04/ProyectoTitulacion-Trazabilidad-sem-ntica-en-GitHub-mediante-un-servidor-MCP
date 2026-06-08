import json

from ServerMCP.app import mcp
from ServerMCP.config import GITHUB_TOKEN
from ServerMCP.connectors.github import GitHubConnector
from ServerMCP.connectors.markdown import read_markdown
from ServerMCP.connectors.openai import OpenAIConnector
from ServerMCP.indexer import DocumentIndex, fragment_markdown
from ServerMCP.prompt_builder import SYSTEM_PROMPT, build_explain_prompt


def _github() -> GitHubConnector:
    return GitHubConnector(GITHUB_TOKEN)


@mcp.tool()
async def explain_commit(
    owner: str,
    repo: str,
    sha: str,
    doc_source: str,
    top_k: int = 3,
) -> str:
    """
    Explica un commit específico cruzando sus cambios con la documentación técnica.
    Usa OpenAI para generar una explicación en lenguaje natural.

    Args:
        owner: Propietario del repositorio de GitHub.
        repo: Nombre del repositorio.
        sha: SHA del commit a explicar (completo o los primeros 7 caracteres).
        doc_source: URL o ruta local a documentación Markdown relevante.
        top_k: Número de fragmentos de documentación a incluir en el contexto (default: 3).
    """
    # 1. Obtener detalles del commit (mensaje + diffs)
    gh = _github()
    commit = await gh.get_commit(owner, repo, sha)

    # 2. Buscar fragmentos de documentación relevantes al mensaje del commit
    doc_content = await read_markdown(doc_source)
    fragments = fragment_markdown(doc_content, doc_source)
    index = DocumentIndex()
    index.add(fragments)

    # Usar el mensaje del commit como query de búsqueda
    query = commit["message"].splitlines()[0]
    doc_fragments = index.search(query, top_k=top_k)

    # 3. Construir prompt dinámico
    prompt = build_explain_prompt(commit, doc_fragments)

    # 4. Llamar a OpenAI para generar la explicación
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
