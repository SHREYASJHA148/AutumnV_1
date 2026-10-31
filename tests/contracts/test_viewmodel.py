from PySide6.QtCore import QCoreApplication

from autumn.controller.contracts import Event
from autumn.ui.viewmodel import ViewModel


class FakeSupervisor:
    def __init__(self):
        self.jobs = []
        self.messages = []
        self.generation = 0

    def submit(self, job):
        self.jobs.append(job)
        return True

    def poll(self):
        messages, self.messages = self.messages, []
        return messages

    def cancel(self, generation):
        self.generation = generation

    def shutdown(self):
        return True


def test_stale_reply_does_not_complete_new_request_or_write_success():
    app = QCoreApplication.instance() or QCoreApplication([])
    assert app
    supervisor = FakeSupervisor()
    vm = ViewModel(supervisor)
    vm.ready = True
    try:
        vm.submit("Fixed test input")
        old = vm.session.active
        vm.stop()
        vm.submit("Another fixed input")
        current = vm.session.active
        supervisor.messages = [{"kind": "event", "event": Event(kind="StepFinished", generation=old.generation,
            request_id=old.request_id, code="SIMULATED").model_dump(mode="json")}]
        vm.poll()
        assert vm.session.active == current
        assert not any(job.records and job.records[0].code == "SIMULATED" for job in supervisor.jobs)
        # Phase 2 routing needs transient input in IPC; persistence jobs must remain redacted.
        assert all("Fixed" not in job.model_dump_json() and "Another" not in job.model_dump_json()
                   for job in supervisor.jobs if job.kind in {"record", "save_settings"})
    finally:
        vm.shutdown()
