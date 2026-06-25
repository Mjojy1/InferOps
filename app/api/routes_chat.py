"""Chat endpoint: RAG Q&A or autonomous agent incident triage."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.schemas import ChatMode, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1", tags=["copilot"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    services = request.app.state.services
    if body.mode == ChatMode.agent:
        return services.answer_agent(body.query, service=body.service)
    return services.answer_rag(body.query, top_k=body.top_k)
