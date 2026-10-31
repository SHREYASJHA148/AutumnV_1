import json

import pytest
from pydantic import ValidationError

from autumn.actions.catalog import AppEntry, FolderEntry, SiteEntry, fingerprint, safe_url
from autumn.actions.engine import Engine, Outcome
from autumn.actions.router import route
from autumn.actions.schemas import (
    AppArgs,
    Capabilities,
    OpenApp,
    Plan,
    SetVolume,
    VolumeArgs,
    parse_plan,
)
from autumn.controller.contracts import Request
from autumn.storage.settings import Settings


class FakeAdapter:
    def __init__(self):
        self.calls = []
        self.result = Outcome(status="succeeded", code="OK", message="Fixed test result.", verification="fake")

    def perform(self, resolved, permit, checkpoint):
        assert permit.outcome == "allow" and checkpoint()
        self.calls.append(resolved)
        return self.result


@pytest.fixture
def settings(tmp_path):
    executable = tmp_path / "Disposable App é.exe"
    executable.write_bytes(b"test data; never executed")
    return Settings(apps=(AppEntry(id="editor", name="Fixture Editor", aliases=("editor",),
        kind="executable", target=str(executable), fingerprint=fingerprint(executable), reviewed=True, enabled=True),),
        folders=(FolderEntry(id="fixtures", name="Fixtures", path=str(tmp_path)),),
        sites=(SiteEntry(id="example", name="Example", url="https://example.com"),))


@pytest.mark.parametrize("text,skill", [("open editor","app.open"),("open fixtures","folder.open"),
    ("open example","website.open"),("set volume to 35 percent","audio.set_volume"),
    ("unmute","audio.set_mute"),("next track","media.control"),("take a screenshot","screen.capture"),
    ("find spreadsheet budget in fixtures","files.search"),("what can you do?","help.capabilities")])
def test_supported_exact_grammar(settings, text, skill):
    assert route(text, settings).plan.steps[0].skill == skill


@pytest.mark.parametrize("text", ["don't open editor", "open editor and delete everything", "open editor now",
    "open editor & calc", "set volume to 20 then mute", "volume 101", "find C:\\private", "open unknown", "open edtor"])
def test_unknown_trailing_negation_and_fuzzy_never_dispatch(settings, text):
    assert route(text, settings).plan is None


@pytest.mark.parametrize("url", ["file:///C:/test.exe", "javascript:alert(1)", "https://a.com/`calc`", "https://a.com/%0a",
    "https://user:password@example.com", "https://a.com\\evil", "https://a.com:99999", "https://a.com/$(cmd)"])
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        safe_url(url)


def test_schema_cannot_take_authority_or_path():
    with pytest.raises(ValidationError):
        parse_plan(json.dumps({"kind":"action_plan", "origin":"typed", "steps":[]}))
    with pytest.raises(ValidationError):
        parse_plan(json.dumps({"kind":"action_plan", "steps":[{"skill":"app.open", "arguments":{"app_id":"editor", "path":"cmd.exe"}}]}))
    with pytest.raises(ValidationError):
        VolumeArgs(percent=True)
    with pytest.raises(ValidationError):
        Plan(steps=(Capabilities(),)*4)


def test_engine_resolves_before_dispatch_and_honors_cancel(settings):
    adapter = FakeAdapter()
    engine = Engine(adapter, settings)
    request = Request(generation=0)
    records = []
    plan = Plan(steps=(OpenApp(arguments=AppArgs(app_id="editor")), SetVolume(arguments=VolumeArgs(percent=30))))

    def step(record, result):
        records.append(record)

    results = engine.execute(plan, request, lambda: len(records) == 0, step)
    assert len(results) == len(adapter.calls) == len(records) == 1
    assert records[0].request_id == request.request_id
    assert "Disposable" not in records[0].model_dump_json()


def test_disabled_missing_changed_target_fail_before_adapter(settings):
    adapter = FakeAdapter()
    engine = Engine(adapter, settings)
    for identifier in ("unknown", "editor"):
        if identifier == "editor":
            from pathlib import Path
            Path(settings.apps[0].target).write_bytes(b"changed")
        results = engine.execute(Plan(steps=(OpenApp(arguments=AppArgs(app_id=identifier)),)), Request(generation=0), lambda: True, lambda *_: None)
        assert results[0].status == "failed"
    assert adapter.calls == []


def test_access_denial_is_reported(settings):
    class Denied(FakeAdapter):
        def perform(self, *args):
            raise PermissionError()

    results = Engine(Denied(), settings).execute(Plan(steps=(SetVolume(arguments=VolumeArgs(percent=10)),)),
        Request(generation=0), lambda: True, lambda *_: None)
    assert results[0].code == "ACCESS_DENIED"
