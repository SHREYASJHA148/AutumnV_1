"""Capture, recognition and playback live in separate supervised processes."""

from __future__ import annotations

import os
import queue
import time
from typing import Literal
from uuid import UUID

from pydantic import Field

from autumn.controller.contracts import Contract


class SpeechJob(Contract):
    kind: Literal[
        "bootstrap",
        "devices",
        "capture",
        "finish_capture",
        "transcribe",
        "speak",
        "play_pcm",
        "health",
    ]
    generation: int = Field(ge=0)
    operation_id: UUID | None = None
    device_id: str = ""
    pcm: bytes = Field(default=b"", max_length=1_280_000)
    sample_rate: int = Field(default=16000, ge=8000, le=96000)
    model_key: Literal["base.en", "small.en"] = "small.en"
    assets_root: str = ""
    text: str = Field(default="", max_length=2000)
    volume: float = Field(default=0.8, ge=0, le=1)
    rate: float = Field(default=1, ge=0.6, le=1.6)
    seconds: int = Field(default=20, ge=1, le=20)
    endpoint: bool = False
    discard: bool = False


def capture_worker(*args, **kwargs):
    speech_main(*args, role="capture", **kwargs)


def recognition_worker(*args, **kwargs):
    speech_main(*args, role="recognition", **kwargs)


def playback_worker(*args, **kwargs):
    speech_main(*args, role="playback", **kwargs)


def speech_main(commands, replies, generation, stopping, root, allow_faults, *, role, capture_gate=None):
    import numpy as np

    from autumn.audio.buffer import CaptureBuffer, normalize, resample, speech_stats
    from autumn.audio.devices import default_endpoint, enumerate_devices, resolve_device
    from autumn.speech.recognition import Recognizer
    from autumn.speech.synthesis import Synthesizer

    parent = os.getppid()
    last_beat = 0.0
    stream = None
    buffer = None
    current = None
    began = 0.0
    last_meter = 0.0
    last_voice = 0.0
    voiced_seen = False
    device = None
    default_input = None
    last_default_check = 0.0
    recognizer = Recognizer() if role == "recognition" else None
    synthesizer = Synthesizer() if role == "playback" else None

    def send(kind, **fields):
        if kind in {"level", "heartbeat"}:
            try:
                replies.put_nowait({"kind": kind, **fields})
            except queue.Full:
                pass
        else:
            replies.put({"kind": kind, **fields}, timeout=0.25)

    def alive():
        nonlocal last_beat
        if stopping.is_set() or os.getppid() != parent:
            return False
        if time.monotonic() - last_beat > 0.25:
            send("heartbeat")
            last_beat = time.monotonic()
        return True

    def checkpoint(job):
        return alive() and generation.value == job.generation

    def finish(discard=False, code="OK"):
        nonlocal stream, buffer, current
        job = current
        if stream is not None:
            stream.abort()
            stream.close()
            stream = None
        if job is not None and buffer is not None:
            if not discard and checkpoint(job) and not buffer.overflow:
                data = normalize(buffer.take(), device["rate"])
                send(
                    "captured",
                    operation_id=str(job.operation_id),
                    generation=job.generation,
                    pcm=data.astype("<f4").tobytes(),
                    sample_rate=16000,
                    code=code,
                )
                data.fill(0)
            else:
                buffer.discard()
                send(
                    "capture_error",
                    operation_id=str(job.operation_id),
                    generation=job.generation,
                    code=code,
                )
        buffer = None
        current = None
        send("idle")

    try:
        while alive():
            if current is not None:
                if not checkpoint(current):
                    finish(True, "CANCELLED")
                elif capture_gate is not None and not capture_gate.value:
                    finish()
                elif buffer.overflow:
                    finish(True, "BUFFER_OVERFLOW")
                elif stream is not None and not stream.active:
                    finish(True, "DEVICE_UNAVAILABLE")
                else:
                    now = time.monotonic()
                    if (
                        not current.device_id
                        and default_input is not None
                        and now - last_default_check > 0.5
                    ):
                        last_default_check = now
                        if default_endpoint("input") != default_input:
                            finish(True, "DEVICE_UNAVAILABLE")
                            continue
                    if now - last_meter > 0.10:
                        recent = buffer.recent().copy()
                        level = float(np.sqrt(np.mean(recent**2))) if len(recent) else 0
                        send(
                            "level",
                            generation=current.generation,
                            value=min(1, level * 8),
                            seconds=round(now - began, 1),
                        )
                        if current.endpoint and len(recent):
                            data = normalize(recent, device["rate"])
                            stats = speech_stats(data)
                            if stats["voiced_seconds"]:
                                voiced_seen = True
                                last_voice = now
                        last_meter = now
                    if now - began >= current.seconds - 0.05:
                        finish(False, "LIMIT_REACHED")
                    elif current.endpoint and voiced_seen and now - last_voice >= 0.8:
                        finish()
                    elif current.endpoint and not voiced_seen and now - began >= 5:
                        finish(True, "SILENT_CAPTURE")
            try:
                job = SpeechJob.model_validate(commands.get(timeout=0.02))
            except queue.Empty:
                continue
            if job.kind == "bootstrap":
                send("speech_ready", role=role)
                continue
            if not checkpoint(job):
                continue
            try:
                if job.kind == "devices" and role == "capture":
                    send("devices", rows=enumerate_devices())
                elif job.kind == "health" and role == "recognition":
                    import shutil
                    from pathlib import Path

                    send("busy", timeout=15)
                    verified = {}
                    for key in (job.model_key, "voice", "voice_config"):
                        try:
                            recognizer.assets.get(key, job.assets_root)
                            verified[key] = True
                        except (OSError, ValueError):
                            verified[key] = False
                    send(
                        "speech_health",
                        verified=verified,
                        free_gb=round(shutil.disk_usage(Path(root)).free / 1024**3, 1),
                    )
                    send("idle")
                elif job.kind == "capture" and role == "capture":
                    if current is not None:
                        continue
                    if capture_gate is not None and not capture_gate.value:
                        send("capture_error", operation_id=str(job.operation_id), generation=job.generation, code="EMPTY_AUDIO")
                        continue
                    send("busy", timeout=job.seconds + 2)
                    import sounddevice as sd

                    device = resolve_device(job.device_id, "input")
                    from pathlib import Path

                    from autumn.winworker.cache import configure

                    configure(Path(root))
                    default_input = default_endpoint("input") if not job.device_id else None
                    buffer = CaptureBuffer(device["rate"])
                    current = job
                    if not checkpoint(job) or (capture_gate is not None and not capture_gate.value):
                        finish(True, "EMPTY_AUDIO")
                        continue

                    def callback(data, frames, timing, status):
                        if status:
                            buffer.overflow = True
                            return
                        buffer.write(data)

                    stream = sd.InputStream(
                        device=device["index"],
                        samplerate=device["rate"],
                        channels=1,
                        dtype="float32",
                        blocksize=max(1, int(device["rate"] * 0.03)),
                        callback=callback,
                    )
                    began = time.monotonic()
                    last_voice = began
                    voiced_seen = False
                    if not checkpoint(job) or (capture_gate is not None and not capture_gate.value):
                        finish(True, "CANCELLED")
                        continue
                    stream.start()
                    send("busy", timeout=job.seconds + 2)
                    send("recording", operation_id=str(job.operation_id), generation=job.generation)
                elif job.kind == "finish_capture" and role == "capture" and current is not None:
                    if job.operation_id == current.operation_id:
                        finish(job.discard, "CANCELLED" if job.discard else "OK")
                elif job.kind == "transcribe" and role == "recognition":
                    send("busy", timeout=17)
                    result = recognizer.transcribe(
                        job.pcm, job.model_key, job.assets_root, lambda: checkpoint(job)
                    )
                    send(
                        "recognized",
                        operation_id=str(job.operation_id),
                        generation=job.generation,
                        result=result,
                    )
                    send("idle")
                elif job.kind in {"speak", "play_pcm"} and role == "playback":
                    send("busy", timeout=32)
                    if job.kind == "speak":
                        try:
                            data, rate = synthesizer.render(
                                job.text,
                                job.assets_root,
                                job.volume,
                                job.rate,
                                lambda: checkpoint(job),
                            )
                        except InterruptedError:
                            raise
                        except Exception:
                            if job.device_id:
                                raise RuntimeError(
                                    "Selected output cannot use default-only Windows fallback"
                                ) from None
                            windows_speak(
                                job.text, job.volume, job.rate, lambda: checkpoint(job), root
                            )
                            send(
                                "played",
                                operation_id=str(job.operation_id),
                                generation=job.generation,
                                engine="Windows female voice",
                            )
                            send("idle")
                            continue
                    else:
                        data = np.frombuffer(job.pcm, dtype="<f4").copy() * job.volume
                        rate = job.sample_rate
                    if not checkpoint(job):
                        raise InterruptedError()
                    import sounddevice as sd

                    output = resolve_device(job.device_id, "output")
                    from pathlib import Path

                    from autumn.winworker.cache import configure
                    configure(Path(root))
                    default_output = default_endpoint("output") if not job.device_id else None
                    last_output_check = time.monotonic()
                    data = resample(data, rate, output["rate"])
                    rate = output["rate"]
                    offset = 0

                    def playback(out, frames, timing, status):
                        nonlocal offset
                        out.fill(0)
                        count = min(frames, len(data) - offset)
                        if count > 0:
                            out[:count, 0] = data[offset : offset + count]
                            offset += count
                        if (
                            offset >= len(data)
                            or generation.value != job.generation
                            or stopping.is_set()
                        ):
                            raise sd.CallbackStop()

                    with sd.OutputStream(
                        device=output["index"],
                        samplerate=rate,
                        channels=1,
                        dtype="float32",
                        callback=playback,
                    ) as playing:
                        until = time.monotonic() + 15.5
                        while playing.active and checkpoint(job) and time.monotonic() < until:
                            if default_output is not None and time.monotonic() - last_output_check > 0.5:
                                last_output_check = time.monotonic()
                                if default_endpoint("output") != default_output:
                                    raise RuntimeError("Output changed; refresh devices")
                            stopping.wait(0.02)
                        timed_out = playing.active and time.monotonic() >= until
                        playing.abort()
                    data.fill(0)
                    if timed_out:
                        raise TimeoutError("Playback deadline reached")
                    if checkpoint(job):
                        send(
                            "played",
                            operation_id=str(job.operation_id),
                            generation=job.generation,
                            engine="Piper" if job.kind == "speak" else "test recording",
                        )
                    send("idle")
            except InterruptedError:
                send("idle")
            except Exception:
                if current is not None:
                    finish(True, "DEVICE_UNAVAILABLE")
                send(
                    "speech_error",
                    role=role,
                    operation_id=str(job.operation_id),
                    generation=job.generation,
                    code="COMPONENT_UNAVAILABLE",
                )
                send("idle")
            finally:
                if role == "playback" and "data" in locals():
                    data.fill(0)
                    data = np.empty(0, dtype=np.float32)
                # Keep only the active capture contract, not completed audio/text IPC payloads.
                job = None
                if role == "recognition":
                    result = None
    finally:
        if stream is not None:
            stream.abort()
            stream.close()
        if buffer is not None:
            buffer.discard()


def windows_speak(text, volume, rate, checkpoint, root):
    from pathlib import Path

    from autumn.winworker.cache import configure

    configure(Path(root))
    import win32com.client

    from autumn.speech.synthesis import short_reply

    voice = win32com.client.Dispatch("SAPI.SpVoice")
    female = next((v for v in voice.GetVoices() if "zira" in v.GetDescription().casefold()), None)
    if female is None:
        raise RuntimeError("No verified female English Windows voice")
    voice.Voice = female
    voice.Volume = int(volume * 100)
    voice.Rate = round((rate - 1) * 5)
    if not checkpoint():
        raise InterruptedError()
    voice.Speak(short_reply(text), 3)
    until = time.monotonic() + 15
    while not voice.WaitUntilDone(0):
        if not checkpoint() or time.monotonic() > until:
            voice.Speak("", 3)
            if not checkpoint():
                raise InterruptedError()
            raise TimeoutError("Windows voice deadline reached")
        time.sleep(0.02)
