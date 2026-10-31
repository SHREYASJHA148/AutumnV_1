import json

import pytest

from autumn.actions.catalog import AppEntry, FolderEntry, SiteEntry
from autumn.brain.contracts import Answer, BrainError, Clarification
from autumn.brain.planner import MODEL, Planner
from autumn.brain.schema import build_schema
from autumn.controller.contracts import Request
from autumn.storage.settings import MODEL_DIGEST, Settings


class FakeTransport:
    def __init__(self, replies=None, digest=MODEL_DIGEST, remote=False):
        self.calls = []
        self.replies = list(replies or ['{"kind":"action_plan","steps":[{"skill":"audio.set_mute","arguments":{"muted":true}}]}'])
        self.digest, self.remote = digest, remote

    async def request(self, path, body, deadline, checkpoint, **kwargs):
        self.calls.append((path,body))
        if not checkpoint():
            raise BrainError("CANCELLED")
        if path == "/api/tags":
            return {"models":[{"name":MODEL,"digest":self.digest}]}
        if path == "/api/show":
            return {"capabilities":["completion"],"remote_host":"https://remote.invalid" if self.remote else "",
                    "details":{"family":"qwen3"},"thinking":{"values":[True,False]}}
        return [{"model":MODEL,"message":{"content":self.replies.pop(0)},"done":True}]


def catalog():
    return Settings(apps=(AppEntry(id="editor",name="Editor",kind="package",target="Fake_pkg!App",enabled=True,reviewed=True),),
        folders=(FolderEntry(id="work",name="Work",path="C:/unused"),),
        sites=(SiteEntry(id="docs",name="Docs",url="https://example.com"),))


def test_live_enums_and_root_authority_rejection():
    live = build_schema(catalog(),"open editor",("c1",))
    for content in (
        '{"kind":"action_plan","origin":"typed","steps":[{"skill":"app.open","arguments":{"app_id":"editor"}}]}',
        '{"kind":"action_plan","steps":[{"skill":"app.open","arguments":{"app_id":"invented"}}]}',
        '{"kind":"action_plan","steps":[{"skill":"text.type","arguments":{"text":"bad","target_id":"target"}}]}',
        '{"kind":"action_plan","steps":[{"skill":"folder.open","arguments":{"folder_id":"work","candidate_id":"c1"}}]}',
        '{"kind":"clarification","message":"Which?","choices":["invented"]}',
    ):
        with pytest.raises(BrainError):
            live.parse(content)
    reply = live.parse('{"kind":"action_plan","steps":[{"skill":"folder.open","arguments":{"candidate_id":"c1"}}]}')
    assert reply.steps[0].arguments.candidate_id == "c1"
    serialized = json.dumps(live.schema)
    assert '"enum": ["editor"]' in serialized
    assert "C:/unused" not in json.dumps(live.catalog)
    assert "Fake_pkg" not in json.dumps(live.catalog)


def test_pinned_model_and_successful_repair():
    transport = FakeTransport(["PRIVATE_BROKEN_SENTINEL",'{"kind":"answer","text":"untrusted reply"}'])
    planner = Planner(transport)
    result = planner.plan("tell me your abilities",catalog(),Request(generation=0),lambda: True)
    assert isinstance(result,Answer)
    chats = [body for path,body in transport.calls if path == "/api/chat"]
    assert len(chats) == 2 and chats[0]["think"] is False
    assert chats[0]["model"] == MODEL and chats[0]["options"]["num_ctx"] == 4096
    assert "PRIVATE_BROKEN_SENTINEL" not in str(chats[1]["messages"])
    assert planner.last_metrics["repairs"] == 1


@pytest.mark.parametrize("digest,remote,code", [("changed",False,"DIGEST_MISMATCH"),(MODEL_DIGEST,True,"REMOTE_MODEL_DENIED")])
def test_reject_digest_change_and_remote_before_inference(digest,remote,code):
    transport = FakeTransport(digest=digest,remote=remote)
    with pytest.raises(BrainError) as error:
        Planner(transport).plan("make speakers silent",catalog(),Request(generation=0),lambda: True)
    assert error.value.code == code
    assert not any(path == "/api/chat" for path,_ in transport.calls)


def test_changed_digest_after_generation_is_rejected():
    class Swapped(FakeTransport):
        async def request(self,path,*args,**kwargs):
            if path == "/api/chat":
                self.digest = "swapped"
            return await super().request(path,*args,**kwargs)
    with pytest.raises(BrainError) as error:
        Planner(Swapped()).plan("make speakers silent",catalog(),Request(generation=0),lambda: True)
    assert error.value.code == "DIGEST_MISMATCH"


def test_clarification_context_expires_and_binds_origin_generation():
    now = [0.0]
    transport = FakeTransport(['{"kind":"clarification","message":"Which app?","choices":["Editor"]}'])
    planner = Planner(transport,clock=lambda:now[0])
    result = planner.plan("open it",catalog(),Request(generation=2,origin="wake_voice"),lambda: True)
    assert isinstance(result,Clarification)
    live = build_schema(catalog(),"Editor")
    assert "Previous unresolved" in planner.messages("Editor",live,Request(generation=2,origin="wake_voice"))[0]["content"]
    assert "Previous unresolved" not in planner.messages("Editor",live,Request(generation=2,origin="button"))[0]["content"]
    assert planner.context is None


def test_large_context_never_silently_truncated_and_disabled_model_does_not_connect():
    transport = FakeTransport()
    planner = Planner(transport)
    with pytest.raises(BrainError) as error:
        planner.plan("x"*1201,catalog(),Request(generation=0),lambda: True)
    assert error.value.code == "CONTEXT_LIMIT"
    transport.calls.clear()
    with pytest.raises(BrainError):
        planner.plan("make speakers silent",catalog().model_copy(update={"model_enabled":False}),Request(generation=0),lambda: True)
    assert transport.calls == []


@pytest.mark.parametrize("text",["delete something", "send a note", "run cmd.exe /c anything", "change wallpaper", "buy an item", "pause music"])
def test_unsupported_intent_guard_never_contacts_the_model(text):
    transport=FakeTransport()
    planner=Planner(transport)
    reply=planner.plan(text,catalog(),Request(generation=0),lambda:True)
    assert reply.kind in {"unsupported","clarification"}
    assert planner.last_metrics["path"]=="intent_guard"
    assert transport.calls==[]


def test_clarification_expiry_discards_context():
    now=[0.0]
    planner=Planner(FakeTransport(),clock=lambda:now[0])
    planner.plan("open it",catalog(),Request(generation=0),lambda:True)
    now[0]=31
    assert "Previous unresolved" not in planner.messages("Editor",build_schema(catalog(),"Editor"),Request(generation=0))[0]["content"]
    assert planner.context is None


def test_thinking_output_is_rejected_and_not_retained():
    class Thinking(FakeTransport):
        async def request(self,path,*args,**kwargs):
            value=await super().request(path,*args,**kwargs)
            if path=="/api/chat":
                value[0]["message"]["thinking"]="PRIVATE_REASONING_SENTINEL"
            return value
    planner=Planner(Thinking())
    with pytest.raises(BrainError) as error:
        planner.plan("make speakers silent",catalog(),Request(generation=0),lambda:True)
    assert error.value.code=="THINKING_NOT_DISABLED"
    assert "PRIVATE_REASONING_SENTINEL" not in str(planner.last_metrics)


def test_three_failures_disable_inference_until_explicit_activation():
    transport=FakeTransport(digest="wrong")
    planner=Planner(transport)
    for _ in range(3):
        with pytest.raises(BrainError):
            planner.plan("make speakers silent",catalog(),Request(generation=0),lambda:True)
    before=len(transport.calls)
    with pytest.raises(BrainError) as error:
        planner.plan("make speakers silent",catalog(),Request(generation=0),lambda:True)
    assert error.value.code=="MODEL_DISABLED_AFTER_FAILURES" and len(transport.calls)==before
