"""Concrete agent tools for incident response.

Each builder closes over the data sources it needs and returns a :class:`Tool`.
The ``search_runbooks`` and ``propose_remediation`` tools perform RAG over the
runbook knowledge base and append to a shared ``citations`` sink so the API can
surface grounded sources alongside the agent's answer.
"""
from __future__ import annotations

import re

from app.agents.base import Tool
from app.config import settings
from app.models.schemas import Citation
from app.rag.retriever import Retriever
from app.telemetry.observability import TelemetryStore

_CMD_RE = re.compile(r"(kubectl|systemctl|helm|docker|journalctl|df\s|du\s|find\s)")


def build_metrics_tool(telemetry: TelemetryStore) -> Tool:
    def run(query: str) -> str:
        service = telemetry.resolve_service(query)
        if not service:
            return (
                "No service resolved from the input. Known services: "
                + ", ".join(telemetry.list_services())
            )
        metrics = telemetry.metrics_for(service) or {}
        lines = [f"Metrics for {service}:"]
        for key, value in metrics.items():
            lines.append(f"  - {key}: {value}")
        return "\n".join(lines)

    return Tool(
        name="query_metrics",
        description=(
            "Fetch current resource and latency metrics (CPU, memory, p99 latency, "
            "error rate, restarts) for a service. Input: a service name or the query."
        ),
        func=run,
    )


def build_logs_tool(telemetry: TelemetryStore) -> Tool:
    def run(query: str) -> str:
        service = telemetry.resolve_service(query)
        if not service:
            return (
                "No service resolved from the input. Known services: "
                + ", ".join(telemetry.list_services())
            )
        logs = telemetry.logs_for(service)
        if not logs:
            return f"No recent logs for {service}."
        return f"Recent logs for {service}:\n" + "\n".join(f"  {ln}" for ln in logs)

    return Tool(
        name="search_logs",
        description=(
            "Retrieve recent warning/error log lines for a service. "
            "Input: a service name or the query."
        ),
        func=run,
    )


def build_runbook_tool(retriever: Retriever, citations: list[Citation]) -> Tool:
    def run(query: str) -> str:
        hits = retriever.retrieve(query, top_k=settings.top_k)
        if not hits:
            return "No matching runbooks found."
        chunks: list[str] = []
        for doc, score in hits[:3]:
            source = doc.metadata.get("source", "runbook")
            citations.append(
                Citation(
                    index=len(citations) + 1,
                    source=source,
                    score=round(float(score), 4),
                    snippet=doc.text.strip()[:280],
                )
            )
            chunks.append(f"[{source}] {doc.text.strip()[:500]}")
        return "\n\n".join(chunks)

    return Tool(
        name="search_runbooks",
        description=(
            "Semantic search (RAG) over the SRE runbook knowledge base. "
            "Input: a description of the symptom or error."
        ),
        func=run,
    )


def build_remediation_tool(retriever: Retriever, citations: list[Citation]) -> Tool:
    def run(query: str) -> str:
        hits = retriever.retrieve(query, top_k=settings.top_k)
        if not hits:
            return "No remediation guidance found."
        commands: list[str] = []
        sources: set[str] = set()
        for doc, _ in hits:
            source = doc.metadata.get("source", "runbook")
            for line in doc.text.splitlines():
                if _CMD_RE.search(line):
                    cmd = line.strip(" `-").strip()
                    if cmd and cmd not in commands:
                        commands.append(cmd)
                        sources.add(source)
        if not commands:
            return "No concrete commands found; review the matched runbooks manually."
        for source in sorted(sources):
            citations.append(
                Citation(index=len(citations) + 1, source=source, score=0.0, snippet="remediation")
            )
        plan = "\n".join(f"  $ {c}" for c in commands[:6])
        return (
            "Proposed remediation plan (DRY-RUN — requires human approval before "
            f"execution). Sources: {', '.join(sorted(sources))}\n{plan}"
        )

    return Tool(
        name="propose_remediation",
        description=(
            "Propose a concrete, dry-run remediation plan (commands) grounded in the "
            "runbooks. Never executes anything. Input: the diagnosis or symptom."
        ),
        func=run,
    )


def build_default_tools(
    telemetry: TelemetryStore, retriever: Retriever, citations: list[Citation]
) -> list[Tool]:
    return [
        build_metrics_tool(telemetry),
        build_logs_tool(telemetry),
        build_runbook_tool(retriever, citations),
        build_remediation_tool(retriever, citations),
    ]
