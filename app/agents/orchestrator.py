"""The agent orchestrator — a ReAct-style plan/act/observe loop.

The model (Ollama in production, the deterministic engine offline) emits a JSON
action each turn. The orchestrator executes the named tool, feeds the
observation back, and repeats until the model returns ``final_answer`` or the
step budget is exhausted. Inference telemetry is aggregated across the run.
"""
from __future__ import annotations

import json
import re

from app.agents.base import AgentRun, AgentStep, Tool
from app.config import settings
from app.inference.base import GenerationResult, Message, ToolSpec
from app.inference.router import InferenceRouter

AGENT_SYSTEM_PROMPT = """You are InferOps, an autonomous Site Reliability Engineering (SRE) copilot.
You diagnose production incidents by reasoning step-by-step and calling tools.

Available tools:
{tools}

Respond with a SINGLE JSON object and nothing else.
To use a tool:
{{"thought": "<reasoning>", "action": "<tool_name>", "action_input": "<input>"}}
When you have enough evidence to conclude:
{{"thought": "<reasoning>", "action": "final_answer", "answer": "<root cause + concise, dry-run remediation steps, citing runbook sources>"}}

Guidelines:
- Gather evidence (metrics, logs, runbooks) before concluding.
- Remediation is DRY-RUN and must be reviewed by a human; never claim you executed anything.
- Be specific: reference the service and exact metric values."""


class AgentOrchestrator:
    def __init__(
        self,
        router: InferenceRouter,
        tools: list[Tool],
        max_steps: int | None = None,
    ) -> None:
        self.router = router
        self.tools = {t.name: t for t in tools}
        self.max_steps = max_steps or settings.max_agent_steps

    def run(self, query: str, service: str | None = None) -> AgentRun:
        tool_specs = [ToolSpec(t.name, t.description) for t in self.tools.values()]
        tool_desc = "\n".join(f"- {t.name}: {t.description}" for t in self.tools.values())

        task = f"Incident query: {query}"
        if service:
            task += f"\nAffected service: {service}"

        messages = [
            Message("system", AGENT_SYSTEM_PROMPT.format(tools=tool_desc)),
            Message("user", task),
        ]

        run = AgentRun(answer="")
        steps: list[AgentStep] = []

        for i in range(1, self.max_steps + 1):
            result = self.router.chat(
                messages, json_mode=True, tools=tool_specs, temperature=0.0
            )
            self._accumulate(run, result)
            action = self._parse(result.text)

            if action is None:
                run.answer = result.text.strip() or "Unable to produce a structured plan."
                run.steps = steps
                return run

            if action.get("action") == "final_answer":
                run.answer = str(action.get("answer", "")).strip() or "No answer produced."
                run.steps = steps
                return run

            name = action.get("action", "")
            action_input = str(action.get("action_input", ""))
            thought = str(action.get("thought", ""))

            tool = self.tools.get(name)
            if tool is None:
                observation = (
                    f"Error: unknown tool '{name}'. Available: {', '.join(self.tools)}"
                )
            else:
                try:
                    observation = tool.func(action_input)
                except Exception as exc:  # tool sandbox
                    observation = f"Tool error: {exc}"

            steps.append(AgentStep(i, thought, name, action_input, observation))
            messages.append(Message("assistant", result.text))
            messages.append(Message("user", f"Observation: {observation}"))

        # Step budget exhausted — request a final synthesis.
        messages.append(
            Message("user", "Provide your final answer now as JSON with action=final_answer.")
        )
        result = self.router.chat(messages, json_mode=True, tools=tool_specs, temperature=0.0)
        self._accumulate(run, result)
        action = self._parse(result.text) or {}
        run.answer = (
            str(action.get("answer", result.text)).strip() or "Reached the step limit."
        )
        run.steps = steps
        return run

    # ----- helpers ----------------------------------------------------------
    @staticmethod
    def _accumulate(run: AgentRun, result: GenerationResult) -> None:
        run.llm_calls += 1
        run.prompt_tokens += result.prompt_tokens
        run.completion_tokens += result.completion_tokens
        run.latency_ms += result.latency_ms
        run.backend = result.backend
        run.model = result.model

    @staticmethod
    def _parse(text: str) -> dict | None:
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    return None
            return None
