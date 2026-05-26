#!/usr/bin/env python3
"""Friday model bake-off.

Loads each candidate model directly via mlx_lm (no server needed), runs the
fixed test set from testset.json, and writes a side-by-side report plus a
perf table (speed + peak memory) so we can pick the brain on a 16GB Mac.

Run it through oMLX's bundled Python (which ships mlx_lm) — see run.sh.
"""

from __future__ import annotations

import gc
import json
import re
import sys
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pet.prompts import BUILDERS  # noqa: E402

HOME = Path.home()
MODELS = HOME / ".omlx" / "models"

# (display name, path) — ordered small -> large
CANDIDATES = [
    ("MiniCPM5-1B", MODELS / "openbmb" / "MiniCPM5-1B-MLX"),
    ("Qwen3-4B-4bit", MODELS / "mlx-community" / "Qwen3-4B-4bit"),
    ("Qwen3-8B-4bit", MODELS / "mlx-community" / "Qwen3-8B-4bit"),
]

MAX_TOKENS = 320
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _peak_gb() -> float:
    for fn in ("get_peak_memory",):
        if hasattr(mx, fn):
            return getattr(mx, fn)() / 1e9
    if hasattr(mx, "metal") and hasattr(mx.metal, "get_peak_memory"):
        return mx.metal.get_peak_memory() / 1e9
    return float("nan")


def _reset_peak() -> None:
    for fn in ("reset_peak_memory",):
        if hasattr(mx, fn):
            getattr(mx, fn)()
            return
    if hasattr(mx, "metal") and hasattr(mx.metal, "reset_peak_memory"):
        mx.metal.reset_peak_memory()


def _clear_cache() -> None:
    if hasattr(mx, "clear_cache"):
        mx.clear_cache()
    elif hasattr(mx, "metal") and hasattr(mx.metal, "clear_cache"):
        mx.metal.clear_cache()


def render_prompt(tokenizer, messages) -> str:
    """Apply chat template with thinking disabled (fall back if unsupported)."""
    try:
        return tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False, enable_thinking=False
        )
    except TypeError:
        return tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )


def run_one(model, tokenizer, messages) -> tuple[str, float, int]:
    prompt = render_prompt(tokenizer, messages)
    t0 = time.time()
    out = generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS, verbose=False)
    dt = time.time() - t0
    out = THINK_RE.sub("", out).strip()
    n_tok = len(tokenizer.encode(out))
    return out, dt, n_tok


def main() -> None:
    tests = json.loads((ROOT / "bench" / "testset.json").read_text())["tests"]
    results: dict[str, dict] = {}
    perf: dict[str, dict] = {}

    for name, path in CANDIDATES:
        if not (path / "config.json").exists():
            print(f"!! skip {name}: not found at {path}")
            continue
        print(f"\n===== loading {name} =====", flush=True)
        _reset_peak()
        model, tokenizer = load(str(path))
        load_peak = _peak_gb()
        tot_t, tot_tok = 0.0, 0
        results[name] = {}
        for t in tests:
            messages = BUILDERS[t["cat"]](t["input"])
            out, dt, ntok = run_one(model, tokenizer, messages)
            results[name][t["id"]] = out
            tot_t += dt
            tot_tok += ntok
            print(f"  [{t['id']}] {ntok} tok in {dt:.1f}s", flush=True)
        perf[name] = {
            "tok_per_s": round(tot_tok / tot_t, 1) if tot_t else 0,
            "peak_gb": round(_peak_gb(), 2),
            "load_peak_gb": round(load_peak, 2),
        }
        del model, tokenizer
        gc.collect()
        _clear_cache()

    # ---- write markdown report ----
    out_md = ROOT / "bench" / "results.md"
    lines = ["# Friday Model Bake-off — Results\n"]
    lines.append("## Perf summary\n")
    lines.append("| model | speed (tok/s) | peak mem (GB) |")
    lines.append("|---|---|---|")
    for name in results:
        p = perf[name]
        lines.append(f"| {name} | {p['tok_per_s']} | {p['peak_gb']} |")
    lines.append("")

    by_id = {t["id"]: t for t in tests}
    for t in tests:
        lines.append(f"## [{t['id']}] {t['cat']} — {t.get('dir','')}")
        lines.append(f"**输入**: {t['input']}")
        lines.append(f"_看点_: {t['look_for']}\n")
        for name in results:
            lines.append(f"**{name}**:\n```\n{results[name].get(t['id'],'(n/a)')}\n```")
        lines.append("")

    out_md.write_text("\n".join(lines))
    (ROOT / "bench" / "results.json").write_text(
        json.dumps({"perf": perf, "results": results, "by_id": list(by_id)}, ensure_ascii=False, indent=2)
    )
    print(f"\nWrote {out_md}")
    print("Perf:", json.dumps(perf, ensure_ascii=False))


if __name__ == "__main__":
    main()
