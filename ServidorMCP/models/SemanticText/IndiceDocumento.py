from pydantic import BaseModel

from ServidorMCP.models.SemanticText.Fragmento import Fragmento


class IndiceDocumento(BaseModel):
    ruta_archivo: str
    total_fragmentos: int
    fragmentos: list[Fragmento]
