import queue
import shutil
import time
from typing import Literal

from pydantic import Field

from autumn.controller.contracts import Contract


class SetupJob(Contract):
    kind: Literal["bootstrap", "inspect", "download", "import"]
    generation: int = Field(ge=0)
    root: str = ""
    source: str = ""
    artifact: str = Field(default="", max_length=32)


def setup_worker(commands, replies, generation, stopping, root, allow_faults, *, capture_gate=None):
    from autumn.setup.assets import checked_root, download, import_asset, inventory
    from autumn.speech.assets import ARTIFACTS

    last = 0.0
    acknowledged_generation = generation.value

    def send(kind, **fields):
        try:
            replies.put_nowait({"kind": kind, **fields})
        except queue.Full:
            if kind not in {"heartbeat", "setup_progress"}:
                raise

    def alive():
        nonlocal last
        if stopping.is_set():
            return False
        if time.monotonic() - last > 0.25:
            send("heartbeat")
            last = time.monotonic()
        return True

    while alive():
        if acknowledged_generation != generation.value:
            acknowledged_generation = generation.value
            send("idle")
        try:
            job = SetupJob.model_validate(commands.get(timeout=0.02))
        except queue.Empty:
            continue
        if job.kind == "bootstrap":
            send("setup_ready")
            continue
        if job.generation != generation.value:
            continue
        try:
            send("busy", timeout=12)
            target = checked_root(job.root)

            def valid():
                return alive() and generation.value == job.generation

            last_progress = 0.0

            def progress(count, total):
                nonlocal last_progress
                if time.monotonic() - last_progress > 0.15:
                    send("setup_progress", generation=job.generation, completed=count, total=total)
                    send("busy", timeout=12)
                    last_progress = time.monotonic()

            if job.kind in {"download", "import"}:
                if job.artifact not in ARTIFACTS:
                    raise ValueError("Unknown pinned asset")
                if job.kind == "download":
                    download(job.artifact, target, valid, progress)
                else:
                    import_asset(job.artifact, job.source, target, valid, progress)
            if not valid():
                raise InterruptedError()
            parent = target
            while not parent.exists():
                parent = parent.parent
            send(
                "setup_inventory",
                generation=job.generation,
                rows=inventory(target),
                free_gb=round(shutil.disk_usage(parent).free / 1024**3, 1),
                setup_space_ok=shutil.disk_usage(parent).free >= 12 * 1024**3,
            )
        except InterruptedError:
            send("setup_cancelled", generation=job.generation)
        except Exception as error:
            send("setup_error", generation=job.generation, code=type(error).__name__)
        finally:
            send("idle")
