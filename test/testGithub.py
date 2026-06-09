"""
Test Sprint 1 — Conector GitHub
Prueba: get_commits y get_pull_requests con distintos parámetros.
"""
import asyncio
from ServerMCP.connectors.github import GitHubConnector
from ServerMCP.config import GITHUB_TOKEN

OWNER = "anthropics"
REPO = "anthropic-sdk-python"


def separador(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


async def test_commits_basico():
    """Obtiene los últimos 5 commits de la rama principal."""
    separador("TEST 1 — Commits básicos (limit=5)")
    gh = GitHubConnector(GITHUB_TOKEN)
    commits = await gh.get_commits(OWNER, REPO, limit=5)

    assert isinstance(commits, list), "Debe retornar una lista"
    assert len(commits) <= 5, "No debe superar el límite"
    assert all("sha" in c and "message" in c and "author" in c for c in commits)

    for c in commits:
        print(f"  [{c['sha_short']}] {c['date']} | {c['author']}")
        print(f"           {c['message'].splitlines()[0]}")

    print(f"\n  OK — {len(commits)} commits obtenidos")


async def test_commits_con_rama():
    """Obtiene commits de una rama específica."""
    separador("TEST 2 — Commits en rama 'main' (limit=3)")
    gh = GitHubConnector(GITHUB_TOKEN)
    commits = await gh.get_commits(OWNER, REPO, branch="main", limit=3)

    assert isinstance(commits, list)
    for c in commits:
        print(f"  [{c['sha_short']}] {c['message'].splitlines()[0]}")

    print(f"\n  OK — {len(commits)} commits en rama 'main'")


async def test_commits_con_fechas():
    """Filtra commits entre dos fechas."""
    separador("TEST 3 — Commits con filtro de fechas")
    gh = GitHubConnector(GITHUB_TOKEN)
    commits = await gh.get_commits(
        OWNER, REPO,
        since="2026-01-01T00:00:00Z",
        until="2026-06-07T23:59:59Z",
        limit=5,
    )

    assert isinstance(commits, list)
    for c in commits:
        print(f"  [{c['sha_short']}] {c['date']} | {c['message'].splitlines()[0]}")

    print(f"\n  OK — {len(commits)} commits en el rango de fechas")


async def test_pull_requests_cerrados():
    """Obtiene los últimos 5 PRs cerrados."""
    separador("TEST 4 — Pull Requests cerrados (limit=5)")
    gh = GitHubConnector(GITHUB_TOKEN)
    prs = await gh.get_pull_requests(OWNER, REPO, state="closed", limit=5)

    assert isinstance(prs, list)
    assert all("number" in pr and "title" in pr and "state" in pr for pr in prs)

    for pr in prs:
        merged = pr["merged_at"] or "no mergeado"
        print(f"  #{pr['number']} [{pr['state']}] {pr['title']}")
        print(f"           Autor: {pr['author']} | Merged: {merged}")

    print(f"\n  OK — {len(prs)} PRs cerrados obtenidos")


async def test_pull_requests_abiertos():
    """Obtiene PRs abiertos."""
    separador("TEST 5 — Pull Requests abiertos (limit=3)")
    gh = GitHubConnector(GITHUB_TOKEN)
    prs = await gh.get_pull_requests(OWNER, REPO, state="open", limit=3)

    assert isinstance(prs, list)
    for pr in prs:
        print(f"  #{pr['number']} {pr['title']}")
        print(f"           Rama: {pr['head_branch']} → {pr['base_branch']}")

    print(f"\n  OK — {len(prs)} PRs abiertos obtenidos")


async def main():
    print("\nINICIANDO TESTS SPRINT 1 — Conector GitHub")
    print(f"Repositorio: {OWNER}/{REPO}")

    tests = [
        test_commits_basico,
        test_commits_con_rama,
        test_commits_con_fechas,
        test_pull_requests_cerrados,
        test_pull_requests_abiertos,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n  FALLO — {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  RESULTADO: {passed} pasados / {failed} fallidos")
    print(f"{'='*60}\n")


asyncio.run(main())
