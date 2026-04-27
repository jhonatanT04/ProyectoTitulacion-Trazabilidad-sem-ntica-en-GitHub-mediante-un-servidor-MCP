from pydantic import BaseModel

from ServidorMCP.models.GitHubModels.ArchivoDiff import ArchivoDiff
from ServidorMCP.models.GitHubModels.Commit import Commit


class DiferenciaCommits(BaseModel):
    base_sha: str
    base_sha_corto: str
    head_sha: str
    head_sha_corto: str
    commits_intermedios: list[Commit]
    total_commits: int
    adiciones_total: int
    eliminaciones_total: int
    archivos_cambiados: list[ArchivoDiff]
