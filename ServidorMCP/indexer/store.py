"""
Almacén de índices de documentación persistidos en disco.

Cada librería indexada se identifica por su URL/fuente y se guarda como:
  - <slug>.pkl   → el DocumentIndex serializado (fragmentos + TF-IDF).
  - <slug>.json  → metadatos (fuente, fecha, nº de páginas y fragmentos).
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ServidorMCP.config import INDEX_DIR
from ServidorMCP.indexer.index import DocumentIndex


def _slug(library: str) -> str:
    """Genera un identificador de archivo estable y legible a partir de la fuente."""
    base = re.sub(r"^https?://", "", library.strip().lower())
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:60] or "doc"
    digest = hashlib.sha1(library.encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def _index_path(library: str) -> Path:
    return Path(INDEX_DIR) / f"{_slug(library)}.pkl"


def _meta_path(library: str) -> Path:
    return Path(INDEX_DIR) / f"{_slug(library)}.json"


def save_index(library: str, index: DocumentIndex, pages: int) -> dict:
    """Guarda el índice y sus metadatos. Devuelve los metadatos."""
    index.save(_index_path(library))
    meta = {
        "library": library,
        "slug": _slug(library),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "pages": pages,
        "fragments": index.size,
    }
    _meta_path(library).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def load_index(library: str) -> DocumentIndex | None:
    """Carga el índice persistido de una librería, o None si no existe."""
    path = _index_path(library)
    return DocumentIndex.load(path) if path.exists() else None


def load_meta(library: str) -> dict | None:
    path = _meta_path(library)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def list_indexes() -> list[dict]:
    """Lista los metadatos de todas las librerías indexadas."""
    directory = Path(INDEX_DIR)
    if not directory.exists():
        return []
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in sorted(directory.glob("*.json"))
    ]
