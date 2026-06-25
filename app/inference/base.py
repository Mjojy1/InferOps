"""Core inference data types and the backend protocol."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass
class Message:
    """A single chat message."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str


@dataclass
class ToolSpec:
    """A lightweight description of a tool exposed to the model."""

    name: str
    description: str


@dataclass
class GenerationResult:
    """The result of a single LLM generation, with inference telemetry."""

    text: str
    model: str
    backend: str  # "ollama" | "fallback"
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float

    @property
    def tokens_per_second(self) -> float:
        if self.latency_ms <= 0:
            return 0.0
        return round(self.completion_tokens / (self.latency_ms / 1000.0), 2)


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol implemented by every inference backend."""

    name: str

    def available(self) -> bool:
        ...

    def chat(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
        tools: Sequence[ToolSpec] | None = None,
    ) -> GenerationResult:
        ...

    def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
        ...
