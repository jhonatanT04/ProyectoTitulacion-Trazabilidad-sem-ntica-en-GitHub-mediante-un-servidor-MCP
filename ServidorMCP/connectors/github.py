import httpx
from typing import Optional

GITHUB_API_BASE = "https://api.github.com"


class GitHubConnector:
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_commits(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 30,
    ) -> list[dict]:
        """Extrae el historial de commits de un repositorio."""
        params: dict = {"per_page": min(limit, 100)}
        if branch:
            params["sha"] = branch
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            raw = response.json()

        return [
            {
                "sha": c["sha"],
                "sha_short": c["sha"][:7],
                "message": c["commit"]["message"],
                "author": c["commit"]["author"]["name"],
                "email": c["commit"]["author"]["email"],
                "date": c["commit"]["author"]["date"],
                "url": c["html_url"],
            }
            for c in raw
        ]

    async def get_commit(self, owner: str, repo: str, sha: str) -> dict:
        """Extrae el detalle de un commit específico incluyendo los diffs por archivo."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{sha}",
                headers=self.headers,
            )
            response.raise_for_status()
            c = response.json()

        return {
            "sha": c["sha"],
            "sha_short": c["sha"][:7],
            "message": c["commit"]["message"],
            "author": c["commit"]["author"]["name"],
            "email": c["commit"]["author"]["email"],
            "date": c["commit"]["author"]["date"],
            "url": c["html_url"],
            "files": [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "patch": f.get("patch", "")[:1500],
                }
                for f in c.get("files", [])
            ],
        }

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        limit: int = 30,
    ) -> list[dict]:
        """Extrae los pull requests con sus metadatos."""
        params = {
            "state": state,
            "per_page": min(limit, 100),
            "sort": "updated",
            "direction": "desc",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            raw = response.json()

        return [
            {
                "number": pr["number"],
                "title": pr["title"],
                "body": pr["body"] or "",
                "state": pr["state"],
                "author": pr["user"]["login"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "merged_at": pr["merged_at"],
                "base_branch": pr["base"]["ref"],
                "head_branch": pr["head"]["ref"],
                "labels": [label["name"] for label in pr["labels"]],
                "url": pr["html_url"],
            }
            for pr in raw
        ]
