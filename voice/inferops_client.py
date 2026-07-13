"""Calls a running InferOps instance over its real HTTP contract:

    POST /api/v1/chat   { "query": ..., "mode": "agent"|"rag", "service": ... }

This keeps the voice layer fully decoupled from InferOps internals — it talks to
the same endpoint the web UI and curl examples use.
"""
from __future__ import annotations

import httpx

from . import config

# Response-body keys tried in order. InferOps returns a grounded answer; adjust
# this list to your exact schema if your field is named differently (check
# GET /docs on your running instance).
_ANSWER_KEYS = ("answer", "final_answer", "response", "message", "content", "text")


def triage(
    query: str,
    *,
    mode: str | None = None,
    service: str | None = None,
    timeout: float = 120.0,
) -> tuple[str, dict]:
    """Send a query to InferOps and return (spoken_answer, full_json)."""
    payload: dict = {"query": query, "mode": mode or config.DEFAULT_MODE}
    svc = service or config.DEFAULT_SERVICE
    if svc:
        payload["service"] = svc

    resp = httpx.post(
        f"{config.INFEROPS_URL}/api/v1/chat",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict):
        for key in _ANSWER_KEYS:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip(), data
        # Fall back to the whole payload if we can't find a known answer field.
        return str(data), data
    return str(data), {"raw": data}


def pick_mode(query: str) -> str:
    """Tiny heuristic: 'how do I…' style questions -> single-shot RAG, else agent.

    Purely a convenience for the voice demo; override with INFEROPS_MODE.
    """
    q = query.lower().strip()
    if q.startswith(("how do i", "how can i", "what is", "what's the runbook")):
        return "rag"
    return config.DEFAULT_MODE
