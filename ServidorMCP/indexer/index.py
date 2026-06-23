import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ServidorMCP.indexer.fragment import Fragment


class DocumentIndex:
    """
    Índice de fragmentos de documentación Markdown con dos modos de recuperación:

      - TF-IDF (sklearn): siempre disponible, determinista, sin red. Es el
        baseline y el fallback.
      - Embeddings: si se adjuntan vectores con `set_embeddings`, la búsqueda
        usa similitud semántica por coseno sobre esos vectores.

    `search` usa embeddings cuando hay matriz de embeddings y se le pasa el
    embedding de la consulta; en cualquier otro caso recae en TF-IDF.
    """

    def __init__(self):
        self._fragments: list[Fragment] = []
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self._matrix = None
        self._embeddings: np.ndarray | None = None

    @property
    def size(self) -> int:
        return len(self._fragments)

    @property
    def has_embeddings(self) -> bool:
        return self._embeddings is not None

    @property
    def mode(self) -> str:
        """Modo de recuperación activo: 'embeddings' o 'tfidf'."""
        return "embeddings" if self.has_embeddings else "tfidf"

    def add(self, fragments: list[Fragment]) -> None:
        """Agrega fragmentos al índice y reconstruye la matriz TF-IDF."""
        self._fragments.extend(fragments)
        texts = [f"{f.title} {f.content}" for f in self._fragments]
        self._matrix = self._vectorizer.fit_transform(texts)
        # Los embeddings (si los había) quedan obsoletos al cambiar el corpus.
        self._embeddings = None

    def corpus_texts(self) -> list[str]:
        """Texto de cada fragmento para embeber (incluye ruta de sección)."""
        return [f"{f.section_path}: {f.content}" for f in self._fragments]

    def set_embeddings(self, vectors: list[list[float]] | np.ndarray) -> None:
        """Adjunta los embeddings del corpus (uno por fragmento, en orden)."""
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.shape[0] != len(self._fragments):
            raise ValueError(
                f"embeddings ({matrix.shape[0]}) no coinciden con "
                f"fragmentos ({len(self._fragments)})"
            )
        self._embeddings = matrix

    def search(
        self,
        query: str,
        top_k: int = 5,
        query_embedding: list[float] | np.ndarray | None = None,
    ) -> list[dict]:
        """
        Busca los fragmentos más relevantes para una consulta.

        Si el índice tiene embeddings y se pasa `query_embedding`, usa similitud
        semántica; de lo contrario, usa TF-IDF.

        Returns:
            Lista de dicts con title, section_path, content (truncado), source,
            score y method ('embeddings' | 'tfidf').
        """
        if not self._fragments:
            return []

        if query_embedding is not None and self._embeddings is not None:
            q = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
            scores = cosine_similarity(q, self._embeddings).flatten()
            method = "embeddings"
        else:
            if self._matrix is None:
                return []
            query_vec = self._vectorizer.transform([query])
            scores = cosine_similarity(query_vec, self._matrix).flatten()
            method = "tfidf"

        top_indices = scores.argsort()[-top_k:][::-1]
        return [
            {
                "title": self._fragments[idx].title,
                "section_path": self._fragments[idx].section_path,
                "content": self._fragments[idx].content[:600],
                "source": self._fragments[idx].source,
                "score": round(float(scores[idx]), 4),
                "method": method,
            }
            for idx in top_indices
            if scores[idx] > 0
        ]

    def clear(self) -> None:
        self._fragments = []
        self._matrix = None
        self._embeddings = None

    def save(self, path: str | Path) -> None:
        """Persiste el índice (fragmentos + TF-IDF + embeddings) en disco."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(
                {
                    "fragments": self._fragments,
                    "vectorizer": self._vectorizer,
                    "matrix": self._matrix,
                    "embeddings": self._embeddings,
                },
                fh,
            )

    @classmethod
    def load(cls, path: str | Path) -> "DocumentIndex":
        """Reconstruye un índice persistido previamente con `save`."""
        with Path(path).open("rb") as fh:
            data = pickle.load(fh)
        index = cls()
        index._fragments = data["fragments"]
        index._vectorizer = data["vectorizer"]
        index._matrix = data["matrix"]
        index._embeddings = data.get("embeddings")  # compat: índices viejos
        return index
