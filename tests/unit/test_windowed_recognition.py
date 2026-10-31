import contextlib
import sys
from types import SimpleNamespace

import numpy as np
import pywhispercpp.model

from autumn.speech import recognition


def test_model_load_and_decode_have_null_streams_in_windowed_app(monkeypatch, tmp_path):
    calls = []

    class Model:
        def __init__(self, *args, **kwargs):
            assert sys.stderr is not None and sys.stdout is not None
            sys.stderr.flush()
            sys.stderr.fileno()
            calls.append("load")

        def transcribe(self, audio, **kwargs):
            assert sys.stderr is not None and sys.stdout is not None
            calls.append("decode")
            return [SimpleNamespace(text="help", probability=0.9)]

    path = tmp_path / "fixed-model.bin"
    path.touch()
    model = recognition.Recognizer()
    monkeypatch.setattr(model.assets, "get", lambda *args: path)
    monkeypatch.setattr(pywhispercpp.model, "Model", Model)
    monkeypatch.setattr(pywhispercpp.model.pw, "whisper_log_set", lambda callback: calls.append("silence"))
    monkeypatch.setattr(recognition, "speech_stats", lambda audio: {"rms": 0.1, "voiced_seconds": 1, "voiced_ratio": 1})
    with contextlib.redirect_stderr(None), contextlib.redirect_stdout(None):
        result = model.transcribe(np.zeros(16000, dtype="<f4").tobytes(), "small.en", "", lambda: True)
    assert result["accepted"] and calls == ["silence", "load", "decode"]
