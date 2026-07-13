"""Thin wrappers around the two ElevenLabs endpoints the voice loop needs:

    transcribe()  -> Scribe v2  (speech_to_text.convert)
    speak()       -> Flash v2.5 (text_to_speech.convert, PCM out)

Method names, model IDs and the PCM output_format below were checked against
elevenlabs-python 2.58.0. If you bump the SDK and something breaks, re-check
these three call sites first.
"""
from __future__ import annotations

import io

import numpy as np
import sounddevice as sd
from elevenlabs.client import ElevenLabs

from . import config

_client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)


def transcribe(wav_bytes: io.BytesIO) -> str:
    """Send a WAV buffer to Scribe v2 and return the recognised text."""
    wav_bytes.seek(0)
    resp = _client.speech_to_text.convert(
        model_id=config.STT_MODEL_ID,
        file=wav_bytes,
    )
    # SpeechToText response exposes `.text`.
    return (getattr(resp, "text", "") or "").strip()


def speak(text: str) -> None:
    """Synthesise `text` with Flash v2.5 and play it back.

    We request raw PCM (pcm_24000) instead of MP3 so playback needs no ffmpeg —
    the bytes go straight to the sound card as 16-bit mono @ 24 kHz.
    """
    if not text.strip():
        return
    audio_iter = _client.text_to_speech.convert(
        voice_id=config.VOICE_ID,
        text=text,
        model_id=config.TTS_MODEL_ID,
        output_format="pcm_24000",
    )
    pcm = b"".join(audio_iter)
    if not pcm:
        return
    samples = np.frombuffer(pcm, dtype=np.int16)
    sd.play(samples, config.TTS_SAMPLE_RATE)
    sd.wait()
