from pydantic import BaseModel

class PullRequest(BaseModel):
    numero: int
    titulo: str
    estado: str
    autor: str
    rama_origen: str
    rama_destino: str
    fecha_creacion: str
    fecha_actualizacion: str
    fecha_merge: str | None
    commits: int
    archivos_cambiados: int
    adiciones: int
    eliminaciones: int
    url: str