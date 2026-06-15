"""
Test Sprint 3 — Correlación semántica commits + docs + OpenAI
Prueba: get_commit, build_explain_prompt y explain_commit completo.
"""
import asyncio
from ServidorMCP.config import GITHUB_TOKEN
from ServidorMCP.connectors.github import GitHubConnector
from ServidorMCP.connectors.openai import OpenAIConnector
from ServidorMCP.connectors.markdown import read_markdown
from ServidorMCP.indexer import fragment_markdown, DocumentIndex
from ServidorMCP.prompt_builder import build_explain_prompt, SYSTEM_PROMPT

OWNER = "anthropics"
REPO = "anthropic-sdk-python"
# Commit con lógica real (fix de autenticación)
TARGET_SHA = "49c5395"
# Documentación más completa para mejor cobertura de búsqueda
DOC_SOURCE = "https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/CONTRIBUTING.md"


def separador(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


async def test_get_commit():
    """Obtiene el detalle de un commit específico con sus diffs."""
    separador("TEST 1 — Obtener detalle de un commit (get_commit)")
    gh = GitHubConnector(GITHUB_TOKEN)

    commit = await gh.get_commit(OWNER, REPO, TARGET_SHA)

    assert "sha" in commit
    assert "message" in commit
    assert "files" in commit
    assert isinstance(commit["files"], list)

    print(f"  SHA:    {commit['sha_short']}")
    print(f"  Autor:  {commit['author']}")
    print(f"  Fecha:  {commit['date']}")
    print(f"  Mensaje: {commit['message'].splitlines()[0]}")
    print(f"  Archivos modificados: {len(commit['files'])}")
    for f in commit["files"]:
        print(f"    [{f['status']}] {f['filename']} (+{f['additions']}/-{f['deletions']})")

    print("\n  OK — Detalle del commit obtenido")
    return commit


async def test_build_prompt(commit: dict):
    """Construye el prompt dinámico cruzando commit con documentación."""
    separador("TEST 2 — Construcción del prompt dinámico")

    # Buscar docs relevantes
    content = await read_markdown(DOC_SOURCE)
    fragments = fragment_markdown(content, DOC_SOURCE)
    index = DocumentIndex()
    index.add(fragments)

    query = commit["message"].splitlines()[0]
    doc_fragments = index.search(query, top_k=3)

    prompt = build_explain_prompt(commit, doc_fragments)

    assert isinstance(prompt, str)
    assert len(prompt) > 100
    assert commit["sha_short"] in prompt

    print(f"  Query usada: '{query}'")
    print(f"  Fragmentos de docs encontrados: {len(doc_fragments)}")
    print(f"  Longitud del prompt: {len(prompt)} caracteres")
    print(f"\n  --- Vista previa del prompt ---")
    for line in prompt.splitlines()[:15]:
        print(f"  {line}")
    print(f"  ...")

    print("\n  OK — Prompt dinámico construido correctamente")
    return prompt, doc_fragments


async def test_openai_connector():
    """Verifica la conexión con OpenAI con un mensaje simple."""
    separador("TEST 3 — Conexión con OpenAI")
    openai = OpenAIConnector()

    response = await openai.complete(
        system="Responde siempre en español de forma muy breve.",
        user="¿Qué es un commit en Git? Máximo 2 oraciones.",
    )

    assert isinstance(response, str)
    assert len(response) > 10

    print(f"  Respuesta de OpenAI:")
    print(f"  {response}")
    print("\n  OK — Conexión con OpenAI exitosa")


async def test_explain_commit_completo():
    """Test de integración completo: commit + docs + OpenAI."""
    separador("TEST 4 — Flujo completo: explain_commit")
    gh = GitHubConnector(GITHUB_TOKEN)
    openai = OpenAIConnector()

    commit = await gh.get_commit(OWNER, REPO, TARGET_SHA)

    # Buscar documentación relevante
    content = await read_markdown(DOC_SOURCE)
    fragments = fragment_markdown(content, DOC_SOURCE)
    index = DocumentIndex()
    index.add(fragments)
    query = commit["message"].splitlines()[0]
    doc_fragments = index.search(query, top_k=3)

    # Construir prompt y llamar a OpenAI
    prompt = build_explain_prompt(commit, doc_fragments)
    explanation = await openai.complete(system=SYSTEM_PROMPT, user=prompt)

    assert isinstance(explanation, str)
    assert len(explanation) > 50

    print(f"  Commit analizado: [{commit['sha_short']}] {commit['message'].splitlines()[0]}")
    print(f"  Fragmentos de docs usados: {len(doc_fragments)}")
    print(f"\n  --- Explicación generada por OpenAI ---\n")
    print(explanation)

    print("\n  OK — Flujo completo exitoso")


async def main():
    print("\nINICIANDO TESTS SPRINT 3 — Correlación semántica + OpenAI")
    print(f"Repositorio: {OWNER}/{REPO}")

    passed = 0
    failed = 0
    commit = None

    # Test 1: get_commit
    try:
        commit = await test_get_commit()
        passed += 1
    except Exception as e:
        print(f"\n  FALLO — {e}")
        failed += 1

    # Test 2: build_prompt (depende del commit)
    if commit:
        try:
            await test_build_prompt(commit)
            passed += 1
        except Exception as e:
            print(f"\n  FALLO — {e}")
            failed += 1

    # Test 3: OpenAI connector
    try:
        await test_openai_connector()
        passed += 1
    except Exception as e:
        print(f"\n  FALLO — {e}")
        failed += 1

    # Test 4: flujo completo
    try:
        await test_explain_commit_completo()
        passed += 1
    except Exception as e:
        print(f"\n  FALLO — {e}")
        failed += 1

    print(f"\n{'='*60}")
    print(f"  RESULTADO: {passed} pasados / {failed} fallidos")
    print(f"{'='*60}\n")


asyncio.run(main())
