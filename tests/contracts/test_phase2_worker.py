import time

from autumn.actions.catalog import FolderEntry
from autumn.controller.contracts import Request
from autumn.controller.worker import Job, Supervisor
from autumn.storage.settings import Settings


def collect_until(supervisor, kind, timeout=12):
    until = time.monotonic() + timeout
    observed = []
    while time.monotonic() < until:
        batch = supervisor.poll()
        observed.extend(batch)
        if any(message["kind"] == kind for message in batch):
            return observed
        time.sleep(0.02)
    raise AssertionError("Required worker response missing")


def test_real_worker_routes_help_search_and_rejects_stale_request(tmp_path):
    root = tmp_path / "runtime é"
    files = tmp_path / "disposable files"
    files.mkdir()
    (files / "budget.xlsx").write_text("Fixed disposable fixture")
    supervisor = Supervisor(root)
    try:
        collect_until(supervisor, "ready")
        supervisor.submit(Job(kind="save_settings", generation=0, settings=Settings(
            folders=(FolderEntry(id="fixtures", name="Fixtures", path=str(files)),))))
        collect_until(supervisor, "settings_saved")
        for text, expected in (("help", "OK"), ("find spreadsheet budget in fixtures", "OK"), ("unsupported fixed privacy marker", "CLARIFICATION")):
            request = Request(generation=0)
            supervisor.submit(Job(kind="execute", generation=0, request=request, text=text))
            observed = collect_until(supervisor, "action_result")
            outcome = next(m["outcome"] for m in observed if m["kind"] == "action_result")
            assert outcome["code"] == expected
            if text.startswith("find"):
                assert len(outcome["matches"]) == 1
            # Drain a command ordered after execution, without relying on event batching.
            supervisor.submit(Job(kind="history", generation=0))
            collect_until(supervisor, "history")
        supervisor.cancel(1)
        supervisor.submit(Job(kind="execute", generation=0, request=Request(generation=0), text="help"))
        supervisor.submit(Job(kind="diagnostics", generation=1))
        observed = collect_until(supervisor, "diagnostics")
        assert not any(m["kind"] == "action_result" for m in observed)
    finally:
        assert supervisor.shutdown()
    raw = (root / "data/jarvis.db").read_bytes()
    assert b"unsupported fixed privacy marker" not in raw
    assert str(files).encode() not in raw
