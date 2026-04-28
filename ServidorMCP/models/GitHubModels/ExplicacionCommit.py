from pydantic import BaseModel


class ExplicacionCommit(BaseModel):
    sha: str
    sha_corto: str
    mensaje_commit: str
    explicacion: str
    fragmentos_usados: int
    modelo: str
