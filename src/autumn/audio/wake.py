"""Pinned local ONNX detector; no discovery, network or microphone on import."""

import numpy as np

from autumn.speech.assets import ARTIFACTS, Assets


class Detector:
    def __init__(self, root="", threshold=0.5):
        from openwakeword.model import Model

        assets = Assets()
        paths = {key: str(assets.get(key, root)) for key in ("wake", "wake_mel", "wake_embedding")}
        self.model = Model(
            wakeword_models=[paths["wake"]],
            inference_framework="onnx",
            melspec_model_path=paths["wake_mel"],
            embedding_model_path=paths["wake_embedding"],
            ncpu=1,
        )
        self.threshold = threshold
        self.consecutive = 0

    def reset(self):
        self.model.reset()
        self.consecutive = 0

    def predict(self, pcm):
        if pcm.dtype != np.int16 or pcm.shape != (1280,):
            raise ValueError("Wake requires one bounded 80 ms frame")
        score = max(float(v) for v in self.model.predict(pcm).values())
        self.consecutive = (
            self.consecutive + 1 if np.isfinite(score) and score >= self.threshold else 0
        )
        return score, self.consecutive >= 2


def profile(device, endpoint, threshold):
    from autumn.policy.confirmation import digest

    return digest(
        {
            "device": device,
            "endpoint": endpoint,
            "threshold": threshold,
            "consecutive_frames": 2,
            "artifacts": {k: ARTIFACTS[k][2] for k in ("wake", "wake_mel", "wake_embedding")},
        }
    )
