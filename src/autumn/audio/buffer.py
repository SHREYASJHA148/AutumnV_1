"""Fixed-size callback storage and local 30 ms speech gating; no audio persistence."""

from __future__ import annotations

import math

import numpy as np


class CaptureBuffer:
    def __init__(self, rate: int, seconds: int = 20):
        if not 8000 <= rate <= 96000 or not 1 <= seconds <= 20:
            raise ValueError("Invalid capture bound")
        self.rate = rate
        self.data = np.empty(rate * seconds, dtype=np.float32)
        self.used = 0
        self.overflow = False

    def write(self, frames):
        flat = frames[:, 0] if frames.ndim == 2 else frames
        end = self.used + len(flat)
        if end > len(self.data):
            self.overflow = True
            return
        self.data[self.used : end] = flat
        self.used = end

    def recent(self):
        return self.data[max(0, self.used - int(self.rate * 0.06)) : self.used]

    def take(self):
        result = self.data[: self.used].copy()
        self.discard()
        return result

    def discard(self):
        self.data.fill(0)
        self.used = 0


def resample(audio, source_rate, target_rate):
    from scipy.signal import resample_poly

    array = np.asarray(audio, dtype=np.float32).reshape(-1)
    if len(array) > source_rate * 20 or not np.isfinite(array).all():
        raise ValueError("Invalid bounded audio")
    if source_rate != target_rate:
        divisor = math.gcd(source_rate, target_rate)
        array = resample_poly(array, target_rate // divisor, source_rate // divisor).astype(
            np.float32
        )
    return np.clip(array, -1, 1)


def normalize(audio, source_rate):
    return resample(audio, source_rate, 16000)


def speech_stats(audio):
    import webrtcvad

    data = np.asarray(audio, dtype=np.float32)
    rms = float(np.sqrt(np.mean(data**2))) if data.size else 0.0
    if rms < 0.001 or data.size < 480:
        return {"rms": rms, "voiced_seconds": 0.0, "voiced_ratio": 0.0}
    detector = webrtcvad.Vad(2)
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2").tobytes()
    voiced = 0
    count = 0
    for offset in range(0, len(pcm) - 959, 960):
        voiced += int(detector.is_speech(pcm[offset : offset + 960], 16000))
        count += 1
    return {"rms": rms, "voiced_seconds": voiced * 0.03, "voiced_ratio": voiced / max(count, 1)}
