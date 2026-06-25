"""Retriever: turns a query into ranked context + citations and a grounded prompt."""
from __future__ import annotations

from app.inference.base import Message
from app.models.schemas import Citation
from app.rag.vector_store import Document, VectorStore

RAG_SYSTEM_PROMPT = (
    "You are InferOps, a Site Reliability Engineering assistant. Answer strictly "
    "using the provided context from internal runbooks. Cite sources inline as [n]. "
    "If the context is insufficient, say you don't have enough information. Be "
    "concise and actionable."
)


class Retriever:
    def __init__(self, store: VectorStore) -> None:
        self.store = store

    def retrieve(self, query: str, top_k: int = 4) -> list[tuple[Document, float]]:
        return self.store.search(query, top_k=top_k)

    def build_messages(
        self, query: str, hits: list[tuple[Document, float]]
    ) -> tuple[list[Message], list[Citation]]:
        lines: list[str] = []
        citations: list[Citation] = []
        for i, (doc, score) in enumerate(hits, start=1):
            source = doc.metadata.get("source", "unknown")
            snippet = " ".join(doc.text.split())
            lines.append(f"[{i}] ({source}) {snippet}")
            citations.append(
                Citation(
                    index=i,
                    source=source,
                    score=round(score, 4),
                    snippet=doc.text.strip()[:280],
                )
            )

        context = "\n".join(lines) if lines else "(no relevant context found)"
        user_prompt = (
            "Answer the production-incident question using only the context below. "
            "Cite sources inline with [n].\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}"
        )
        messages = [
            Message("system", RAG_SYSTEM_PROMPT),
            Message("user", user_prompt),
        ]
        return messages, citations
