# 周五 / Friday 🦜

A local, private, free desktop English companion. Friday lives in a corner of
your screen and helps you with three things:

- **Translate** — Chinese ⇄ English, idiomatic (not word-for-word)
- **Writing** — fix grammar / naturalness and explain why (in Chinese)
- **Speaking** — record a sentence, get a more natural way to say it

Everything runs **on your Mac** through [oMLX](https://github.com/jundot/omlx)
— no API costs, no data leaving your machine.

> Pronunciation/accent scoring is acoustic and out of scope. Friday coaches
> phrasing and word choice from the *text* of what you said.

## Architecture

```
┌─ Friday (this repo) ──────────┐        ┌─ oMLX server (you run it) ────┐
│  PySide6 floating window      │  HTTP  │  127.0.0.1:8000               │
│  ① select text → translate    │ ─────> │  /v1/chat/completions  (LLM)  │
│  ② type        → writing tips │        │  /v1/audio/transcriptions     │
│  ③ 🎤 record   → speaking tips │ <───── │     (Whisper STT)             │
└───────────────────────────────┘        └───────────────────────────────┘
```

Friday is a **thin client** — all inference happens in oMLX. The app depends
only on `httpx`, `PySide6`, `sounddevice`. No MLX dependency.

## Prerequisites

1. **[oMLX](https://github.com/jundot/omlx)** installed and the server running,
   with an API key set.
2. Models pulled into oMLX's model directory (`~/.omlx/models`):
   - Brain: `mlx-community/Qwen3-4B-4bit` (chosen via the bake-off below)
   - Speech: `mlx-community/whisper-large-v3-turbo`
     (also copy `preprocessor_config.json`, `tokenizer.json`,
     `special_tokens_map.json` from `openai/whisper-large-v3-turbo` if the MLX
     repo omits them).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The API key is read automatically from your local oMLX settings
(`~/.omlx/settings.json`). To point at oMLX running elsewhere, set env vars:

```bash
export FRIDAY_BASE_URL=http://127.0.0.1:8000/v1
export FRIDAY_API_KEY=...        # optional; defaults to local oMLX key
export FRIDAY_MODEL=Qwen3-4B-4bit
```

## Usage (library, today)

```python
from pet import brain
brain.translate("他这个人刀子嘴豆腐心。")
brain.writing_suggest("I am writing to you for asking about the status.")
brain.speak_feedback("I very like coffee but today I no drink.")
```

The floating-window UI is Phase 2 (see Roadmap).

## Model bake-off

`bench/run.py` compares candidate brains on a fixed test set
(`bench/testset.json`) and writes `bench/results.md`. On a 16GB Mac:

| model | speed | peak mem | verdict |
|---|---|---|---|
| MiniCPM5-1B | 77 tok/s | 0.8 GB | ❌ doesn't translate (too small) |
| **Qwen3-4B-4bit** | 26 tok/s | 2.6 GB | ✅ chosen — fast, light, good |
| Qwen3-8B-4bit | 13 tok/s | 4.9 GB | best on hard idioms; optional HQ mode |

```bash
./bench/run.sh   # runs through oMLX's bundled Python
```

## Project layout

```
pet/        # the app
  config.py    # endpoint / model / key resolution
  prompts.py   # the three skill prompts (shared with bench)
  brain.py     # HTTP client over oMLX chat API
  audio.py     # mic record + Whisper transcribe
  app.py       # floating-window UI (Phase 2)
bench/      # dev-only model comparison
docs/       # status & notes
```

## Roadmap

- [x] Phase 0 — model bake-off, brain selected (Qwen3-4B-4bit)
- [x] Phase 1 — translate / writing / speaking backend, validated over HTTP
- [ ] Phase 2 — corner floating-window UI, global hotkey, mic button
- [ ] Phase 3 — pet character (expressions), autostart, history, optional TTS

## License

MIT — see [LICENSE](LICENSE).
