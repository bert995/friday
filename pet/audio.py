"""Microphone capture + speech-to-text via the oMLX Whisper endpoint.

Records 16 kHz mono audio, writes a temp WAV, and POSTs it to
/v1/audio/transcriptions (OpenAI-compatible). Returns the transcript, which
the caller hands to brain.speak_feedback().

Note: this gives the *text* of what was said. Pronunciation/accent scoring is
acoustic and out of scope — Friday only coaches phrasing.
"""

from __future__ import annotations

import io
import wave

import httpx
import numpy as np
import sounddevice as sd

from . import config

SAMPLE_RATE = 16_000
_TIMEOUT = httpx.Timeout(120.0, connect=5.0)


def record(seconds: float = 6.0) -> bytes:
    """Record from the default mic and return WAV bytes (16-bit PCM mono)."""
    frames = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                    channels=1, dtype="int16")
    sd.wait()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(frames.tobytes())
    return buf.getvalue()


def transcribe(wav_bytes: bytes, *, language: str = "en") -> str:
    """Send WAV bytes to oMLX Whisper and return the transcript text."""
    headers = {"Authorization": f"Bearer {config.get_api_key()}"}
    files = {"file": ("speech.wav", wav_bytes, "audio/wav")}
    data = {"model": config.STT_MODEL, "language": language}
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(f"{config.BASE_URL}/audio/transcriptions",
                        headers=headers, files=files, data=data)
        r.raise_for_status()
        return r.json().get("text", "").strip()


def record_and_transcribe(seconds: float = 6.0, *, language: str = "en") -> str:
    return transcribe(record(seconds), language=language)


class Recorder:
    """Toggle recorder: start() then stop() -> WAV bytes.

    Used by the UI's mic button (click to start, click again to stop).
    Frames accumulate in a PortAudio callback thread; appending to a list
    is safe there.
    """

    def __init__(self, samplerate: int = SAMPLE_RATE):
        self.samplerate = samplerate
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        self._frames = []

        def _cb(indata, frames, time_info, status):  # noqa: ANN001
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.samplerate, channels=1, dtype="int16", callback=_cb
        )
        self._stream.start()

    def stop(self) -> bytes:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return b""
        data = np.concatenate(self._frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(data.tobytes())
        return buf.getvalue()

    def snapshot(self) -> bytes:
        """WAV bytes of everything recorded so far, WITHOUT stopping.

        Used for live partial transcription while recording continues.
        """
        frames = list(self._frames)  # copy ref; callback may still append
        if not frames:
            return b""
        data = np.concatenate(frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(data.tobytes())
        return buf.getvalue()

    @property
    def is_recording(self) -> bool:
        return self._stream is not None
