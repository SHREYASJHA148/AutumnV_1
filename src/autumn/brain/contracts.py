"""Planner replies carry intentions only; action authority stays outside this union."""
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from autumn.actions.schemas import Plan
from autumn.controller.contracts import Contract


class Clarification(Contract):
    kind: Literal["clarification"] = "clarification"
    message: str = Field(min_length=1, max_length=180)
    choices: tuple[Annotated[str, Field(min_length=1, max_length=80)], ...] = Field(default=(), max_length=5)


class Unsupported(Contract):
    kind: Literal["unsupported"] = "unsupported"
    message: str = Field(min_length=1, max_length=180)


class Answer(Contract):
    kind: Literal["answer"] = "answer"
    text: str = Field(min_length=1, max_length=300)


Reply = Annotated[Plan | Clarification | Unsupported | Answer, Field(discriminator="kind")]
REPLY = TypeAdapter(Reply)


class BrainError(Exception):
    """Only a fixed error code may be rendered or persisted, never transport/model text."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
