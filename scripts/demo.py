"""Standalone demo: runs an end-to-end incident triage without the web server.

Usage:
    python -m scripts.demo
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import Services  # noqa: E402

LINE = "═" * 72


def banner(text: str) -> None:
    print(f"\n{LINE}\n  {text}\n{LINE}")


def main() -> None:
    banner("InferOps · Local-Inference SRE Copilot — Demo")

    services = Services()
    documents, chunks = services.ingest()
    health = services.health()
    print(f"  Inference backend : {health.active_backend}")
    print(f"  LLM model         : {health.llm_model}")
    print(f"  Knowledge base    : {documents} runbooks → {chunks} chunks indexed")

    query = "checkout-api p99 latency is spiking and pods keep restarting. What's wrong and how do I fix it?"
    service = "checkout-api"

    banner("AGENT MODE · autonomous incident triage")
    print(f"  Query   : {query}")
    print(f"  Service : {service}\n")

    response = services.answer_agent(query, service=service)

    for step in response.steps:
        print(f"  ┌─ Step {step.step}: {step.action}('{step.action_input}')")
        if step.thought:
            print(f"  │  thought: {step.thought}")
        for line in step.observation.splitlines():
            print(f"  │  {line}")
        print("  └─")

    banner("FINAL ANSWER")
    print(response.answer)

    if response.citations:
        banner("GROUNDED SOURCES (RAG)")
        for c in response.citations:
            print(f"  [{c.index}] {c.source}  (score={c.score})")

    inf = response.inference
    banner("INFERENCE TELEMETRY")
    print(f"  backend={inf.backend}  model={inf.model}  llm_calls={inf.llm_calls}")
    print(
        f"  tokens(out)={inf.completion_tokens}  latency={inf.latency_ms}ms  "
        f"throughput={inf.tokens_per_second} tok/s"
    )
    print()


if __name__ == "__main__":
    main()
