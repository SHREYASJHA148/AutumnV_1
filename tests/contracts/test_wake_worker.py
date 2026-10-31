import time
from uuid import uuid4

from autumn.audio.wake_worker import WakeJob, wake_worker
from autumn.controller.worker import Supervisor


def no_hardware_worker(*args, **kwargs):
    import sounddevice

    def forbidden(**options):
        raise AssertionError("A microphone must never open before calibration")

    sounddevice.InputStream = forbidden
    wake_worker(*args, **kwargs)


def test_uncalibrated_arm_refused_in_owned_process_before_hardware(tmp_path):
    supervisor = Supervisor(tmp_path, worker_target=no_hardware_worker, owned_job=True)
    try:
        supervisor.capture_gate.value = True
        supervisor.submit(WakeJob(kind="listen", generation=0, operation_id=uuid4(), mode="arm"))
        end = time.monotonic() + 12
        observed = []
        while time.monotonic() < end:
            observed.extend(supervisor.poll())
            if any(e["kind"] == "wake_error" for e in observed):
                break
            time.sleep(0.02)
        assert any(
            e["kind"] == "wake_error" and e["code"] == "CALIBRATION_REQUIRED" for e in observed
        )
        assert not any(e["kind"] == "wake_listening" for e in observed)
    finally:
        assert supervisor.shutdown()
