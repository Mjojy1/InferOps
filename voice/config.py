"""Configuration for the InferOps voice layer.

All values come from environment variables so nothing secret is hard-coded.
Copy voice/.env.example to .env (or export these in your shell) before running.
"""
from __future__ import annotations

import os


def _get(name: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"See voice/.env.example."
        )
    return val


# --- ElevenLabs -------------------------------------------------------------
ELEVENLABS_API_KEY = _get("ELEVENLABS_API_KEY", required=True)

# A voice from your ElevenLabs Voice Library. "Rachel" is a common default;
# grab any voice_id from https://elevenlabs.io/app/voice-library.
VOICE_ID = _get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel

# Low-latency model — the one ElevenLabs recommends for real-time agents.
TTS_MODEL_ID = _get("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5")

# Current speech-to-text model (scribe_v1 is deprecated).
STT_MODEL_ID = _get("ELEVENLABS_STT_MODEL", "scribe_v2")

# --- InferOps ---------------------------------------------------------------
# Where your running InferOps FastAPI app lives.
INFEROPS_URL = _get("INFEROPS_URL", "http://localhost:8000")

# Default triage mode: "agent" (autonomous) or "rag" (single-shot Q&A).
DEFAULT_MODE = _get("INFEROPS_MODE", "agent")

# Optional service hint passed to the agent (e.g. "checkout-api").
DEFAULT_SERVICE = _get("INFEROPS_SERVICE", None)

# --- Audio ------------------------------------------------------------------
# Scribe handles 16 kHz mic input fine; Flash returns 24 kHz PCM.
MIC_SAMPLE_RATE = int(_get("MIC_SAMPLE_RATE", "16000"))
TTS_SAMPLE_RATE = 24000  # fixed by the pcm_24000 output_format below
