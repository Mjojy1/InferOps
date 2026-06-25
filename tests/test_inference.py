"""Inference layer tests (offline fallback engine)."""
from __future__ import annotations

from app.inference.base import Message
from app.inference.fallback import EMBED_DIM
from app.inference.metrics import InferenceMetrics
from app.inference.router import InferenceRouter


def test_router_uses_fallback_when_offline():
    router = InferenceRouter(force_offline=True)
    assert router.ollama_available() is False
    assert router.active_backend == "fallback"


def test_fallback_chat_produces_text_and_records_metrics():
    router = InferenceRouter(force_offline=True)
    result = router.chat([Message("user", "checkout-api is throwing OOMKilled errors")])
    assert result.backend == "fallback"
    assert isinstance(result.text, str) and result.text
    assert result.latency_ms >= 0


def test_fallback_embeddings_have_fixed_dimension():
    router = InferenceRouter(force_offline=True)
    vectors = router.embed(["high cpu throttling", "disk pressure"])
    assert len(vectors) == 2
    assert all(len(v) == EMBED_DIM for v in vectors)


def test_metrics_snapshot_accumulates():
    m = InferenceMetrics()
    router = InferenceRouter(force_offline=True)
    res = router.fallback.chat([Message("user", "hello world")])
    m.record(res)
    snap = m.snapshot()
    assert snap["requests"] == 1
    assert "fallback" in snap["by_backend"]
