# 🎙️ InferOps Voice Layer

A hands-free voice front end over the [InferOps](../README.md) SRE copilot. Ask
about an incident out loud and hear the grounded diagnosis read back — useful
when you're on-call, away from the keyboard, or just want a faster loop than
typing curl.

## Pipeline

```
🎤 mic  →  ElevenLabs Scribe v2 (STT)  →  InferOps POST /api/v1/chat (LLM + RAG agent)
        →  ElevenLabs Flash v2.5 (TTS)  →  🔊 speaker  →  (back to listening)
```

The voice layer stays fully decoupled from InferOps internals: it talks to the
same `POST /api/v1/chat` endpoint the web UI and the curl examples use.

## Setup

1. **Install the Python deps:**

   ```bash
   pip install -r voice/requirements.txt
   ```

2. **Install the system audio libraries** (needed by `sounddevice` /
   `soundfile`):

   - **macOS:** `brew install portaudio libsndfile`
   - **Debian/Ubuntu:** `sudo apt install libportaudio2 libsndfile1`

3. **Add your ElevenLabs API key:**

   ```bash
   cp voice/.env.example .env
   # then edit .env and set ELEVENLABS_API_KEY=sk_...
   ```

   The real `.env` is git-ignored — only `voice/.env.example` is committed.

4. **Start InferOps** in one terminal:

   ```bash
   uvicorn app.main:app --port 8000
   ```

5. **Run the voice loop** from the repo root in another terminal:

   ```bash
   python -m voice.voice_loop
   ```

   Press Enter to start talking, Enter again when you're done. The agent's
   answer is printed and spoken. Ctrl-C to quit.

## Configuration

Everything is driven by environment variables (see `voice/.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `ELEVENLABS_API_KEY` | *(required)* | Your ElevenLabs key |
| `ELEVENLABS_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` (Rachel) | Any voice from your library |
| `ELEVENLABS_TTS_MODEL` | `eleven_flash_v2_5` | Low-latency TTS model |
| `ELEVENLABS_STT_MODEL` | `scribe_v2` | Speech-to-text model |
| `INFEROPS_URL` | `http://localhost:8000` | Where InferOps is running |
| `INFEROPS_MODE` | `agent` | `agent` (autonomous) or `rag` (Q&A) |
| `INFEROPS_SERVICE` | *(unset)* | Optional service hint, e.g. `checkout-api` |
| `MIC_SAMPLE_RATE` | `16000` | Mic capture rate (Scribe handles 16 kHz) |

## Limitations

- **Half-duplex, push-to-talk.** The loop listens, then thinks, then speaks,
  then listens again. You **cannot barge in** (talk over the agent while it's
  responding). Full-duplex, server-side managed turn-taking is what
  [ElevenAgents](https://elevenlabs.io/agents) provides — this layer keeps
  things simple and local instead.
- **One mic, one speaker, one machine.** No telephony, no WebRTC, no streaming
  partial transcripts.

## Verified against

- `elevenlabs` Python SDK **2.58.0**
- STT model `scribe_v2`, TTS model `eleven_flash_v2_5`
- TTS output format `pcm_24000` (raw 16-bit mono PCM @ 24 kHz — no ffmpeg needed)

If you bump the SDK and something breaks, re-check the three call sites in
`voice/elevenlabs_io.py` first.
