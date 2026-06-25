"""Pydantic request/response schemas for the InferOps API."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    rag = "rag"
    agent = "agent"


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        examples=["checkout-api p99 latency is spiking and pods keep restarting — what do I do?"],
    )
    mode: ChatMode = ChatMode.agent
    service: str | None = Field(default=None, examples=["checkout-api"])
    top_k: int | None = Field(default=None, ge=1, le=20)


class Citation(BaseModel):
    index: int
    source: str
    score: float
    snippet: str


class AgentStepModel(BaseModel):
    step: int
    thought: str
    action: str
    action_input: str
    observation: str


class InferenceStats(BaseModel):
    backend: str
    model: str
    llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    tokens_per_second: float


class ChatResponse(BaseModel):
    mode: ChatMode
    answer: str
    citations: list[Citation] = []
    steps: list[AgentStepModel] = []
    inference: InferenceStats


class IngestRequest(BaseModel):
    path: str | None = Field(
        default=None, description="Optional path to a directory of .md runbooks."
    )


class IngestResponse(BaseModel):
    documents_indexed: int
    chunks_indexed: int
    embedding_backend: str


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    ollama_available: bool
    active_backend: str
    llm_model: str
    embedding_model: str
    documents_indexed: int
