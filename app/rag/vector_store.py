"""A small in-memory vector store backed by NumPy (cosine similarity).

Deliberately dependency-light: no external vector DB is required to run the
demo. The interface (`add_texts` / `search`) mirrors what you would later swap
for FAISS, Chroma, or pgvector in production.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.rag.embeddings import Embedder


@dataclass
class Document:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


class VectorStore:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self.docs: list[Document] = []
        self._matrix: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.docs)

    def clear(self) -> None:
        self.docs = []
        self._matrix = None

    def add_texts(self, items: list[tuple[str, dict]]) -> int:
        if not items:
            return 0
        texts = [text for text, _ in items]
        vectors = np.asarray(self.embedder.embed(texts), dtype=np.float32)
        for (text, meta) in items:
            self.docs.append(Document(id=str(len(self.docs)), text=text, metadata=meta))
        self._matrix = vectors if self._matrix is None else np.vstack([self._matrix, vectors])
        return len(items)

    def search(self, query: str, top_k: int = 4) -> list[tuple[Document, float]]:
        if not self.docs or self._matrix is None:
            return []
        q = np.asarray(self.embedder.embed([query])[0], dtype=np.float32)
        q_norm = q / (np.linalg.norm(q) + 1e-9)
        m_norm = self._matrix / (np.linalg.norm(self._matrix, axis=1, keepdims=True) + 1e-9)
        sims = m_norm @ q_norm
        top_idx = np.argsort(-sims)[:top_k]
        return [(self.docs[i], float(sims[i])) for i in top_idx]
