# 周五 / Friday 🐱

A local, private, free desktop English companion. Friday is a little cat that
lives in the corner of your screen and helps you with three things:

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
│  pywebview corner window      │  HTTP  │  127.0.0.1:8000               │
│  ① select + ⌘C → translate    │ ─────> │  /v1/chat/completions  (LLM)  │
│  ② type        → writing tips │        │  /v1/audio/transcriptions     │
│  ③ 🎤 record   → speaking tips │ <───── │     (Whisper STT)             │
└───────────────────────────────┘        └───────────────────────────────┘
```

Friday is a **thin client** — a "remote control". All the heavy lifting (the
language model) happens inside oMLX. Friday itself only depends on `httpx`,
`pywebview`, `sounddevice`, `pynput`, `numpy`. **No MLX / model is bundled in
the app**, which is why you must install oMLX and pull a model first.

## Prerequisites

1. **[oMLX](https://github.com/jundot/omlx)** installed, and its server running
   with an API key set (Friday reads the key from `~/.omlx/settings.json`).
2. Two models pulled into oMLX (`~/.omlx/models`):
   - **Brain:** `mlx-community/Qwen3.5-4B-4bit` — does all three skills.
   - **Speech:** `mlx-community/whisper-large-v3-turbo`
     (if the MLX repo omits them, also copy `preprocessor_config.json`,
     `tokenizer.json`, `special_tokens_map.json` from
     `openai/whisper-large-v3-turbo`).

> 16 GB Mac tip: keep **one** model loaded at a time. Set oMLX's
> `idle_timeout_seconds` (e.g. 180) so an idle model auto-unloads before the
> next one loads.

## Build the macOS app

```bash
./build.sh            # creates .venv, installs deps + PyInstaller, packages
open dist/Friday.app  # launch it
```

Then drag `dist/Friday.app` into `/Applications`. Double-click to open — Friday
appears in the bottom-right corner of your screen.

Notes:

- The build is **ad-hoc signed** so it runs locally without an Apple Developer
  account. If you instead *download* a build from someone else, macOS Gatekeeper
  may block it ("can't be opened…") — right-click → **Open** once to allow it.
  (Friction-free distribution would need real signing + notarization.)
- **Permissions on first run:** macOS will ask for the **microphone** (for
  speaking feedback). For the global hotkey (⌘⇧T to translate the clipboard),
  grant Friday **Accessibility** in System Settings → Privacy & Security.

## Run from source (development)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m pet.shell      # or: ./start.sh
```

Override the endpoint / model / key with env vars if oMLX runs elsewhere:

```bash
export FRIDAY_BASE_URL=http://127.0.0.1:8000/v1
export FRIDAY_API_KEY=...          # optional; defaults to local oMLX key
export FRIDAY_MODEL=Qwen3.5-4B-4bit
```

You can also use the backend as a library:

```python
from pet import brain
brain.translate("他这个人刀子嘴豆腐心。")
brain.writing_suggest("I am writing to you for asking about the status.")
brain.speak_feedback("I very like coffee but today I no drink.")
```

## Choosing the brain

`bench/run.py` compares candidate models on a fixed test set
(`bench/testset.json`). The short version of how `Qwen3.5-4B-4bit` was picked:

| model | notes |
|---|---|
| MiniCPM5-1B | ❌ too small — doesn't really translate |
| Qwen3-4B-4bit | ✅ first pick — fast & light; superseded |
| Qwen3-8B-4bit | better on hard idioms, but heavy for 16 GB |
| Seed-X-PPO-7B (4bit) | ❌ broken quant — ~40% degenerate output |
| translategemma-4b | great translations, but translate-only + raw output spam |
| **Qwen3.5-4B-4bit** | ✅ **chosen** — one model, all three skills, clean output |

```bash
./bench/run.sh   # runs through oMLX's bundled Python
```

## Project layout

```
app_main.py   # entry point for the packaged app
Friday.spec   # PyInstaller recipe (→ dist/Friday.app)
build.sh      # one-command build
pet/
  config.py     # endpoint / model / key resolution
  prompts.py    # the three skill prompts (shared with bench)
  brain.py      # HTTP client over oMLX chat API
  audio.py      # mic record + Whisper transcribe
  bridge.py     # JS↔Python bridge (window.pywebview.api)
  shell.py      # transparent, frameless, always-on-top window
  app.py        # legacy PySide6 UI (superseded by the web shell)
web/          # the UI — index.html + cat sprites
bench/        # dev-only model comparison
docs/         # status & notes
```

## Roadmap

- [x] Phase 0 — model bake-off, brain selected (`Qwen3.5-4B-4bit`)
- [x] Phase 1 — translate / writing / speaking backend, validated over HTTP
- [x] Phase 2 — corner window (pywebview), cat character, global hotkey, mic
- [x] Packaged as a double-clickable `Friday.app`
- [ ] Phase 3 — richer pet animation, auto-start on login, history, optional TTS

## License

MIT — see [LICENSE](LICENSE).
