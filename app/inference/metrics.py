"""In-process inference metrics registry (tokens, latency, backend mix)."""
from __future__ import annotations

import threading

from app.inference.base import GenerationResult


class InferenceMetrics:
    """Thread-safe aggregate counters for LLM inference."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.requests = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.latency_ms_total = 0.0
        self.by_backend: dict[str, dict[str, float]] = {}
        self.by_model: dict[str, dict[str, float]] = {}

    def record(self, result: GenerationResult) -> None:
        with self._lock:
            self.requests += 1
            self.prompt_tokens += result.prompt_tokens
            self.completion_tokens += result.completion_tokens
            self.latency_ms_total += result.latency_ms
            self._bump(self.by_backend, result.backend, result)
            self._bump(self.by_model, result.model, result)

    @staticmethod
    def _bump(bucket: dict[str, dict[str, float]], key: str, result: GenerationResult) -> None:
        entry = bucket.setdefault(
            key, {"requests": 0.0, "completion_tokens": 0.0, "latency_ms": 0.0}
        )
        entry["requests"] += 1
        entry["completion_tokens"] += result.completion_tokens
        entry["latency_ms"] += result.latency_ms

    def snapshot(self) -> dict:
        with self._lock:
            avg_latency = self.latency_ms_total / self.requests if self.requests else 0.0
            tps = (
                self.completion_tokens / (self.latency_ms_total / 1000.0)
                if self.latency_ms_total
                else 0.0
            )
            return {
                "requests": self.requests,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "avg_latency_ms": round(avg_latency, 2),
                "avg_tokens_per_second": round(tps, 2),
                "by_backend": {k: dict(v) for k, v in self.by_backend.items()},
                "by_model": {k: dict(v) for k, v in self.by_model.items()},
            }


# Process-wide singleton.
metrics = InferenceMetrics()
