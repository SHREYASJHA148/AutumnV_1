import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from autumn.actions.engine import Engine
from autumn.actions.registry import REGISTRY
from autumn.actions.schemas import OpenWebsite, Plan, WebsiteArgs, parse_plan
from autumn.controller.contracts import Request
from autumn.policy.matrix import decide
from autumn.storage.settings import Settings


@pytest.mark.parametrize("skill", list(REGISTRY))
@pytest.mark.parametrize("origin", ["typed", "button", "ptt_voice", "wake_voice", "routine"])
@pytest.mark.parametrize("registered", [True, False])
def test_entire_policy_matrix(skill, origin, registered):
    result = decide(skill, origin, registered_site=registered)
    if not REGISTRY[skill].available or origin == "routine":
        assert result.outcome == "deny"
    elif skill == "text.type":
        assert result.outcome == ("deny" if origin == "wake_voice" else "confirm")
    elif skill == "website.open" and not registered and origin in {"ptt_voice", "wake_voice"}:
        assert result.outcome == ("deny" if origin == "wake_voice" else "confirm")
    else:
        assert result.outcome == "allow"


@given(st.sampled_from(["origin", "permission", "target", "path", "confirmation", "cancel_generation", "shell"]), st.text(max_size=80))
def test_model_cannot_inject_authority(field, value):
    plan = {"kind":"action_plan", "steps":[{"skill":"help.capabilities", "arguments":{}}], field:value}
    with pytest.raises(ValidationError):
        parse_plan(json.dumps(plan))


@given(st.sampled_from(list(REGISTRY)), st.sampled_from(["typed", "button", "ptt_voice", "wake_voice"]))
def test_routine_never_adds_authority(skill, origin):
    assert decide(skill, "routine", inherited_origin=origin) == decide(skill, origin)


@settings(max_examples=30)
@given(st.sampled_from(["wake_voice", "ptt_voice", "routine"]), st.sampled_from(["example.com", "example.org", "localhost"]))
def test_no_adapter_call_without_allow_policy(origin, host):
    class Forbidden:
        def perform(self, *args):
            raise AssertionError("Unauthorized adapter dispatch")

    plan = Plan(steps=(OpenWebsite(arguments=WebsiteArgs(url=f"https://{host}/")),))
    results = Engine(Forbidden(), Settings()).execute(plan, Request(generation=0, origin=origin), lambda: True, lambda *_: None)
    assert results[0].code == "DENIED"
