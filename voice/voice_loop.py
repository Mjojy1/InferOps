"""Talk to InferOps.

Full loop:  mic → Scribe v2 (STT) → InferOps /api/v1/chat (LLM + RAG agent)
            → Flash v2.5 (TTS) → speaker, then back to listening.

Run:
    # 1. start InferOps in another terminal
    uvicorn app.main:app --port 8000
    # 2. then, from the repo root:
    python -m voice.voice_loop
"""
from __future__ import annotations

import sys

from . import audio, config, elevenlabs_io, inferops_client


def _preflight() -> None:
    """Fail fast with a clear message if InferOps isn't reachable."""
    import httpx

    try:
        r = httpx.get(f"{config.INFEROPS_URL}/health", timeout=5.0)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - surface any connectivity issue
        print(
            f"✖ Can't reach InferOps at {config.INFEROPS_URL} ({exc}).\n"
            f"  Start it first:  uvicorn app.main:app --port 8000",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    _preflight()
    print("🛰️  InferOps voice copilot")
    print(f"    STT: {config.STT_MODEL_ID}  ·  TTS: {config.TTS_MODEL_ID}  "
          f"·  InferOps: {config.INFEROPS_URL}")
    print("    Ask about an incident out loud. Ctrl-C to quit.\n")

    while True:
        try:
            input("[Enter] to talk ")
            wav = audio.record_turn()

            question = elevenlabs_io.transcribe(wav)
            if not question:
                print("  (didn't catch that — try again)\n")
                continue
            print(f"  🧑 You: {question}")

            mode = inferops_client.pick_mode(question)
            answer, _raw = inferops_client.triage(question, mode=mode)
            print(f"  🛰️  InferOps [{mode}]: {answer}\n")

            elevenlabs_io.speak(answer)

        except KeyboardInterrupt:
            print("\n👋 bye")
            break
        except Exception as exc:  # noqa: BLE001 - keep the loop alive in a demo
            print(f"  ⚠️  error this turn: {exc}\n")


if __name__ == "__main__":
    main()
