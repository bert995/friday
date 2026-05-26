"""pywebview shell — a transparent, frameless, always-on-top window that hosts
the web UI (web/index.html) and wires it to the Python bridge.

Run:  python3 -m pet.shell   (from the repo root, inside the venv)
"""

from __future__ import annotations

from pathlib import Path

import webview

from .bridge import Api

WIN_W, WIN_H = 340, 620  # compact; card grows upward from the bottom-anchored cat
WEB = Path(__file__).resolve().parent.parent / "web" / "index.html"


def _corner_pos() -> tuple[int, int]:
    """Bottom-right of the main screen (falls back to a sane default)."""
    try:
        from AppKit import NSScreen

        frame = NSScreen.mainScreen().visibleFrame()
        x = int(frame.origin.x + frame.size.width - WIN_W - 24)
        y = int(frame.size.height - WIN_H - 24)  # pywebview y is from top
        return x, y
    except Exception:  # noqa: BLE001
        return 1100, 560


def main() -> None:
    api = Api()
    x, y = _corner_pos()
    window = webview.create_window(
        "周五",
        url=WEB.as_uri(),
        js_api=api,
        width=WIN_W,
        height=WIN_H,
        x=x,
        y=y,
        frameless=True,
        easy_drag=True,
        on_top=True,
        transparent=True,
    )
    api.attach(window)
    api.start_background()
    webview.start()


if __name__ == "__main__":
    main()
