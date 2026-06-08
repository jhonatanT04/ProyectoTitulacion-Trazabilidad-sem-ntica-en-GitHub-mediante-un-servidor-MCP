"""
Construcción de prompts dinámicos que correlacionan commits de GitHub
con fragmentos de documentación técnica.
"""

SYSTEM_PROMPT = """Eres un asistente experto en ingeniería de software.
Tu tarea es analizar commits de un repositorio y explicar, con base en la
documentación técnica proporcionada, por qué se realizaron esos cambios,
qué problema resuelven y qué parte de la documentación los justifica.
Responde en español de forma clara y estructurada."""


def build_explain_prompt(commit: dict, doc_fragments: list[dict]) -> str:
    """
    Construye el prompt dinámico que cruza datos del commit con documentación.

    Args:
        commit: Dict con sha, message, author, date, files (con patches).
        doc_fragments: Lista de fragmentos relevantes de la documentación.
    """
    # Sección de commit
    files_section = ""
    for f in commit.get("files", []):
        files_section += f"\n  [{f['status']}] {f['filename']} (+{f['additions']} / -{f['deletions']})"
        if f.get("patch"):
            files_section += f"\n```diff\n{f['patch']}\n```"

    commit_section = f"""## Commit analizado
- SHA: {commit['sha_short']} ({commit['sha']})
- Autor: {commit['author']} <{commit['email']}>
- Fecha: {commit['date']}
- Mensaje: {commit['message']}

### Archivos modificados:{files_section or ' (sin archivos disponibles)'}"""

    # Sección de documentación
    if doc_fragments:
        docs_section = "## Documentación técnica relevante\n"
        for i, frag in enumerate(doc_fragments, 1):
            docs_section += f"\n### [{i}] {frag['section_path']} (score: {frag['score']})\n"
            docs_section += f"{frag['content']}\n"
    else:
        docs_section = "## Documentación técnica\n(No se encontraron fragmentos relevantes para este commit.)"

    question = """## Pregunta
Con base en el commit y la documentación proporcionada:
1. ¿Qué problema o necesidad resuelve este cambio?
2. ¿Qué parte de la documentación técnica justifica o explica este cambio?
3. ¿Qué impacto tiene en el sistema?"""

    return f"{commit_section}\n\n{docs_section}\n\n{question}"
