import os

import openai
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


def get_openai_client() -> openai.AsyncOpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY no está configurado. "
            "Crea un archivo .env con tu clave de OpenAI."
        )
    return openai.AsyncOpenAI(api_key=api_key)
