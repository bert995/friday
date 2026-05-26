#!/usr/bin/env python3
"""Friday backend playground.

Try the three skills from the terminal before the UI exists.

Usage:
  python3 try.py                 # interactive menu
  python3 try.py t "他这个人刀子嘴豆腐心。"     # one-shot translate
  python3 try.py w "I very like this movie."   # one-shot writing tips
  python3 try.py s "I no drink coffee today."  # one-shot speaking tips (typed)

Requires the oMLX server running with the models registered.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pet import brain  # noqa: E402

SKILLS = {
    "t": ("翻译", brain.translate),
    "w": ("写作建议", brain.writing_suggest),
    "s": ("口语点评", brain.speak_feedback),
}


def run(key: str, text: str) -> None:
    label, fn = SKILLS[key]
    t0 = time.time()
    try:
        out = fn(text)
    except Exception as e:  # noqa: BLE001
        print(f"\n⚠️  出错了: {e}\n（确认 oMLX 服务在跑、模型已注册）")
        return
    print(f"\n— {label} ({time.time() - t0:.1f}s) —\n{out}\n")


def interactive() -> None:
    print("周五 · 后端试用台   (Ctrl-C 退出)")
    while True:
        choice = input("\n选模式  [t]翻译  [w]写作  [s]口语(打字)  > ").strip().lower()
        if choice in ("q", "quit", "exit"):
            break
        if choice not in SKILLS:
            print("  请输入 t / w / s")
            continue
        text = input("输入内容 > ").strip()
        if text:
            run(choice, text)


if __name__ == "__main__":
    try:
        if len(sys.argv) >= 3 and sys.argv[1] in SKILLS:
            run(sys.argv[1], " ".join(sys.argv[2:]))
        else:
            interactive()
    except (KeyboardInterrupt, EOFError):
        print("\nbye 👋")
