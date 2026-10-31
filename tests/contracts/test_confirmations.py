from test_worker import wait_for

from autumn.actions.schemas import OpenWebsite, Plan
from autumn.controller.contracts import Request
from autumn.controller.worker import Job, Supervisor


def test_worker_cancel_and_restart_forget_confirmation_without_opening_browser(tmp_path):
    worker=Supervisor(tmp_path)
    try:
        wait_for(worker,"ready")
        plan=Plan(steps=(OpenWebsite(arguments={"url":"https://example.com/autumn-disposable"}),))
        worker.submit(Job(kind="execute",generation=0,request=Request(generation=0,origin="ptt_voice"),plan=plan))
        approval,_=wait_for(worker,"confirmation")
        # Explicit rejection can never dispatch the URL or start a browser.
        worker.submit(Job(kind="confirm",generation=0,confirmation_id=approval["token"],approved=False))
        outcome,_=wait_for(worker,"action_result")
        assert outcome["outcome"]["code"]=="DENIED"
        worker.submit(Job(kind="execute",generation=0,request=Request(generation=0,origin="ptt_voice"),plan=plan))
        approval,_=wait_for(worker,"confirmation")
        worker.process.terminate()
        wait_for(worker,"worker_failed")
        wait_for(worker,"ready")
        worker.submit(Job(kind="confirm",generation=0,confirmation_id=approval["token"],approved=True))
        worker.submit(Job(kind="diagnostics",generation=0))
        _,events=wait_for(worker,"diagnostics")
        assert not any(e["kind"] in {"action_result","action_finished","confirmation"} for e in events)
    finally:
        assert worker.shutdown()
