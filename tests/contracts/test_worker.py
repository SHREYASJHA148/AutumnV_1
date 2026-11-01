import time

from autumn.controller.contracts import Request
from autumn.controller.worker import Job, Supervisor
from autumn.storage.settings import Settings


def wait_for(supervisor, kind, timeout=12):
    until = time.monotonic() + timeout
    observed = []
    while time.monotonic() < until:
        batch = supervisor.poll()
        observed.extend(batch)
        match = next((message for message in batch if message["kind"] == kind), None)
        if match:
            return match, observed
        time.sleep(0.02)
    raise AssertionError(f"Worker did not produce {kind}")


def test_cancel_generation_and_no_replay(tmp_path):
    supervisor = Supervisor(tmp_path / "worker é")
    try:
        wait_for(supervisor, "ready")
        request = Request(generation=0)
        assert supervisor.submit(Job(kind="simulate", generation=0, request=request))
        supervisor.cancel(1)
        supervisor.submit(Job(kind="diagnostics", generation=1))
        _, observed = wait_for(supervisor, "diagnostics")
        assert not any(m["kind"] == "event" and m["event"]["kind"] == "StepFinished" for m in observed)
        supervisor.submit(Job(kind="simulate", generation=1, request=Request(generation=1)))
        _, events = wait_for(supervisor, "event")
        assert any(m["event"]["generation"] == 1 for m in events if m["kind"] == "event")
    finally:
        assert supervisor.shutdown()


def test_crash_restart_limit_and_no_replay(tmp_path):
    supervisor = Supervisor(tmp_path, allow_faults=True)
    try:
        wait_for(supervisor, "ready")
        for failure in range(3):
            supervisor.submit(Job(kind="crash", generation=failure))
            message, observed = wait_for(supervisor, "worker_failed")
            assert message["disabled"] == (failure == 2)
            assert not any(m["kind"] == "event" for m in observed)
            if failure < 2:
                wait_for(supervisor, "ready")
        assert supervisor.disabled
        assert not supervisor.submit(Job(kind="diagnostics", generation=3))
    finally:
        assert supervisor.shutdown()


def test_hung_worker_is_terminated_without_blocking_poll(tmp_path):
    supervisor = Supervisor(tmp_path, heartbeat_timeout=0.15, allow_faults=True)
    try:
        wait_for(supervisor, "ready")
        # The startup grace has ended for this deliberate fault injection.
        supervisor.started -= 11
        supervisor.submit(Job(kind="hang", generation=0))
        wait_for(supervisor, "worker_failed", timeout=3)
        wait_for(supervisor, "ready")
    finally:
        assert supervisor.shutdown()


def test_unwritable_settings_keep_ui_bootstrap_available(tmp_path):
    # A directory at the file location produces a deterministic write/read failure without permissions changes.
    (tmp_path / "config/settings.json").mkdir(parents=True)
    supervisor = Supervisor(tmp_path)
    try:
        message, _ = wait_for(supervisor, "ready")
        assert message["code"] == "STORAGE_UNAVAILABLE"
        assert not message["settings"]["microphone_enabled_at_start"]
    finally:
        assert supervisor.shutdown()


def test_async_settings_saved_and_restored(tmp_path):
    supervisor = Supervisor(tmp_path)
    try:
        wait_for(supervisor, "ready")
        supervisor.submit(Job(kind="save_settings", generation=0, settings=Settings(history_days=14)))
        message, _ = wait_for(supervisor, "settings_saved")
        assert message["settings"]["history_days"] == 14
    finally:
        assert supervisor.shutdown()
    restored = Supervisor(tmp_path)
    try:
        message, _ = wait_for(restored, "ready")
        assert message["settings"]["history_days"] == 14
        assert not message["settings"]["microphone_enabled_at_start"]
    finally:
        assert restored.shutdown()


def test_cancel_quarantines_a_blocked_worker_within_bounded_time(tmp_path):
    supervisor = Supervisor(tmp_path, allow_faults=True)
    try:
        wait_for(supervisor, "ready")
        supervisor.submit(Job(kind="hang", generation=0))
        supervisor.busy_until = time.monotonic() + 5
        supervisor.cancel(1)
        started = time.monotonic()
        wait_for(supervisor, "worker_failed", timeout=2)
        assert time.monotonic() - started < 1
        wait_for(supervisor, "ready")
    finally:
        assert supervisor.shutdown()


def test_microphone_lease_rejects_old_voice_but_preserves_typed_commands(tmp_path):
    supervisor = Supervisor(tmp_path)
    try:
        wait_for(supervisor, "ready")
        supervisor.cancel_voice()
        assert supervisor.submit(Job(kind="execute", generation=0, request=Request(generation=0, origin="ptt_voice", voice_generation=0), text="help"))
        supervisor.submit(Job(kind="diagnostics", generation=0))
        _, observed = wait_for(supervisor, "diagnostics")
        assert not any(event["kind"] in {"action_result", "action_finished"} for event in observed)
        supervisor.submit(Job(kind="execute", generation=0, request=Request(generation=0), text="help"))
        event, _ = wait_for(supervisor, "action_result")
        assert event["outcome"]["status"] == "succeeded"
    finally:
        assert supervisor.shutdown()


def test_general_mode_bypasses_legacy_phrase_rejection_without_starting_model(tmp_path):
    supervisor = Supervisor(tmp_path)
    try:
        wait_for(supervisor,'ready')
        supervisor.submit(Job(kind='save_settings',generation=0,settings=Settings(master_control=True,model_enabled=False)))
        wait_for(supervisor,'settings_saved')
        supervisor.submit(Job(kind='execute',generation=0,request=Request(generation=0),text='open spotify and then play some music'))
        result,_ = wait_for(supervisor,'action_result')
        assert result['outcome']['code']=='DISABLED'
        assert 'supported command' not in result['outcome']['message']
    finally:
        assert supervisor.shutdown()
