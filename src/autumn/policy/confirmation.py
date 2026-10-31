"""Volatile, immutable, expiring, single-use grants. Never persisted or model supplied."""

import hashlib
import json
import time
from dataclasses import dataclass
from uuid import uuid4


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Approval:
    token: str
    request: str
    step: int
    origin: str
    generation: int
    arguments: str
    target: str
    expires: float


class Confirmations:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.pending = None

    def issue(self, request, step, action, target):
        self.pending = Approval(
            uuid4().hex,
            str(request.request_id),
            step,
            request.origin,
            request.generation,
            digest(action.model_dump(mode="json")),
            digest(target),
            self.clock() + 30,
        )
        return self.pending

    def consume(self, token, request, step, action, target):
        approval, self.pending = self.pending, None
        return bool(
            approval
            and token == approval.token
            and self.clock() < approval.expires
            and (
                approval.request,
                approval.step,
                approval.origin,
                approval.generation,
                approval.arguments,
                approval.target,
            )
            == (
                str(request.request_id),
                step,
                request.origin,
                request.generation,
                digest(action.model_dump(mode="json")),
                digest(target),
            )
        )

    def clear(self):
        self.pending = None
