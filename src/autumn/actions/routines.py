"""Only user-authored, non-nested, catalog-referencing actions may be saved."""

import unicodedata
from typing import Annotated

from pydantic import Field, field_validator

from autumn.actions.schemas import Action, Identifier
from autumn.controller.contracts import Contract


class Routine(Contract):
    id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=60)]
    steps: Annotated[tuple[Action, ...], Field(min_length=1, max_length=5)]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if any(unicodedata.category(c).startswith("C") for c in value) or not value.strip():
            raise ValueError("Invalid routine name")
        return " ".join(value.split())

    @field_validator("steps")
    @classmethod
    def catalogued(cls, steps):
        for action in steps:
            if action.skill in {"routine.run", "text.type"}:
                raise ValueError("No nesting or dictation in routines")
            if action.skill == "website.open" and not action.arguments.site_id:
                raise ValueError("Routines use registered websites")
            if action.skill == "folder.open" and not action.arguments.folder_id:
                raise ValueError("Routines use registered folders")
        return steps


class RoutinePlan(Contract):
    steps: Annotated[tuple[Action, ...], Field(min_length=1, max_length=5)]
