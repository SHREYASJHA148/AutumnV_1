import numpy as np
import pytest

from autumn.audio.buffer import CaptureBuffer, normalize, resample, speech_stats
from autumn.speech.assets import native_path
from autumn.speech.synthesis import short_reply
from autumn.speech.workers import SpeechJob


def test_capture_buffer_is_bounded_and_discard_zeros_memory():
    buffer = CaptureBuffer(16000, 1)
    buffer.write(np.ones((8000, 1), dtype=np.float32))
    assert buffer.used == 8000
    buffer.write(np.ones(9000, dtype=np.float32))
    assert buffer.overflow and buffer.used == 8000
    data = buffer.take()
    assert len(data) == 8000 and buffer.used == 0 and np.count_nonzero(buffer.data) == 0


def test_resampling_shapes_and_invalid_audio_refusal():
    data = np.sin(np.arange(48000, dtype=np.float32) * 0.04) * 0.1
    assert len(normalize(data, 48000)) == 16000
    assert len(resample(data, 48000, 44100)) == 44100
    with pytest.raises(ValueError):
        normalize(np.array([np.nan], dtype=np.float32), 16000)
    with pytest.raises(ValueError):
        normalize(np.zeros(320001, dtype=np.float32), 16000)


def test_silence_has_no_voiced_frames():
    stats = speech_stats(np.zeros(16000, dtype=np.float32))
    assert stats["voiced_seconds"] == 0 and stats["rms"] == 0


def test_short_spoken_policy_and_binary_ipc_contract():
    assert short_reply("First. Second. Third.") == "First. Second."
    assert len(short_reply("word " * 100).split()) == 36
    pcm = bytes(range(256)) * 10
    job = SpeechJob(kind="transcribe", generation=2, pcm=pcm)
    assert SpeechJob.model_validate(job.model_dump(mode="python")).pcm == pcm


def test_native_non_ascii_file_path_uses_same_existing_file(tmp_path):
    path = tmp_path / "pronunciation é"
    path.mkdir()
    (path / "fixed.txt").write_text("fixed", encoding="utf-8")
    from pathlib import Path
    alias = Path(native_path(path))
    assert alias.samefile(path) and (alias / "fixed.txt").read_text() == "fixed"
