from pydantic import BaseModel


class Fragmento(BaseModel):
    id: str
    titulo: str
    nivel: int
    contenido: str
    ruta_archivo: str
    posicion: int
