"""Development probe: synthetic PCM only, no microphone, speakers or action dispatch."""

import json
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

import numpy as np

from autumn.audio.buffer import normalize
from autumn.speech.assets import Assets
from autumn.speech.service import SpeechService
from autumn.speech.synthesis import Synthesizer

PHRASES = (
    "Open Notepad.", "Open Calculator.", "What can you do?", "Set volume to fifty percent.",
    "Mute the speakers.", "Pause the music.", "Take a screenshot.", "Open Downloads.",
    "Find a PDF file.", "Open Spotify.",
)


def run(report: Path, root: Path) -> int:
    service = SpeechService(root)
    started = time.monotonic()
    result = {"frozen": bool(getattr(sys, "frozen", False)), "scope": "public synthetic development audio; NOT owner/NFR-03 or GPU acceptance", "microphone_opened": False, "speaker_playback": False, "action_dispatches": 0}

    def stage(name):
        result["stage"] = name
        result["pipeline_operational"] = False
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2), encoding="utf-8")

    def wait(kind, operation=None):
        while time.monotonic() - started < 55:
            for event in service.poll():
                if event["kind"] in {"speech_error", "worker_failed"}:
                    result["worker_failure"] = {key: event[key] for key in ("kind", "role", "code", "disabled") if key in event}
                    raise RuntimeError("Speech worker failed")
                if event["kind"] == kind and (operation is None or event.get("operation_id") == str(operation)):
                    return event
            time.sleep(0.01)
        raise TimeoutError("Probe exceeded 55 seconds")

    def decode(pcm):
        operation = uuid4()
        then = time.monotonic()
        if not service.send("recognition", "transcribe", operation_id=operation, pcm=pcm):
            raise RuntimeError("Speech queue unavailable")
        response = wait("recognized", operation)
        return response["result"], round(time.monotonic() - then, 4)

    try:
        stage("artifact_checks")
        assets = Assets()
        result["verified_artifacts"] = {key: assets.get(key).is_file() for key in ("small.en", "base.en", "voice", "voice_config")}
        stage("device_enumeration_no_capture")
        service.send("capture", "devices")
        rows = wait("devices")["rows"]
        result["devices"] = {kind: len([row for row in rows if row["kind"] == kind]) for kind in ("input", "output")}
        stage("silence_and_noise")
        silence, _ = decode(np.zeros(16000, dtype="<f4").tobytes())
        result["silence_rejected"] = not silence["accepted"]
        noise = np.random.default_rng(42).normal(0, 0.02, 32000).astype("<f4")
        rejection, _ = decode(noise.tobytes())
        noise.fill(0)
        result["noise_rejected"] = not rejection["accepted"]
        synthesis = Synthesizer()
        records = []
        for phrase in PHRASES:
            stage("synthetic_case_" + str(len(records)))
            then = time.monotonic()
            audio, rate = synthesis.render(phrase, "", 0.8, 1, lambda: True)
            synth_seconds = round(time.monotonic() - then, 4)
            result["last_synthesis_seconds"] = synth_seconds
            stage("recognition_case_" + str(len(records)))
            pcm = normalize(audio, rate)
            audio.fill(0)
            response, decode_seconds = decode(pcm.astype("<f4").tobytes())
            pcm.fill(0)
            def canonical(text):
                return re.sub(r"[^a-z0-9]", "", text.casefold())
            records.append({"index": len(records), "accepted": response["accepted"], "exact_normalized_match": response["accepted"] and canonical(response["text"]) == canonical(phrase), "synthesis_seconds": synth_seconds, "recognition_seconds": decode_seconds})
        result["synthetic_cases"] = records
        result["synthetic_exact_matches"] = sum(row["exact_normalized_match"] for row in records)
        result["recognition_warm_p50_seconds"] = round(float(np.quantile([r["recognition_seconds"] for r in records[1:]], 0.5)), 4)
        result["recognition_warm_p95_seconds"] = round(float(np.quantile([r["recognition_seconds"] for r in records[1:]], 0.95)), 4)
        result["pipeline_operational"] = all(row["accepted"] for row in records) and result["silence_rejected"] and result["noise_rejected"]
        result["stage"] = "finished"
    except Exception as error:
        result["pipeline_operational"] = False
        result["error_type"] = type(error).__name__
    finally:
        result["clean_shutdown"] = service.shutdown()
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["pipeline_operational"] and result["clean_shutdown"] else 1
