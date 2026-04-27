from pydantic import BaseModel


class Fragmento(BaseModel):
    id: str
    titulo: str
    nivel: int
    tipo: str           # "seccion" | "codigo" | "intro"
    jerarquia: list[str]  # breadcrumb de headers padres (ej: ["Instalación", "Config"])
    lenguaje: str | None  # solo para tipo "codigo" (ej: "python", "bash")
    contenido: str
    ruta_archivo: str
    posicion: int
