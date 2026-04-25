from typing import Literal
import httpx
from ServidorMCP.models.GitHubModels.Commit import Commit
from ServidorMCP.models.GitHubModels.PullRequest import PullRequest


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        estado: Literal["open", "closed", "all"] = "open",
        cantidad: int = 30,
    ) -> list[PullRequest]:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {"state": estado, "per_page": min(cantidad, 100)}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            datos = response.json()

        pull_requests = []
        for pr in datos:
            # El endpoint /pulls no incluye stats; se obtienen del endpoint individual
            pr_detail = await self._get_pr_detail(owner, repo, pr["number"])
            pull_requests.append(
                PullRequest(
                    numero=pr["number"],
                    titulo=pr["title"],
                    estado=pr["state"],
                    autor=pr["user"]["login"],
                    rama_origen=pr["head"]["ref"],
                    rama_destino=pr["base"]["ref"],
                    fecha_creacion=pr["created_at"],
                    fecha_actualizacion=pr["updated_at"],
                    fecha_merge=pr.get("merged_at"),
                    commits=pr_detail.get("commits", 0),
                    archivos_cambiados=pr_detail.get("changed_files", 0),
                    adiciones=pr_detail.get("additions", 0),
                    eliminaciones=pr_detail.get("deletions", 0),
                    url=pr["html_url"],
                )
            )
        return pull_requests

    async def _get_pr_detail(self, owner: str, repo: str, numero: int) -> dict:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{numero}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def get_commits(
        self,
        owner: str,
        repo: str,
        rama: str = "main",
        cantidad: int = 30,
    ) -> list[Commit]:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params = {"sha": rama, "per_page": min(cantidad, 100)}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            datos = response.json()

        return [
            Commit(
                sha=c["sha"],
                sha_corto=c["sha"][:7],
                mensaje=c["commit"]["message"].split("\n")[0],  # solo la primera línea
                autor=c["commit"]["author"]["name"],
                email_autor=c["commit"]["author"]["email"],
                fecha=c["commit"]["author"]["date"],
                url=c["html_url"],
            )
            for c in datos
        ]
