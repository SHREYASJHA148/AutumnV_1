"""Accelerated synthetic wake inference, never a substitute for owner/household trials."""

import json
import time

import numpy as np

from autumn.audio.wake import Detector


def run(report):
    began = time.monotonic()
    result = {
        "scope": "synthetic silence/noise only; no microphone/speakers; NOT NFR-08 or NFR-10",
        "owner_attempts": 0,
        "household_audio_seconds": 0,
    }
    try:
        detector = Detector()
        rows = []
        for kind in ("silence", "noise"):
            detector.reset()
            random = np.random.default_rng(62)
            maximum = 0.0
            triggers = 0
            started = time.process_time()
            for _ in range(125):
                frame = (
                    np.zeros(1280, dtype=np.int16)
                    if kind == "silence"
                    else random.integers(-100, 101, 1280, dtype=np.int16)
                )
                score, hit = detector.predict(frame)
                frame.fill(0)
                maximum = max(maximum, score)
                triggers += int(hit)
            rows.append(
                {
                    "kind": kind,
                    "synthetic_audio_seconds": 10,
                    "maximum_score": maximum,
                    "trigger_frames": triggers,
                    "cpu_seconds": round(time.process_time() - started, 3),
                }
            )
        result["trials"] = rows
        result["passed"] = not any(row["trigger_frames"] for row in rows)
    except Exception as error:
        result["passed"] = False
        result["error_type"] = type(error).__name__
    result["elapsed_seconds"] = round(time.monotonic() - began, 3)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["passed"] else 1
