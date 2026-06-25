"""Inference router: prefers local Ollama, falls back to the offline engine.

The router is the single entry point the rest of the app uses for generation
and embeddings. It records inference telemetry and transparently degrades to the
deterministic engine if Ollama is disabled or unreachable.
"""
from __future__ import annotations

from typing import Sequence

from app.config import settings
from app.inference.base import GenerationResult, Message, ToolSpec
from app.inference.fallback import FallbackEngine
from app.inference.metrics import metrics
from app.inference.ollama_client import OllamaClient


class InferenceRouter:
    def __init__(self, force_offline: bool = False) -> None:
        self.ollama = OllamaClient()
        self.fallback = FallbackEngine()
        self._ollama_ok: bool | None = False if force_offline else None

    def ollama_available(self, refresh: bool = False) -> bool:
        if self._ollama_ok is None or refresh:
            self._ollama_ok = settings.enable_ollama and self.ollama.available()
        return bool(self._ollama_ok)

    @property
    def active_backend(self) -> str:
        return self.ollama.name if self.ollama_available() else self.fallback.name

    def _backend(self):
        return self.ollama if self.ollama_available() else self.fallback

    def chat(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
        tools: Sequence[ToolSpec] | None = None,
    ) -> GenerationResult:
        backend = self._backend()
        try:
            result = backend.chat(
                messages,
                model=model,
                temperature=temperature,
                json_mode=json_mode,
                tools=tools,
            )
        except Exception:
            # A runtime failure (e.g. Ollama died mid-session) — degrade once.
            self._ollama_ok = False
            result = self.fallback.chat(
                messages,
                model=model,
                temperature=temperature,
                json_mode=json_mode,
                tools=tools,
            )
        metrics.record(result)
        return result

    def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
        backend = self._backend()
        try:
            return backend.embed(texts, model=model)
        except Exception:
            self._ollama_ok = False
            return self.fallback.embed(texts, model=model)
