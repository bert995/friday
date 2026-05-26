"""Friday's brain: thin client over the oMLX OpenAI-compatible API.

The shipped app depends only on httpx — all inference happens in the local
oMLX server. Thinking is disabled (enable_thinking=False): for a translator /
writing tool we want fast, clean output, not chain-of-thought.
"""

from __future__ import annotations

import re

import httpx

from . import config, prompts

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_TIMEOUT = httpx.Timeout(60.0, connect=5.0)


def _chat(messages: list[dict], *, max_tokens: int = 320, temperature: float = 0.3,
          model: str | None = None) -> str:
    payload = {
        "model": model or config.MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        # Disable Qwen3 chain-of-thought — passed via chat_template_kwargs, the
        # only place oMLX reads it (a top-level enable_thinking is ignored).
        "chat_template_kwargs": {"enable_thinking": False},
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {config.get_api_key()}"}
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(f"{config.BASE_URL}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
    return _THINK_RE.sub("", content).strip()


def translate(text: str, *, model: str | None = None) -> str:
    """Chinese <-> English. Target language is decided in prompts.build_translate."""
    return _chat(prompts.build_translate(text), max_tokens=256, temperature=0.2, model=model)


def writing_suggest(text: str, *, model: str | None = None) -> str:
    """Grammar / naturalness feedback on written English."""
    return _chat(prompts.build_writing(text), max_tokens=400, temperature=0.4, model=model)


def speak_feedback(transcript: str, *, model: str | None = None) -> str:
    """Idiomatic feedback on a transcribed spoken sentence (text-level only)."""
    return _chat(prompts.build_speaking(transcript), max_tokens=400, temperature=0.4, model=model)
