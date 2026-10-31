from autumn.audio.source import FakeAudioSource


def test_audio_injection_and_close_discards_remaining_frames():
    source = FakeAudioSource((b"one", b"two"))
    frames = source.frames()
    assert next(frames) == b"one"
    source.close()
    assert list(frames) == []
