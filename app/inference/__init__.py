"""Inference layer: local LLM (Ollama) with a deterministic offline fallback."""
from __future__ import annotations

from app.inference.base import GenerationResult, LLMBackend, Message, ToolSpec

__all__ = ["GenerationResult", "LLMBackend", "Message", "ToolSpec"]
