"""Agent primitives: tools and run records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Tool:
    """A callable the agent can invoke. ``func`` maps a string input to a string observation."""

    name: str
    description: str
    func: Callable[[str], str]


@dataclass
class AgentStep:
    step: int
    thought: str
    action: str
    action_input: str
    observation: str


@dataclass
class AgentRun:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    # Aggregated inference telemetry for the whole run.
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    backend: str = ""
    model: str = ""
