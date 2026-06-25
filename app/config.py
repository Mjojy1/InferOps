"""Application settings, loaded from environment variables / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. Field names map to UPPER_CASE env vars."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "InferOps"
    environment: str = "local"

    # Local inference (Ollama). When Ollama is unreachable or disabled, the
    # router transparently falls back to a deterministic offline engine so the
    # app stays runnable on any machine (CI, laptops without a GPU, demos).
    enable_ollama: bool = True
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1"
    embedding_model: str = "nomic-embed-text"
    request_timeout: float = 60.0

    # RAG
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4

    # Agent
    max_agent_steps: int = 6

    # Data
    data_dir: str = "data"


settings = Settings()
