"""In-memory English whisper.cpp with VAD/confidence refusal and native cancellation."""

import contextlib
import os
import re
import time

import numpy as np

from autumn.audio.buffer import speech_stats
from autumn.speech.assets import Assets, native_path


def _discard_native_log(*_args):
    pass


class Recognizer:
    def __init__(self):
        self.assets = Assets()
        self.model = None
        self.loaded = None

    def transcribe(self, pcm, model_key, root, checkpoint):
        audio = np.frombuffer(pcm, dtype="<f4").copy()
        try:
            return self._decode(audio, model_key, root, checkpoint)
        finally:
            audio.fill(0)

    def _decode(self, audio, model_key, root, checkpoint):
        if not 1 <= len(audio) <= 320000:
            return {"accepted": False, "code": "EMPTY_AUDIO"}
        stats = speech_stats(audio)
        if stats["rms"] < 0.001:
            return {"accepted": False, "code": "SILENT_CAPTURE", "stats": stats}
        if stats["voiced_seconds"] < 0.30 or stats["voiced_ratio"] < 0.08:
            return {"accepted": False, "code": "NO_SPEECH", "stats": stats}
        deadline = time.monotonic() + 15
        path = self.assets.get(model_key, root)
        if not checkpoint():
            return {"accepted": False, "code": "CANCELLED"}
        if self.loaded != str(path):
            import _pywhispercpp
            from pywhispercpp.model import Model

            _pywhispercpp.whisper_log_set(_discard_native_log)
            self.model = None
            # Windowed executables have sys.stderr=None; the library flushes it on load.
            with open(os.devnull, "w") as sink, contextlib.redirect_stderr(sink), contextlib.redirect_stdout(sink):
                self.model = Model(
                    native_path(path),
                    context_params={"use_gpu": False},
                    n_threads=4,
                    redirect_whispercpp_logs_to=os.devnull,
                    print_realtime=False,
                    print_progress=False,
                    print_timestamps=False,
                    language="en",
                    no_context=True,
                    initial_prompt="Autumn. Open apps and folders. Volume, mute, music, screenshots, filenames.",
                )
            self.loaded = str(path)
        # Both Python and native diagnostic streams are silenced: no recognized text in logs.
        with (
            open(os.devnull, "w") as sink,
            contextlib.redirect_stdout(sink),
            contextlib.redirect_stderr(sink),
        ):
            segments = self.model.transcribe(
                audio,
                language="en",
                no_context=True,
                print_realtime=False,
                print_progress=False,
                print_timestamps=False,
                suppress_blank=True,
                no_speech_thold=0.6,
                extract_probability=True,
                abort_callback=lambda: not checkpoint() or time.monotonic() > deadline,
            )
        audio.fill(0)
        if not checkpoint() or time.monotonic() > deadline:
            return {"accepted": False, "code": "CANCELLED"}
        if any(not np.isfinite(s.probability) or s.probability < 0.35 for s in segments):
            return {"accepted": False, "code": "LOW_CONFIDENCE", "stats": stats}
        usable = segments
        text = " ".join(s.text for s in usable).strip()
        if (
            not text
            or not re.search("[A-Za-z]", text)
            or re.search(r"\[(?:blank|silence|music|noise)|\((?:silence|music|noise)", text, re.I)
        ):
            return {"accepted": False, "code": "LOW_CONFIDENCE", "stats": stats}
        return {
            "accepted": True,
            "code": "OK",
            "text": text[:2000],
            "stats": stats,
            "confidence": float(min(s.probability for s in usable)),
        }
