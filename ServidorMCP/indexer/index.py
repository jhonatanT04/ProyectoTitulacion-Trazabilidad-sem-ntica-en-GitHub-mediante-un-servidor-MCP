import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ServerMCP.indexer.fragment import Fragment


class DocumentIndex:
    """
    Índice TF-IDF sobre fragmentos de documentación Markdown.
    Permite agregar múltiples fuentes y buscar por similitud de texto.
    """

    def __init__(self):
        self._fragments: list[Fragment] = []
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self._matrix = None

    @property
    def size(self) -> int:
        return len(self._fragments)

    def add(self, fragments: list[Fragment]) -> None:
        """Agrega fragmentos al índice y reconstruye la matriz TF-IDF."""
        self._fragments.extend(fragments)
        texts = [f"{f.title} {f.content}" for f in self._fragments]
        self._matrix = self._vectorizer.fit_transform(texts)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Busca los fragmentos más relevantes para una consulta.

        Returns:
            Lista de dicts con title, section_path, content (truncado), source y score.
        """
        if not self._fragments or self._matrix is None:
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        top_indices = scores.argsort()[-top_k:][::-1]

        return [
            {
                "title": self._fragments[idx].title,
                "section_path": self._fragments[idx].section_path,
                "content": self._fragments[idx].content[:600],
                "source": self._fragments[idx].source,
                "score": round(float(scores[idx]), 4),
            }
            for idx in top_indices
            if scores[idx] > 0
        ]

    def clear(self) -> None:
        self._fragments = []
        self._matrix = None

    def save(self, path: str | Path) -> None:
        """Persiste el índice (fragmentos + vectorizador + matriz) en disco."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(
                {
                    "fragments": self._fragments,
                    "vectorizer": self._vectorizer,
                    "matrix": self._matrix,
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
        return index
