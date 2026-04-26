import os

from dotenv import load_dotenv

from ServidorMCP.logic.GitHubCliente import GitHubClient

load_dotenv()


def get_github_client() -> GitHubClient:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError(
            "GITHUB_TOKEN no está configurado. "
            "Crea un archivo .env con tu token de GitHub."
        )
    return GitHubClient(token)
