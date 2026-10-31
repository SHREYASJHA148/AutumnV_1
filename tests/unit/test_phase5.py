from types import SimpleNamespace

import pytest

from autumn.actions.engine import Engine, Outcome
from autumn.actions.routines import Routine
from autumn.actions.schemas import Capabilities, Plan, RunRoutine, TextArgs, TypeText
from autumn.controller.contracts import Request
from autumn.policy.confirmation import Confirmations
from autumn.storage.settings import Settings
from autumn.winworker.dictation import Dictation


@pytest.mark.parametrize(
    "change", ["expiry", "text", "target", "origin", "request", "generation", "token", "reuse"]
)
def test_approval_binds_every_authority_field_and_is_single_use(change):
    clock = [0]
    store = Confirmations(lambda: clock[0])
    request = Request(generation=0)
    action = TypeText(arguments={"text": "Public test", "target_id": "target"})
    target = {"pid": 123, "control": 45}
    approval = store.issue(request, 1, action, target)
    token = approval.token
    if change == "expiry":
        clock[0] = 30
    elif change == "text":
        action = TypeText(arguments={"text": "Changed", "target_id": "target"})
    elif change == "target":
        target = {"pid": 123, "control": 46}
    elif change == "origin":
        request = request.model_copy(update={"origin": "wake_voice"})
    elif change == "request":
        request = Request(generation=0)
    elif change == "generation":
        request = request.model_copy(update={"generation": 1})
    elif change == "token":
        token = "wrong"
    elif change == "reuse":
        assert store.consume(token, request, 1, action, target)
    assert not store.consume(token, request, 1, action, target)


@pytest.mark.parametrize("bad", ["\n", "\r", "\t", "\x00", "\x85", "\u2028", "\u2029", "\u200e"])
def test_dictation_never_allows_controls_or_line_breaks(bad):
    with pytest.raises(ValueError):
        TextArgs(text="x" + bad + "y", target_id="target")


def test_routines_are_bounded_no_nesting_or_dictation_or_unregistered_urls():
    for steps in (
        (),
        (Capabilities(),) * 6,
        (TypeText(arguments={"text": "x", "target_id": "target"}),),
        (RunRoutine(arguments={"routine_id": "nested"}),),
    ):
        with pytest.raises(ValueError):
            Routine(id="r", name="Demo", steps=steps)


def test_routine_runs_serially_inherits_origin_and_halts_on_first_failure():
    from autumn.actions.schemas import SetMute

    routine = Routine(id="r", name="Demo", steps=(SetMute(arguments={"muted": True}),) * 5)

    class Adapter:
        def __init__(self):
            self.calls = 0

        def perform(self, resolved, permit, checkpoint):
            self.calls += 1
            return Outcome(
                status="failed" if self.calls == 3 else "succeeded",
                code="COMPONENT_UNAVAILABLE" if self.calls == 3 else "OK",
                message="Fixed",
                verification="fake",
            )

    adapter = Adapter()
    engine = Engine(adapter, Settings(routines=(routine,)))
    records = []
    results = engine.execute(
        Plan(steps=(RunRoutine(arguments={"routine_id": "r"}),)),
        Request(generation=0, origin="wake_voice"),
        lambda: True,
        lambda record, result: records.append(record),
    )
    assert adapter.calls == 3 and len(results) == 3
    assert [r.step_id for r in records] == [1, 2, 3] and all(
        r.origin == "wake_voice" for r in records
    )


def test_dictation_focus_change_or_cancellation_halts_without_retry(monkeypatch):
    import win32api

    monkeypatch.setattr(win32api, "GetAsyncKeyState", lambda key: 0)
    target = SimpleNamespace()
    adapter = Dictation()
    sent = []
    adapter.current = lambda target, focused=False: len(sent) < 2
    adapter.send_character = lambda char: sent.append(char) or True
    result = adapter.type_text(target, "Public sample", lambda: True)
    assert result.status == "partial" and len(sent) == 2
    sent.clear()
    result = adapter.type_text(target, "Public sample", lambda: False)
    assert result.status == "cancelled" and not sent


def test_engine_requires_confirmation_and_rechecks_after_approval():
    class Adapter:
        dictation = SimpleNamespace(resolve=lambda token: "snapshot")

        def perform(self, *args):
            raise AssertionError("No typing without an approval")

    engine = Engine(Adapter(), Settings())
    results = engine.execute(
        Plan(steps=(TypeText(arguments={"text": "Public", "target_id": "target"}),)),
        Request(generation=0),
        lambda: True,
        lambda *args: None,
    )
    assert results[0].code == "DENIED"


def test_unicode_events_contain_only_packet_characters_and_keyup():
    native = Dictation()
    captured = []

    def send(count, events, size):
        captured.extend(
            [
                (
                    events[i].type,
                    events[i].keyboard.vk,
                    events[i].keyboard.scan,
                    events[i].keyboard.flags,
                )
                for i in range(count)
            ]
        )
        return count

    native.user = SimpleNamespace(SendInput=send)
    assert native.send_character("🙂")
    assert len(captured) == 4
    assert all(
        kind == 1 and vk == 0 and flags in {4, 6} and unit not in {9, 10, 13}
        for kind, vk, unit, flags in captured
    )
    assert [row[3] for row in captured] == [4, 6, 4, 6]
