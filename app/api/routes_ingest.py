"""Runbook ingestion endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.schemas import IngestRequest, IngestResponse

router = APIRouter(prefix="/api/v1", tags=["rag"])


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: Request, body: IngestRequest | None = None) -> IngestResponse:
    services = request.app.state.services
    path = body.path if body else None
    documents, chunks = services.ingest(path)
    return IngestResponse(
        documents_indexed=documents,
        chunks_indexed=chunks,
        embedding_backend=services.embedder.backend,
    )
