"""Runtime config for Friday.

Resolution order for each value: explicit env var → sensible default.
The API key is NEVER hardcoded or committed. By default it is read from the
local oMLX settings file (the user's own machine); override with an env var
if you run oMLX elsewhere.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# oMLX OpenAI-compatible endpoint
BASE_URL = os.environ.get("FRIDAY_BASE_URL", "http://127.0.0.1:8000/v1")

# The brain. Chosen via bake-off (see bench/). Override with FRIDAY_MODEL.
MODEL = os.environ.get("FRIDAY_MODEL", "Qwen3-4B-4bit")

# Optional stronger model for a future "high-quality mode". Empty by default:
# Qwen3-8B was removed to keep a 16GB Mac comfortable (only one small model
# should be loaded at a time). Set this + install a model to enable an HQ mode.
HQ_MODEL = os.environ.get("FRIDAY_HQ_MODEL", "")

# Whisper model id for speech-to-text (set once the STT model is installed).
STT_MODEL = os.environ.get("FRIDAY_STT_MODEL", "whisper-large-v3-turbo")

_OMLX_SETTINGS = Path.home() / ".omlx" / "settings.json"


def get_api_key() -> str:
    """Return the oMLX API key (env first, then local oMLX settings)."""
    for var in ("FRIDAY_API_KEY", "OMLX_API_KEY"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        data = json.loads(_OMLX_SETTINGS.read_text())
        key = data.get("auth", {}).get("api_key")
        if key:
            return key
    except (OSError, json.JSONDecodeError):
        pass
    raise RuntimeError(
        "No API key found. Set FRIDAY_API_KEY, or configure one in the oMLX app."
    )
