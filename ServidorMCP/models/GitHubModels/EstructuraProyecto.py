from pydantic import BaseModel

from ServidorMCP.models.GitHubModels.ArchivoArbol import ArchivoArbol


class EstructuraProyecto(BaseModel):
    commit_sha: str
    commit_sha_corto: str
    mensaje_commit: str
    autor: str
    fecha: str
    total_archivos: int
    total_directorios: int
    entradas: list[ArchivoArbol]
