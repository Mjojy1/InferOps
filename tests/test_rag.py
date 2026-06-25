"""RAG layer tests: chunking, indexing and retrieval relevance."""
from __future__ import annotations

import pytest

from app.rag.chunking import chunk_text
from app.services import Services


@pytest.fixture()
def services() -> Services:
    svc = Services(force_offline=True)
    svc.ingest()
    return svc


def test_chunking_respects_size_and_is_nonempty():
    text = "\n\n".join(f"Paragraph number {i} with some content." for i in range(20))
    chunks = chunk_text(text, chunk_size=120, overlap=20)
    assert chunks
    assert all(isinstance(c, str) and c.strip() for c in chunks)


def test_ingest_indexes_runbooks(services: Services):
    assert len(services.store) > 0
    assert services.embedder.backend == "fallback"


def test_retrieval_finds_oomkill_runbook(services: Services):
    hits = services.retriever.retrieve("OOMKilled CrashLoopBackOff memory limit exceeded", top_k=3)
    assert hits
    top_sources = [doc.metadata["source"] for doc, _ in hits]
    assert "pod_crashloop_oomkill.md" in top_sources


def test_rag_answer_includes_citations(services: Services):
    response = services.answer_rag("how do I fix disk pressure no space left on device?")
    assert response.answer
    assert response.citations
    assert response.inference.backend == "fallback"
