"""周五 / Friday — corner floating-window desktop pet (Phase 2).

A frameless, always-on-top card that sits in a screen corner:
  · 翻译 / 写作 / 口语 modes
  · async inference so the window never freezes
  · 🎤 toggle recording -> Whisper -> speaking feedback
  · global hotkey (⌘⇧T) -> translate whatever is on the clipboard

Run:  python3 -m pet.app   (from the repo root, inside the venv)
"""

from __future__ import annotations

import threading

from PySide6 import QtCore, QtGui, QtWidgets

from . import audio, brain

HOTKEY = "<cmd>+<shift>+t"
MODES = [("翻译", "translate"), ("写作", "writing"), ("口语", "speaking")]
PLACEHOLDER = {
    "translate": "输入中文或英文，回车翻译…",
    "writing": "贴一段英文，我帮你改得更自然…",
    "speaking": "点 🎤 说一句英文，或直接打字模拟…",
}
BRAIN_FN = {
    "translate": brain.translate,
    "writing": brain.writing_suggest,
    "speaking": brain.speak_feedback,
}


# --------------------------------------------------------------------------- #
# Background inference: run blocking brain/audio calls off the UI thread and
# deliver the result back via a queued Qt signal.
# --------------------------------------------------------------------------- #
class _Task(QtCore.QObject):
    done = QtCore.Signal(str)
    failed = QtCore.Signal(str)


def run_async(fn, args=(), *, on_done=None, on_error=None) -> _Task:
    task = _Task()
    if on_done:
        task.done.connect(on_done)
    if on_error:
        task.failed.connect(on_error)

    def worker():
        try:
            task.done.emit(fn(*args))
        except Exception as e:  # noqa: BLE001
            task.failed.emit(str(e))

    threading.Thread(target=worker, daemon=True).start()
    return task


class _Hotkey(QtCore.QObject):
    """Global hotkey via pynput; emits `fired` on the Qt thread."""

    fired = QtCore.Signal()

    def __init__(self, combo: str = HOTKEY):
        super().__init__()
        self.ok = False
        try:
            from pynput import keyboard

            self._listener = keyboard.GlobalHotKeys({combo: self.fired.emit})
            self._listener.start()
            self.ok = True
        except Exception:  # noqa: BLE001 — missing perms / lib; degrade gracefully
            self._listener = None


# --------------------------------------------------------------------------- #
# Draggable header (the window is frameless, so we move it ourselves).
# --------------------------------------------------------------------------- #
class DragHeader(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._press = None

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() == QtCore.Qt.LeftButton:
            self._press = e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._press is not None:
            self.window().move(e.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, e):  # noqa: N802
        self._press = None


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
class FridayWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.mode = "translate"
        self.recorder = audio.Recorder()
        self._tasks: set[_Task] = set()  # keep refs alive

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 470)
        self._build_ui()
        self._install_hotkey()
        self._move_to_corner()

    # ---- UI ----
    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QtWidgets.QFrame(objectName="card")
        shadow = QtWidgets.QGraphicsDropShadowEffect(blurRadius=28, xOffset=0, yOffset=6)
        shadow.setColor(QtGui.QColor(0, 0, 0, 70))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(16, 12, 16, 16)
        v.setSpacing(10)

        # header
        header = DragHeader()
        h = QtWidgets.QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        avatar = QtWidgets.QLabel("🦜", objectName="avatar")
        title = QtWidgets.QLabel("周五", objectName="title")
        self.status = QtWidgets.QLabel("待命中", objectName="status")
        self.status.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        close = QtWidgets.QPushButton("×", objectName="close")
        close.setFixedSize(22, 22)
        close.clicked.connect(QtWidgets.QApplication.quit)
        h.addWidget(avatar)
        h.addWidget(title)
        h.addStretch(1)
        h.addWidget(self.status, 1)
        h.addWidget(close)
        v.addWidget(header)

        # mode tabs
        tabs = QtWidgets.QHBoxLayout()
        tabs.setSpacing(6)
        self.mode_group = QtWidgets.QButtonGroup(self)
        for i, (label, key) in enumerate(MODES):
            b = QtWidgets.QPushButton(label, objectName="tab", checkable=True)
            b.setProperty("modeKey", key)
            b.clicked.connect(lambda _=False, k=key: self._set_mode(k))
            self.mode_group.addButton(b, i)
            tabs.addWidget(b)
            if key == self.mode:
                b.setChecked(True)
        v.addLayout(tabs)

        # input
        self.input = QtWidgets.QPlainTextEdit(objectName="input")
        self.input.setPlaceholderText(PLACEHOLDER[self.mode])
        self.input.setFixedHeight(74)
        v.addWidget(self.input)

        # action row: mic (speaking only) + send
        row = QtWidgets.QHBoxLayout()
        self.mic = QtWidgets.QPushButton("🎤 录音", objectName="mic")
        self.mic.clicked.connect(self._toggle_record)
        self.mic.setVisible(self.mode == "speaking")
        self.send = QtWidgets.QPushButton("发送  ⌘⏎", objectName="send")
        self.send.clicked.connect(self._on_send)
        row.addWidget(self.mic)
        row.addStretch(1)
        row.addWidget(self.send)
        v.addLayout(row)

        # result
        self.result = QtWidgets.QTextEdit(objectName="result", readOnly=True)
        self.result.setPlaceholderText("结果会显示在这里")
        v.addWidget(self.result, 1)

        # ⌘⏎ to send
        QtGui.QShortcut(QtGui.QKeySequence("Meta+Return"), self.input, self._on_send)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self.input, self._on_send)

        self.setStyleSheet(_QSS)

    def _set_mode(self, key: str):
        self.mode = key
        self.input.setPlaceholderText(PLACEHOLDER[key])
        self.mic.setVisible(key == "speaking")

    def _move_to_corner(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)

    # ---- actions ----
    def _busy(self, text: str):
        self.status.setText(text)
        self.send.setEnabled(False)

    def _ready(self):
        self.status.setText("待命中")
        self.send.setEnabled(True)

    def _show_result(self, text: str):
        self.result.setPlainText(text)
        self._ready()

    def _show_error(self, msg: str):
        self.result.setPlainText(f"⚠️ 出错了：{msg}\n\n（确认 oMLX 服务在运行）")
        self._ready()

    def _on_send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self._busy("🤔 思考中…")
        self.result.setPlainText("…")
        task = run_async(
            BRAIN_FN[self.mode], (text,),
            on_done=self._show_result, on_error=self._show_error,
        )
        self._tasks.add(task)

    def _toggle_record(self):
        if not self.recorder.is_recording:
            try:
                self.recorder.start()
            except Exception as e:  # noqa: BLE001
                self._show_error(f"麦克风打不开：{e}")
                return
            self.mic.setText("■ 停止")
            self.status.setText("🎧 听你说…（再点停止）")
        else:
            wav = self.recorder.stop()
            self.mic.setText("🎤 录音")
            if not wav:
                self._ready()
                return
            self._busy("🤔 识别中…")
            self.result.setPlainText("…")
            task = run_async(
                self._transcribe_and_coach, (wav,),
                on_done=self._show_result, on_error=self._show_error,
            )
            self._tasks.add(task)

    @staticmethod
    def _transcribe_and_coach(wav: bytes) -> str:
        transcript = audio.transcribe(wav)
        if not transcript:
            return "没听清，再说一遍试试～"
        feedback = brain.speak_feedback(transcript)
        return f"🎙️ 你说的：{transcript}\n\n{feedback}"

    # ---- global hotkey ----
    def _install_hotkey(self):
        self._hotkey = _Hotkey()
        self._hotkey.fired.connect(self._on_hotkey)
        if not self._hotkey.ok:
            self.status.setText("热键未启用")

    def _on_hotkey(self):
        clip = QtWidgets.QApplication.clipboard().text().strip()
        if not clip:
            self.status.setText("剪贴板是空的")
            return
        self._select_tab("translate")
        self.input.setPlainText(clip)
        self.show()
        self.raise_()
        self.activateWindow()
        self._on_send()

    def _select_tab(self, key: str):
        self._set_mode(key)
        for b in self.mode_group.buttons():
            b.setChecked(b.property("modeKey") == key)


_QSS = """
#card { background: #ffffff; border-radius: 16px; }
#avatar { font-size: 20px; }
#title { font-size: 15px; font-weight: 600; color: #1f2328; margin-left: 4px; }
#status { font-size: 11px; color: #8a8f98; }
#close { border: none; color: #b0b4bb; font-size: 16px; border-radius: 11px; }
#close:hover { background: #f0f1f3; color: #1f2328; }
#tab {
  border: none; padding: 6px 0; border-radius: 9px;
  font-size: 13px; color: #6b7280; background: #f3f4f6;
}
#tab:checked { background: #4f46e5; color: #ffffff; font-weight: 600; }
#input, #result {
  border: 1px solid #e6e8eb; border-radius: 10px; padding: 8px;
  font-size: 13px; color: #1f2328; background: #fcfcfd;
}
#input:focus { border-color: #4f46e5; }
#result { background: #f6f7f9; }
#send {
  border: none; background: #4f46e5; color: #fff; font-size: 13px;
  font-weight: 600; padding: 7px 16px; border-radius: 10px;
}
#send:hover { background: #4338ca; }
#send:disabled { background: #c7c9f0; }
#mic {
  border: 1px solid #e6e8eb; background: #fff; font-size: 13px;
  padding: 7px 14px; border-radius: 10px; color: #1f2328;
}
#mic:hover { border-color: #4f46e5; }
"""


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(True)
    win = FridayWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
