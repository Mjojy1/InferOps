"""Deterministic offline inference engine.

This engine keeps InferOps fully runnable without a GPU or a running Ollama
server (CI, laptops, quick demos). It is intentionally simple: it produces
lexical embeddings and rule-based responses. When a real model is available the
router prefers Ollama and this engine is never used.

It plays two roles:
  * Embeddings: deterministic hashed bag-of-words vectors (cosine-comparable).
  * Chat: an extractive RAG answerer, and — in agent mode — a small planner
    that emits the same JSON tool-call protocol a real model would.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Sequence

import numpy as np

from app.inference.base import GenerationResult, Message, ToolSpec

_TOKEN_RE = re.compile(r"[a-z0-9]+")
EMBED_DIM = 512

# Preferred order in which the planner gathers evidence before concluding.
_TOOL_ORDER = ["query_metrics", "search_logs", "search_runbooks", "propose_remediation"]


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _stable_hash(token: str) -> int:
    return int.from_bytes(hashlib.md5(token.encode("utf-8")).digest()[:4], "little")


class FallbackEngine:
    """A dependency-free, deterministic stand-in for a hosted LLM."""

    name = "fallback"

    def available(self) -> bool:
        return True

    # ----- embeddings -------------------------------------------------------
    def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = np.zeros(EMBED_DIM, dtype=np.float32)
            for tok in _tokens(text):
                vec[_stable_hash(tok) % EMBED_DIM] += 1.0
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec /= norm
            vectors.append(vec.tolist())
        return vectors

    # ----- chat -------------------------------------------------------------
    def chat(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
        tools: Sequence[ToolSpec] | None = None,
    ) -> GenerationResult:
        start = time.perf_counter()
        if json_mode and tools:
            text = self._plan(messages, list(tools))
        else:
            text = self._answer(messages)
        latency_ms = (time.perf_counter() - start) * 1000.0

        completion_tokens = max(1, len(_tokens(text)))
        prompt_tokens = sum(len(_tokens(m.content)) for m in messages)
        return GenerationResult(
            text=text,
            model=model or "heuristic-fallback",
            backend=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency_ms, 2),
        )

    # ----- agent planner ----------------------------------------------------
    def _plan(self, messages: Sequence[Message], tools: list[ToolSpec]) -> str:
        names = {t.name for t in tools}
        order = [n for n in _TOOL_ORDER if n in names]
        actions_taken = sum(1 for m in messages if m.role == "assistant")
        query = self._first_user(messages)
        service = self._extract_service(messages)

        if actions_taken < len(order):
            action = order[actions_taken]
            if action == "search_runbooks":
                action_input = self._evidence_query(messages, query)
            elif action == "propose_remediation":
                diagnosis = self._diagnosis(self._observation_map(messages))
                action_input = self._evidence_query(messages, diagnosis)
            else:  # query_metrics, search_logs
                action_input = service or query
            return json.dumps(
                {
                    "thought": f"I should call {action} to gather evidence before concluding.",
                    "action": action,
                    "action_input": action_input,
                }
            )

        return json.dumps(
            {
                "thought": "I have gathered metrics, logs and runbook guidance; summarizing.",
                "action": "final_answer",
                "answer": self._synthesize(messages, query, service),
            }
        )

    def _synthesize(self, messages: Sequence[Message], query: str, service: str) -> str:
        obs = self._observation_map(messages)
        diagnosis = self._diagnosis(obs)
        target = service or "the affected service"

        parts = [f"Root cause (likely): {diagnosis} on {target}."]
        key_metrics = self._key_metrics(obs.get("query_metrics", ""))
        if key_metrics:
            parts.append("Key metrics — " + key_metrics)
        error_line = self._first_error(obs.get("search_logs", ""))
        if error_line:
            parts.append("Primary log signal — " + error_line)

        remediation_src = obs.get("propose_remediation") or obs.get("search_runbooks", "")
        if remediation_src:
            commands = self._commands(remediation_src)
            parts.append(
                "Recommended remediation (DRY-RUN — review before applying):\n" + commands
            )

        sources = self._sources(obs.get("search_runbooks", "") + obs.get("propose_remediation", ""))
        parts.append("Sources: " + (sources or "internal runbooks"))
        return "\n\n".join(parts)

    def _evidence_query(self, messages: Sequence[Message], base: str) -> str:
        """Build a symptom-rich search query from the evidence gathered so far."""
        obs = self._observation_map(messages)
        terms: list[str] = []
        for line in obs.get("search_logs", "").splitlines():
            if "ERROR" in line or "WARN" in line:
                terms.append(re.sub(r".*?(ERROR|WARN)\s*", "", line))
        saturation = re.search(r"saturation:\s*(\S+)", obs.get("query_metrics", ""))
        if saturation:
            terms.append(saturation.group(1))
        return (base + " " + " ".join(terms)).strip()[:300]

    # ----- pure RAG answer --------------------------------------------------
    def _answer(self, messages: Sequence[Message]) -> str:
        question = self._first_user(messages)
        context = self._extract_context(messages)
        if not context:
            return (
                "I don't have enough information in the indexed runbooks to answer that "
                "confidently."
            )
        sentences = self._rank_sentences(context, question)
        if not sentences:
            return (
                "I don't have enough information in the indexed runbooks to answer that "
                "confidently."
            )
        return " ".join(sentences[:3])

    # ----- helpers ----------------------------------------------------------
    @staticmethod
    def _first_user(messages: Sequence[Message]) -> str:
        for m in messages:
            if m.role == "user":
                # The task line may be "Incident query: ...". Strip the label.
                line = m.content.splitlines()[0]
                return re.sub(r"^(incident query|query):\s*", "", line, flags=re.I).strip()
        return ""

    @staticmethod
    def _extract_service(messages: Sequence[Message]) -> str:
        text = "\n".join(m.content for m in messages if m.role == "user")
        labelled = re.search(r"affected service:\s*([a-z0-9][a-z0-9-]+)", text, re.I)
        if labelled:
            return labelled.group(1).lower()
        generic = re.search(
            r"\b([a-z][a-z0-9]*-(?:api|svc|service|worker|gateway|db))\b", text, re.I
        )
        return generic.group(1).lower() if generic else ""

    def _observation_map(self, messages: Sequence[Message]) -> dict[str, str]:
        """Pair each assistant tool action with the observation that followed."""
        result: dict[str, str] = {}
        last_action: str | None = None
        for m in messages:
            if m.role == "assistant":
                try:
                    last_action = json.loads(m.content).get("action")
                except Exception:
                    last_action = None
            elif m.role in ("user", "tool") and m.content.startswith("Observation:"):
                if last_action:
                    result[last_action] = m.content[len("Observation:"):].strip()
                    last_action = None
        return result

    @staticmethod
    def _diagnosis(obs: dict[str, str]) -> str:
        blob = " ".join(obs.values()).lower()
        if "oomkill" in blob or "memory limit" in blob or "crashloop" in blob:
            return "memory exhaustion / OOMKill driving CrashLoopBackOff"
        if "throttl" in blob or "cpu" in blob and "9" in blob:
            return "CPU saturation and throttling"
        if "disk" in blob or "no space left" in blob:
            return "disk pressure on the volume/node"
        if "timeout" in blob or "latency" in blob or "pool exhausted" in blob:
            return "latency from a slow/saturated downstream dependency"
        return "elevated error rate"

    @staticmethod
    def _key_metrics(text: str) -> str:
        wanted = {
            "cpu_pct": "cpu",
            "memory_pct": "memory",
            "disk_pct": "disk",
            "p99_latency_ms": "p99",
            "error_rate_pct": "errors",
            "restart_count_1h": "restarts/1h",
        }
        found: list[str] = []
        for line in text.splitlines():
            match = re.match(r"\s*-\s*([a-z0-9_]+):\s*(.+)", line)
            if match and match.group(1) in wanted:
                found.append(f"{wanted[match.group(1)]} {match.group(2).strip()}")
        return ", ".join(found)

    @staticmethod
    def _first_error(text: str) -> str:
        for line in text.splitlines():
            if "ERROR" in line:
                return line.strip()[:200]
        return ""

    @staticmethod
    def _commands(text: str) -> str:
        pattern = re.compile(r"(kubectl|systemctl|helm|docker|journalctl|df\s|du\s|find\s)")
        cmds = [ln.strip(" `$") for ln in text.splitlines() if pattern.search(ln)]
        if cmds:
            return "\n".join(f"  $ {c}" for c in cmds[:5])
        return "  " + text.strip()[:300]

    @staticmethod
    def _sources(text: str) -> str:
        found = sorted(set(re.findall(r"([\w.\-]+\.md)", text)))
        return ", ".join(found)

    @staticmethod
    def _extract_context(messages: Sequence[Message]) -> str:
        for m in messages:
            if "CONTEXT:" in m.content:
                body = m.content.split("CONTEXT:", 1)[1]
                return body.split("QUESTION:", 1)[0].strip()
        return ""

    @staticmethod
    def _rank_sentences(context: str, question: str) -> list[str]:
        q_terms = set(_tokens(question))
        sentences = re.split(r"(?<=[.!?])\s+|\n+", context)
        scored: list[tuple[int, str]] = []
        for sent in sentences:
            clean = sent.strip(" []")
            if len(clean) < 12:
                continue
            overlap = len(q_terms & set(_tokens(clean)))
            if overlap:
                scored.append((overlap, clean))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]
