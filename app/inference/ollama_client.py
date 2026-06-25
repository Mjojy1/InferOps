"""Ollama-backed local inference client (chat + embeddings)."""
from __future__ import annotations

import time
from typing import Sequence

import httpx

from app.config import settings
from app.inference.base import GenerationResult, Message, ToolSpec


class OllamaClient:
    """Talks to a local Ollama server over its HTTP API.

    Raises on transport errors so the router can fall back gracefully.
    """

    name = "ollama"

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def available(self) -> bool:
        """Cheap reachability probe against the Ollama API."""
        try:
            resp = self._client.get("/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def chat(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
        tools: Sequence[ToolSpec] | None = None,  # described in-prompt; kept for parity
    ) -> GenerationResult:
        model = model or settings.llm_model
        payload: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"

        start = time.perf_counter()
        resp = self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.perf_counter() - start) * 1000.0

        text = data.get("message", {}).get("content", "")
        return GenerationResult(
            text=text,
            model=model,
            backend=self.name,
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            latency_ms=round(latency_ms, 2),
        )

    def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
        model = model or settings.embedding_model
        vectors: list[list[float]] = []
        for text in texts:
            resp = self._client.post("/api/embeddings", json={"model": model, "prompt": text})
            resp.raise_for_status()
            vectors.append(resp.json().get("embedding", []))
        return vectors
