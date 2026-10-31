"""Owned wake listener, bounded frame queue; closes before command capture begins."""

import queue
import time
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field

from autumn.controller.contracts import Contract


class WakeJob(Contract):
    kind: Literal["bootstrap", "listen", "check", "load_calibration", "save_calibration"]
    generation: int = Field(ge=0)
    operation_id: UUID | None = None
    mode: Literal["arm", "calibrate"] = "arm"
    device_id: str = ""
    assets_root: str = ""
    threshold: float = Field(default=0.5, ge=0.1, le=0.95)
    record: dict | None = None


def wake_worker(commands, replies, generation, stopping, root, allow_faults, *, capture_gate=None):
    import threading

    import numpy as np
    import sounddevice as sd

    from autumn.audio.buffer import normalize
    from autumn.audio.calibration import Calibration, load, save
    from autumn.audio.devices import default_endpoint, resolve_device
    from autumn.audio.wake import Detector, profile
    from autumn.speech.assets import Assets
    from autumn.winworker.cache import configure

    configure(Path(root))
    detector = None
    loaded = None
    beat = 0.0

    def send(kind, **fields):
        try:
            replies.put_nowait({"kind": kind, **fields}) if kind in {
                "heartbeat",
                "wake_score",
            } else replies.put({"kind": kind, **fields}, timeout=0.25)
        except queue.Full:
            if kind not in {"heartbeat", "wake_score"}:
                raise

    def alive():
        nonlocal beat
        if stopping.is_set():
            return False
        if time.monotonic() - beat > 0.25:
            send("heartbeat")
            beat = time.monotonic()
        return True

    acknowledged_generation = generation.value
    while alive():
        if generation.value != acknowledged_generation:
            acknowledged_generation = generation.value
            send("idle")
        try:
            job = WakeJob.model_validate(commands.get(timeout=0.02))
        except queue.Empty:
            continue
        if job.kind == "bootstrap":
            send("wake_ready")
            continue
        if job.generation != generation.value:
            continue
        if job.kind in {"load_calibration", "save_calibration"}:
            try:
                if job.kind == "save_calibration":
                    save(Path(root), Calibration.model_validate(job.record))
                record = load(Path(root))
                send(
                    "wake_calibration",
                    record=record.model_dump() if record else None,
                    generation=job.generation,
                )
            except (OSError, ValueError):
                send(
                    "wake_error",
                    generation=job.generation,
                    operation_id=str(job.operation_id),
                    code="WAKE_COMPONENT_UNAVAILABLE",
                )
            continue
        stream = None
        frames = queue.Queue(maxsize=8)
        overflow = threading.Event()

        def valid():
            return (
                alive()
                and generation.value == job.generation
                and (capture_gate is None or capture_gate.value)
            )

        try:
            send("busy", timeout=15)
            if job.kind == "check":
                assets = Assets()
                verified = all(
                    assets.get(k, job.assets_root).is_file()
                    for k in ("wake", "wake_mel", "wake_embedding")
                )
                send("wake_checked", verified=verified, generation=job.generation)
                continue
            device = resolve_device(job.device_id, "input")
            endpoint = default_endpoint("input") if not job.device_id else None
            signature = profile(device["id"], endpoint, job.threshold)
            if job.mode == "arm":
                record = load(Path(root))
                if record is None or not record.accepted or record.profile != signature:
                    raise PermissionError("Calibration required")
            if loaded != (job.assets_root, job.threshold):
                detector = Detector(job.assets_root, job.threshold)
                loaded = (job.assets_root, job.threshold)
            detector.reset()
            if not valid():
                continue

            def callback(data, count, timing, status):
                if status:
                    overflow.set()
                    return
                try:
                    frames.put_nowait(data[:, 0].copy())
                except queue.Full:
                    overflow.set()

            stream = sd.InputStream(
                device=device["index"],
                samplerate=device["rate"],
                channels=1,
                dtype="float32",
                blocksize=round(device["rate"] * 0.08),
                callback=callback,
            )
            if not valid():
                continue
            stream.start()
            began = time.monotonic()
            cpu = time.process_time()
            import ctypes

            class Power(ctypes.Structure):
                _fields_ = [
                    ("ac", ctypes.c_ubyte),
                    ("flags", ctypes.c_ubyte),
                    ("percent", ctypes.c_ubyte),
                    ("reserved", ctypes.c_ubyte),
                    ("life", ctypes.c_ulong),
                    ("full", ctypes.c_ulong),
                ]

            power = Power()
            mains = True
            checked = began
            last_score = 0.0
            trigger = False
            send(
                "wake_listening",
                operation_id=str(job.operation_id),
                generation=job.generation,
                profile=signature,
            )
            send("idle")
            while valid() and stream.active:
                if overflow.is_set():
                    raise RuntimeError("Audio overrun")
                now = time.monotonic()
                if endpoint is not None and now - checked > 0.5:
                    checked = now
                    if default_endpoint("input") != endpoint:
                        raise RuntimeError("Default device changed")
                try:
                    frame = frames.get(timeout=0.02)
                except queue.Empty:
                    continue
                normalized = normalize(frame, device["rate"])
                frame.fill(0)
                pcm = (normalized * 32767).astype(np.int16)
                normalized.fill(0)
                if len(pcm) != 1280:
                    raise ValueError("Unexpected audio frame")
                score, trigger = detector.predict(pcm)
                pcm.fill(0)
                if now - last_score > 0.5:
                    mains = mains and bool(
                        ctypes.WinDLL("kernel32").GetSystemPowerStatus(ctypes.byref(power))
                        and power.ac == 1
                    )
                    send(
                        "wake_score",
                        generation=job.generation,
                        operation_id=str(job.operation_id),
                        score=round(score, 4),
                        cpu_one_core_percent=round(
                            (time.process_time() - cpu) / max(0.01, now - began) * 100, 2
                        ),
                        wall_seconds=round(now - began, 2),
                        on_mains=mains,
                    )
                    last_score = now
                if trigger:
                    break
            # A wake never competes with the command recorder for the microphone.
            stream.abort()
            stream.close()
            stream = None
            if trigger and valid():
                send("wake_detected", generation=job.generation, operation_id=str(job.operation_id))
        except Exception as error:
            send(
                "wake_error",
                generation=job.generation,
                operation_id=str(job.operation_id),
                code="CALIBRATION_REQUIRED"
                if isinstance(error, PermissionError)
                else "WAKE_COMPONENT_UNAVAILABLE",
            )
        finally:
            if stream is not None:
                stream.abort()
                stream.close()
            for name in ('frame','normalized','pcm'):
                value=locals().get(name)
                if isinstance(value,np.ndarray):
                    value.fill(0)
            if detector is not None:
                detector.reset()
            while not frames.empty():
                try:
                    frames.get_nowait().fill(0)
                except queue.Empty:
                    break
            send("wake_stopped", operation_id=str(job.operation_id), generation=job.generation)
            send("idle")
