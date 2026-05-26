"""Python <-> JS bridge for the pywebview shell.

The web UI calls these via `window.pywebview.api.<method>()`. Things a browser
can't do (mic capture, global hotkey, clipboard watching) live here; results
are pushed back to JS with `window.evaluate_js(...)`.

JS hooks the web UI must define (see web/index.html):
  window.fridayPartial(text)      # live transcription update while recording
  window.fridayClipboard(text)    # text grabbed via hotkey / clipboard watch
"""

from __future__ import annotations

import json
import threading
import time

from . import audio, brain

_PARTIAL_EVERY = 1.2  # seconds between live-transcription refreshes


class Api:
    def __init__(self):
        self._window = None
        self.recorder = audio.Recorder()
        self._partial_thread: threading.Thread | None = None
        self._clip_watch = False
        self._self_copied: str | None = None  # text WE put on the clipboard

    def attach(self, window) -> None:
        self._window = window

    # ---- JS -> Python: the three skills ----
    def translate(self, text: str) -> str:
        return brain.translate(text)

    def writing_suggest(self, text: str) -> str:
        return brain.writing_suggest(text)

    def speak_feedback(self, text: str) -> str:
        return brain.speak_feedback(text)

    # ---- JS -> Python: speaking with live transcription ----
    def start_recording(self) -> bool:
        try:
            self.recorder.start()
        except Exception:  # noqa: BLE001
            return False
        self._partial_thread = threading.Thread(target=self._stream_partials, daemon=True)
        self._partial_thread.start()
        return True

    def stop_recording(self) -> dict:
        """Stop, do a final transcription + feedback, return both."""
        wav = self.recorder.stop()
        if not wav:
            return {"transcript": "", "feedback": "没听清，再说一遍试试～"}
        transcript = audio.transcribe(wav)
        if not transcript:
            return {"transcript": "", "feedback": "没听清，再说一遍试试～"}
        feedback = brain.speak_feedback(transcript)
        return {"transcript": transcript, "feedback": feedback}

    def _stream_partials(self) -> None:
        while self.recorder.is_recording:
            time.sleep(_PARTIAL_EVERY)
            wav = self.recorder.snapshot()
            if not wav or not self.recorder.is_recording:
                continue
            try:
                partial = audio.transcribe(wav)
            except Exception:  # noqa: BLE001
                continue
            if partial and self.recorder.is_recording:
                self._push("fridayPartial", partial)

    # ---- JS -> Python: 划词翻译 toggle ----
    def set_clip_watch(self, on: bool) -> bool:
        self._clip_watch = bool(on)
        return self._clip_watch

    # ---- JS -> Python: copy a result to the clipboard ----
    def copy_output(self, text: str) -> bool:
        try:
            from AppKit import NSPasteboard

            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(text, "public.utf8-plain-text")
            # Remember it so the clipboard watcher doesn't translate our own copy.
            self._self_copied = text.strip()
            return True
        except Exception:  # noqa: BLE001
            return False

    # ---- background: global hotkey + clipboard watch ----
    def start_background(self) -> None:
        self._install_hotkey()
        threading.Thread(target=self._watch_clipboard, daemon=True).start()

    def _install_hotkey(self) -> None:
        try:
            from pynput import keyboard

            self._listener = keyboard.GlobalHotKeys(
                {"<cmd>+<shift>+t": self._grab_clipboard}
            )
            self._listener.start()
        except Exception:  # noqa: BLE001
            self._listener = None

    def _watch_clipboard(self) -> None:
        try:
            from AppKit import NSPasteboard
        except Exception:  # noqa: BLE001
            return
        pb = NSPasteboard.generalPasteboard()
        last = pb.changeCount()
        while True:
            time.sleep(0.4)
            if not self._clip_watch:
                last = pb.changeCount()
                continue
            cur = pb.changeCount()
            if cur != last:
                last = cur
                text = (pb.stringForType_("public.utf8-plain-text") or "").strip()
                if text and text == self._self_copied:
                    self._self_copied = None  # our own copy — skip once
                    continue
                if text:
                    self._push("fridayClipboard", text)

    def _grab_clipboard(self) -> None:
        try:
            from AppKit import NSPasteboard

            text = NSPasteboard.generalPasteboard().stringForType_(
                "public.utf8-plain-text"
            ) or ""
        except Exception:  # noqa: BLE001
            text = ""
        if text.strip():
            self._push("fridayClipboard", text.strip())

    # ---- helper: call a JS function with one string arg ----
    def _push(self, js_fn: str, payload: str) -> None:
        if self._window is None:
            return
        try:
            self._window.evaluate_js(f"window.{js_fn}({json.dumps(payload)})")
        except Exception:  # noqa: BLE001
            pass
