from pydantic import BaseModel


class ArchivoArbol(BaseModel):
    ruta: str
    tipo: str        # "blob" (archivo) | "tree" (directorio)
    sha: str
    tamanio: int | None  # bytes; None para directorios
