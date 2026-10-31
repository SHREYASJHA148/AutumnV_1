import pytest
from pydantic import ValidationError

from autumn.controller.contracts import CaptureState as C
from autumn.controller.contracts import Event, Request
from autumn.controller.contracts import TaskState as T
from autumn.controller.state import CAPTURE_EDGES, TASK_EDGES, Session


def test_first_launch_and_bounded_queue():
    state = Session()
    assert (state.capture, state.task) == (C.DISABLED, T.IDLE)
    assert all(state.enqueue() for _ in range(6))
    assert state.enqueue() is None
    assert len(state.pending) == 5


def test_stop_cancels_all_and_rejects_late_events():
    state = Session()
    request = state.enqueue()
    state.enqueue()
    stale = Event(kind="StepFinished", request_id=request.request_id, generation=0, code="SIMULATED")
    assert state.accepts(stale)
    assert len(state.stop()) == 2
    state.enqueue()
    assert not state.accepts(stale)
    assert state.generation == 1


@pytest.mark.parametrize("capture,after", [(C.DISABLED,C.DISABLED),(C.PTT_READY,C.PTT_READY),(C.RECORDING,C.PTT_READY),(C.ARMED_WAKE,C.DISABLED)])
def test_stop_capture_policy(capture, after):
    state = Session()
    state.capture = capture
    state.stop()
    assert state.capture == after


def test_suspend_blocks_dispatch_and_resume_requires_explicit_voice():
    state = Session()
    state.set_capture(C.PTT_READY)
    state.enqueue()
    state.suspend()
    assert state.capture == C.DISABLED
    assert state.enqueue() is None
    state.resume()
    assert state.capture == C.DISABLED and state.enqueue() is not None


@pytest.mark.parametrize("before", list(C))
@pytest.mark.parametrize("after", list(C))
def test_capture_transition_matrix(before, after):
    state = Session()
    state.capture = before
    if before == after or after in CAPTURE_EDGES[before]:
        state.set_capture(after)
        assert state.capture == after
    else:
        with pytest.raises(ValueError):
            state.set_capture(after)


@pytest.mark.parametrize("before", list(T))
@pytest.mark.parametrize("after", list(T))
def test_task_transition_matrix(before, after):
    state = Session()
    state.task = before
    if before == after or after == T.CANCELLING or after in TASK_EDGES[before]:
        state.set_task(after)
        assert state.task == after
    else:
        with pytest.raises(ValueError):
            state.set_task(after)


def test_request_cannot_take_execution_authority():
    with pytest.raises(ValidationError):
        Request(generation=0, permission="allow", target="anything")
