# Friday — current status

_Last updated: 2026-05-27_

## What's done

- **Phase 0 — model bake-off (complete).** Compared MiniCPM5-1B / Qwen3-4B-4bit /
  Qwen3-8B-4bit on a fixed 9-prompt test set (`bench/`). 1B is unusable (doesn't
  even translate). **Chosen brain: `Qwen3-4B-4bit`** — fast (26 tok/s), light
  (2.6 GB peak), quality clearly "usable". 8B kept as an optional high-quality
  mode for the hardest idioms.
- **Phase 1 — text + audio backend (complete, validated over HTTP).**
  - `pet/prompts.py` — three skill prompts. Translate direction is decided in
    code (CJK detection) because letting the model auto-detect caused it to
    paraphrase in the source language. Idioms told to render by meaning.
  - `pet/brain.py` — thin httpx client over oMLX `/v1/chat/completions`.
    Thinking disabled via `chat_template_kwargs={"enable_thinking": false}`
    (a top-level `enable_thinking` is ignored by oMLX — important gotcha).
  - `pet/audio.py` — mic capture (sounddevice) + `/v1/audio/transcriptions`.
  - Validated: translate, writing, speaking all return clean output; full
    speech→transcribe→feedback chain works (tested with macOS `say` audio).
- **oMLX setup.** Models live in `~/.omlx/models`. Whisper needed HF
  processor/tokenizer files copied from `openai/whisper-large-v3-turbo` on top
  of the MLX weights (oMLX errors clearly if missing).
- Open-source scaffolding: README, LICENSE (MIT), .gitignore, requirements.

## Gotchas / environment notes

- New models aren't served until oMLX re-discovers them. Trigger without the
  browser: `POST /admin/api/login` (with the API key) to get a session cookie,
  then `POST /admin/api/reload`.
- `enable_thinking` must go inside `chat_template_kwargs`, not top-level.
- Background `huggingface_hub` downloads here get cut off after metadata —
  download model weights in the foreground.

- **Phase 2 — UI (complete, headless-validated).** `pet/app.py`: frameless,
  always-on-top corner card (PySide6). Draggable header, 翻译/写作/口语 tabs,
  async inference off the UI thread (threading + queued Qt signals), 🎤 toggle
  record → Whisper → speaking feedback, global hotkey ⌘⇧T → translate clipboard.
  Deps in a `.venv` (PySide6, sounddevice, pynput, httpx, numpy). Launch with
  `./start.sh` or `python3 -m pet.app`. Smoke-tested in QT_QPA_PLATFORM=offscreen:
  window builds, modes switch, and a real translate flows UI→thread→oMLX→signal→pane.

## What remains

- **Live run on the user's display** (can't be done headlessly): verify look,
  grant macOS mic + Accessibility/Input-Monitoring permissions, confirm the
  hotkey fires and recording works with a real mic.
- **Phase 3 — pet polish:** character expressions (idle/thinking/talking),
  autostart, history, optional TTS, package as a proper .app (Dock icon,
  permissions prompts behave better than running from Terminal).
- "Show uncertainty" interaction polish (offer two options / flag low confidence).

## Update (2026-05-26, later): web-shell pivot + cat character

- **Character is now an orange/ginger Devon Rex cat** (橘黄色德文猫), not a parrot.
- **Shell pivoted Qt → web** (pywebview) so claude-design HTML/CSS/JS + cat
  animations drop straight in. New files:
  - `pet/bridge.py` — `Api` exposed to JS as `window.pywebview.api`: translate /
    writing_suggest / speak_feedback, start/stop_recording (with **live partial
    transcription** pushed via `window.fridayPartial`), `set_clip_watch`, global
    hotkey ⌘⇧T + clipboard-watch (both push via `window.fridayClipboard`).
  - `pet/shell.py` — transparent/frameless/on-top window, corner-positioned,
    loads `web/index.html`. Run: `python3 -m pet.shell`.
  - `web/index.html` — minimal functional skeleton (cat 🐱 placeholder) that
    claude-design visuals will replace; keep the element ids + JS hooks.
  - `pet/app.py` (Qt) is now legacy.
- Bridge + transcription validated headlessly; the window itself needs a live
  desktop session (mic + accessibility/clipboard permissions on first run).

## Update (2026-05-26, cat asset)

- Adopted the Codex pixel-art cat from `~/.codex/pets/devon/spritesheet.webp`
  (chibi peach/orange-and-white Devon Rex). Sheet had **no frame atlas** and an
  RGBA-transparent bg (the magenta is colored data under alpha=0). Auto-segmented
  57 frames by content bands; picked 5 → `web/assets/cat/{idle,listening,thinking,
  talking,sleeping}.png` (frames #22/#29/#48/#24/#36).
- Wired into the shell: `#cat` is now an `<img>` (pixel-crisp, idle bob); `setPose()`
  swaps frames on state (thinking on send, listening while recording, talking on
  result). Also added a **copy button** on the result (via `Api.copy_output`, which
  suppresses the self-copy so 划词翻译 doesn't re-translate it).

## Update (2026-05-26, translation + memory hygiene)

- **Translation prompt improved** (`pet/prompts.py`): force natural target word
  order + faithfulness + direction-specific few-shot. Everyday quality now ≈ Lark
  on common sentences; hard telegraphic/idiom cases remain 4B's ceiling.
- **Seed-X experiment FAILED.** Tried `dong-99/Seed-X-PPO-7B-mlx-4Bit` (ByteDance
  translation model). Its good outputs beat Qwen on word order, but the 4bit
  conversion is broken — ~40% of inputs degenerate to repeated `<s>` (confirmed
  via mlx_lm directly, so it's the quant, not oMLX). 8bit (~7.5G) is too big for
  16GB. → **Stay on Qwen3-4B + improved prompt.**
- **Near-freeze incident**: oMLX `idle_timeout` was `null` (models never auto-
  unload), so it held Qwen3-4B + Seed-X at once; a diagnostic loaded a 3rd 7B →
  16GB blew past into swap. Fixed: set `idle_timeout_seconds=180`; deleted unused
  models. **16GB rule: keep ONE small model loaded; never load several.**
- **Lean model set now**: only `Qwen3-4B-4bit` (brain) + `whisper-large-v3-turbo`
  (STT) remain on disk (3.6G). Deleted Seed-X, Qwen3-8B, MiniCPM5-1B.
- **Action for user**: restart oMLX (quit & reopen) so idle_timeout takes effect,
  memory clears, and deleted models drop from the served list.

## Update (2026-05-26, claude-design UI integrated)

- Integrated the claude-design UI (from `~/Downloads/desk pet.zip` → `Friday.html`)
  into `web/index.html`. Kept all visuals/animations (cat pokes above the card,
  click-to-toggle, state ornaments: sound waves / think bubbles / sleep z's,
  speech-tail result, mic pulse). Stripped the demo scaffolding (fake desktop
  bg/dock/clock, state-demo strip) and made the body transparent for the real window.
- Replaced the mock logic with real bridge calls: send → `api.translate` /
  `api.writing_suggest`; mic → `api.start_recording` / `api.stop_recording`
  (+ `window.fridayPartial` live transcript); copy → `api.copy_output`; 划词 toggle
  → `api.set_clip_watch` (+ `window.fridayClipboard`). ⌘↩ sends.
- Result rendering simplified to faithfully show the brain's text (the design's
  fixed fix/note/better 3-section split was tied to mock data).
- `pet/shell.py` window resized to 420×760 (card grows upward from the bottom-
  anchored cat). Cat frames synced from the design's copy.
- Validated headlessly: inline JS passes `node --check`; `pet.shell` imports;
  bridge skills already verified. The live window needs the user's display.

## Update (2026-05-26, first commit + UI tweaks)

- **Committed** the initial version (`master`, "Initial commit — Friday …").
- UI tweaks from live feedback: window 420×760 → **340×620**, card 360→296,
  cat 168→138 (lighter/smaller); **drag-vs-click fixed** — dragging the cat to
  move the window no longer toggles the card (>6px move = drag, ignored).
- Confirmed: 划词翻译 ON → copy auto-translates (no manual send; `fridayClipboard`
  calls `run`).

## What remains (next, per user)

- **Optimize translation quality** further (beyond the Qwen3-4B + improved prompt).
- **Auto-start on login** (package/login-item).
- Live-run verification of the compact window + drag fix on the user's desktop.
- Maybe: window click-through on transparent areas; history panel; TTS.
- Live run: grant mic + (for hotkey) Accessibility permission; verify the
  transparent window, drag, streaming transcription, 划词翻译 toggle.
- True zero-keypress select-to-translate via macOS Accessibility AXSelectedText
  (current 划词 = clipboard-watch: select + ⌘C → auto-translate).
- Phase 3 polish: cat expressions/animation, autostart, history, optional TTS,
  package as a real .app.

## Update (2026-05-27, brain → Qwen3.5-4B)

- **Translation shoot-out concluded.** After the Seed-X failure, evaluated
  cloud Qwen-MT (rejected: not local) and a community ranking article. Final
  short-list was **translategemma-4b** vs **Qwen3.5-4B**; the user chose
  **Qwen3.5-4B** as the single brain for all three skills.
  - translategemma is translate-only and, run raw via mlx_lm, spammed
    `<end_of_turn>` ~150× after the (excellent) translation — extra integration
    cost for one skill, so rejected.
- **`pet/config.py`**: `MODEL` default is now `Qwen3.5-4B-4bit` (was
  `Qwen3-4B-4bit`). Override still via `FRIDAY_MODEL`.
- **Verified over HTTP on Qwen3.5-4B** (thinking off via `chat_template_kwargs`):
  translate (ZH↔EN + idiom "half-baked" → "还不太成熟"), writing, speaking all
  return clean output, **no `<think>` leak**.
- oMLX re-discovery done (login → `/admin/api/reload`); served list now =
  Qwen3-4B-4bit, Qwen3.5-4B-4bit, translategemma-4b-it-4bit, whisper.
- **Disk:** Qwen3.5-4B-4bit (2.9G) + whisper (1.5G) are the keepers. The losing
  models on disk — Qwen3-4B-4bit (2.1G, old brain) and translategemma-4b-it-4bit
  (2.1G, rejected) — are cleanup candidates (disk only; RAM rule is about loaded
  models, so this isn't stability-critical).
