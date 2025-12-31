from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import uuid4
import time


@dataclass(frozen=True)
class Event:
    id: str
    ts: float
    type: str
    action: str
    payload: dict[str, Any]

    @classmethod
    def create(cls, event_type: str, action: str, payload: Mapping[str, Any]) -> "Event":
        return cls(
            id=str(uuid4()),
            ts=time.time(),
            type=event_type,
            action=action,
            payload=dict(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "type": self.type,
            "action": self.action,
            "payload": dict(self.payload),
        }
