"""Agent layer tests: the orchestrator runs tools and produces a grounded answer."""
from __future__ import annotations

import pytest

from app.services import Services


@pytest.fixture()
def services() -> Services:
    svc = Services(force_offline=True)
    svc.ingest()
    return svc


def test_agent_runs_tools_and_returns_answer(services: Services):
    response = services.answer_agent(
        "checkout-api pods keep restarting with OOMKilled", service="checkout-api"
    )
    assert response.mode == "agent"
    assert response.answer
    assert len(response.steps) >= 3

    actions = [s.action for s in response.steps]
    assert "search_runbooks" in actions
    assert "query_metrics" in actions


def test_agent_reports_inference_telemetry(services: Services):
    response = services.answer_agent("inventory-worker has disk pressure", service="inventory-worker")
    inf = response.inference
    assert inf.llm_calls >= 1
    assert inf.backend == "fallback"
    assert inf.completion_tokens > 0


def test_agent_surfaces_runbook_citations(services: Services):
    response = services.answer_agent(
        "checkout-api OOMKilled CrashLoopBackOff", service="checkout-api"
    )
    sources = {c.source for c in response.citations}
    assert any(s.endswith(".md") for s in sources)
