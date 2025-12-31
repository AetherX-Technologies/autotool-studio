from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import uuid4


class ActionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Action:
    id: str
    type: str
    params: dict[str, Any]
    timeout: float | None = None
    retry: int = 0

    @classmethod
    def create(
        cls,
        action_type: str,
        params: Mapping[str, Any],
        *,
        timeout: float | None = None,
        retry: int = 0,
        action_id: str | None = None,
    ) -> "Action":
        return cls(
            id=action_id or str(uuid4()),
            type=action_type,
            params=dict(params),
            timeout=timeout,
            retry=retry,
        )

    @classmethod
    def from_obj(cls, value: "Action | Mapping[str, Any]") -> "Action":
        if isinstance(value, Action):
            return value
        if not isinstance(value, Mapping):
            raise ActionError("Action must be a dict-like object")
        action_type = value.get("type")
        if not action_type:
            raise ActionError("Action type is required")
        params = value.get("params", {})
        timeout = value.get("timeout")
        retry = int(value.get("retry", 0))
        action_id = value.get("id") or str(uuid4())
        return cls(
            id=action_id,
            type=str(action_type),
            params=dict(params),
            timeout=timeout,
            retry=retry,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "params": dict(self.params),
            "timeout": self.timeout,
            "retry": self.retry,
        }


@dataclass(frozen=True)
class ExecutionResult:
    action_id: str
    success: bool
    message: str = ""
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "success": self.success,
            "message": self.message,
            "data": dict(self.data) if self.data is not None else None,
        }
