from pydantic import BaseModel


class ArchivoDiff(BaseModel):
    ruta: str
    estado: str  # added, removed, modified, renamed, copied
    adiciones: int
    eliminaciones: int
    cambios: int
    patch: str | None = None  # diff unificado; None si el archivo es binario o muy grande
