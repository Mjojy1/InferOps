"""Microphone capture for push-to-talk.

Half-duplex on purpose: we listen, then think, then speak, then listen again.
(True full-duplex barge-in — talking over the agent — is what ElevenAgents'
managed turn-taking model gives you server-side; see voice/README.md.)
"""
from __future__ import annotations

import io

import numpy as np
import sounddevice as sd
import soundfile as sf

from . import config


def record_turn() -> io.BytesIO:
    """Record from the default mic until the user presses Enter.

    Returns an in-memory 16-bit PCM WAV buffer ready to hand to Scribe.
    """
    frames: list[np.ndarray] = []

    def _callback(indata, _frames, _time, status):
        if status:
            # Overflows are non-fatal for a demo; just note them.
            print(f"  (audio status: {status})")
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=config.MIC_SAMPLE_RATE,
        channels=1,
        dtype="int16",
        callback=_callback,
    )
    with stream:
        input("  🎙️  listening — press Enter when you're done… ")

    if frames:
        audio = np.concatenate(frames, axis=0)
    else:
        audio = np.zeros((0, 1), dtype="int16")

    buf = io.BytesIO()
    sf.write(buf, audio, config.MIC_SAMPLE_RATE, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf
