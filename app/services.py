"""Service container: builds and wires the inference, RAG and agent stack.

A single :class:`Services` instance is created at app startup and stored on
``app.state``. It owns the vector index and exposes the two product workflows:
``answer_rag`` (grounded Q&A) and ``answer_agent`` (autonomous incident triage).
"""
from __future__ import annotations

from pathlib import Path

from app.agents.orchestrator import AgentOrchestrator
from app.agents.tools import build_default_tools
from app.config import settings
from app.inference.router import InferenceRouter
from app.models.schemas import (
    AgentStepModel,
    ChatResponse,
    Citation,
    HealthResponse,
    InferenceStats,
)
from app.rag.chunking import chunk_text
from app.rag.embeddings import Embedder
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.telemetry.observability import TelemetryStore


class Services:
    def __init__(self, force_offline: bool = False) -> None:
        self.router = InferenceRouter(force_offline=force_offline)
        self.embedder = Embedder(self.router)
        self.store = VectorStore(self.embedder)
        self.retriever = Retriever(self.store)
        self.telemetry = TelemetryStore.load()

    # ----- indexing ---------------------------------------------------------
    def ingest(self, path: str | None = None) -> tuple[int, int]:
        """(Re)index runbooks. Returns (documents, chunks)."""
        runbook_dir = Path(path) if path else Path(settings.data_dir) / "runbooks"
        files = sorted(runbook_dir.glob("*.md"))
        self.store.clear()

        items: list[tuple[str, dict]] = []
        for file in files:
            text = file.read_text(encoding="utf-8")
            for chunk in chunk_text(text, settings.chunk_size, settings.chunk_overlap):
                items.append((chunk, {"source": file.name}))

        self.store.add_texts(items)
        return len(files), len(items)

    # ----- workflows --------------------------------------------------------
    def answer_rag(self, query: str, top_k: int | None = None) -> ChatResponse:
        hits = self.retriever.retrieve(query, top_k=top_k or settings.top_k)
        messages, citations = self.retriever.build_messages(query, hits)
        result = self.router.chat(messages, temperature=0.2)
        stats = InferenceStats(
            backend=result.backend,
            model=result.model,
            llm_calls=1,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=round(result.latency_ms, 2),
            tokens_per_second=result.tokens_per_second,
        )
        return ChatResponse(
            mode="rag",
            answer=result.text.strip(),
            citations=citations,
            steps=[],
            inference=stats,
        )

    def answer_agent(self, query: str, service: str | None = None) -> ChatResponse:
        citations: list[Citation] = []
        tools = build_default_tools(self.telemetry, self.retriever, citations)
        orchestrator = AgentOrchestrator(self.router, tools, settings.max_agent_steps)
        run = orchestrator.run(query, service=service)

        tps = (
            round(run.completion_tokens / (run.latency_ms / 1000.0), 2)
            if run.latency_ms
            else 0.0
        )
        stats = InferenceStats(
            backend=run.backend,
            model=run.model,
            llm_calls=run.llm_calls,
            prompt_tokens=run.prompt_tokens,
            completion_tokens=run.completion_tokens,
            latency_ms=round(run.latency_ms, 2),
            tokens_per_second=tps,
        )
        steps = [
            AgentStepModel(
                step=s.step,
                thought=s.thought,
                action=s.action,
                action_input=s.action_input,
                observation=s.observation,
            )
            for s in run.steps
        ]
        return ChatResponse(
            mode="agent",
            answer=run.answer,
            citations=_dedupe_citations(citations),
            steps=steps,
            inference=stats,
        )

    # ----- health -----------------------------------------------------------
    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            environment=settings.environment,
            ollama_available=self.router.ollama_available(),
            active_backend=self.router.active_backend,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            documents_indexed=len(self.store),
        )


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    best: dict[str, Citation] = {}
    for c in citations:
        existing = best.get(c.source)
        if existing is None or c.score > existing.score:
            best[c.source] = c
    ordered = sorted(best.values(), key=lambda c: c.score, reverse=True)
    return [
        Citation(index=i, source=c.source, score=c.score, snippet=c.snippet)
        for i, c in enumerate(ordered, start=1)
    ]
