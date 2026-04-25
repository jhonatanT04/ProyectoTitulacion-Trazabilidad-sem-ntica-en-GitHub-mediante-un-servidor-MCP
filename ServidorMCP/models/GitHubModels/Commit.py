from pydantic import BaseModel

class Commit(BaseModel):
    sha: str
    sha_corto: str
    mensaje: str
    autor: str
    email_autor: str
    fecha: str
    url: str
