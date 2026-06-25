"""Embedding provider.

Wraps the inference router and *locks* the chosen backend (Ollama or the
deterministic fallback) for the lifetime of the index so that document and query
vectors always share the same dimensionality and distribution.
"""
from __future__ import annotations

from typing import Sequence

from app.inference.router import InferenceRouter


class Embedder:
    def __init__(self, router: InferenceRouter) -> None:
        self.router = router
        # Decide once: keeps document/query embeddings consistent.
        self.backend = "ollama" if router.ollama_available() else "fallback"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.backend == "ollama":
            try:
                return self.router.ollama.embed(list(texts))
            except Exception:
                # Downgrade once; subsequent calls use the fallback consistently.
                self.backend = "fallback"
        return self.router.fallback.embed(list(texts))
