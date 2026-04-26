from pydantic import BaseModel

from ServidorMCP.models.SemanticText.Fragmento import Fragmento


class ResultadoBusqueda(BaseModel):
    termino: str
    total: int
    fragmentos: list[Fragmento]
