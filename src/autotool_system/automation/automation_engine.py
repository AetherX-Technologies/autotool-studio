from __future__ import annotations

from typing import Any, Iterable, Mapping
import time

from .action import Action, ActionError, ExecutionResult
from ..utils.logger import get_logger

try:
    import pyautogui
except Exception as exc:  # pragma: no cover - import-time guard
    pyautogui = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


_ALLOWED_ACTIONS = {
    "click",
    "move",
    "type",
    "hotkey",
    "wait",
    "screenshot",
    "key_down",
    "key_up",
    "mouse_down",
    "mouse_up",
    "scroll",
}


def _get_backend() -> Any:
    if pyautogui is None:
        raise RuntimeError(f"pyautogui is not available: {_IMPORT_ERROR}")
    return pyautogui


def _scale(value: float, speed: float) -> float:
    if speed <= 0:
        raise ActionError("Speed must be greater than 0")
    return value / speed


class AutomationEngine:
    def __init__(
        self,
        backend: Any | None = None,
        *,
        failsafe: bool = True,
        pause: float = 0.1,
    ) -> None:
        self._backend = backend or _get_backend()
        self._logger = get_logger("autotool.automation")
        self._audit = get_logger("autotool.audit")
        if hasattr(self._backend, "FAILSAFE"):
            self._backend.FAILSAFE = failsafe
        if hasattr(self._backend, "PAUSE"):
            self._backend.PAUSE = pause
        self._paused = False
        self._stopped = False

    def execute(self, action: Action | Mapping[str, Any], *, speed: float = 1.0) -> ExecutionResult:
        try:
            action_obj = Action.from_obj(action)
        except ActionError as exc:
            action_id = None
            if isinstance(action, Mapping):
                action_id = action.get("id")
            return ExecutionResult(
                action_id=action_id or "unknown",
                success=False,
                message=str(exc),
            )
        if action_obj.type not in _ALLOWED_ACTIONS:
            self._logger.warning("Unsupported action type: %s", action_obj.type)
            return ExecutionResult(
                action_id=action_obj.id,
                success=False,
                message=f"Unsupported action type: {action_obj.type}",
            )
        if self._stopped:
            self._logger.warning("Execution stopped before action %s", action_obj.id)
            return ExecutionResult(action_id=action_obj.id, success=False, message="Execution stopped")
        try:
            self._audit.info("action_start id=%s type=%s", action_obj.id, action_obj.type)
            result = self._execute_action(action_obj, speed=speed)
            self._audit.info("action_end id=%s success=%s", action_obj.id, result.success)
            return result
        except Exception as exc:
            failsafe_exc = getattr(self._backend, "FailSafeException", None)
            if failsafe_exc is not None and isinstance(exc, failsafe_exc):
                self._logger.warning("Failsafe triggered for action %s", action_obj.id)
                return ExecutionResult(
                    action_id=action_obj.id,
                    success=False,
                    message="Failsafe triggered",
                    data={"error": exc.__class__.__name__},
                )
            self._logger.error("Action %s failed: %s", action_obj.id, exc)
            return ExecutionResult(
                action_id=action_obj.id,
                success=False,
                message=str(exc),
                data={"error": exc.__class__.__name__},
            )

    def execute_sequence(
        self, actions: Iterable[Action | Mapping[str, Any]], *, speed: float = 1.0
    ) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []
        self._stopped = False
        for action in actions:
            while self._paused and not self._stopped:
                time.sleep(0.05)
            if self._stopped:
                break
            results.append(self.execute(action, speed=speed))
        return results

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stopped = True
        self._paused = False
        self._logger.warning("Automation engine stopped")

    def _execute_action(self, action: Action, *, speed: float) -> ExecutionResult:
        params = dict(action.params)
        action_type = action.type

        if action_type == "click":
            x = params.get("x")
            y = params.get("y")
            button = params.get("button", "left")
            clicks = int(params.get("clicks", 1))
            interval = float(params.get("interval", 0.0))
            kwargs: dict[str, Any] = {
                "clicks": clicks,
                "interval": _scale(interval, speed),
                "button": button,
            }
            if x is not None and y is not None:
                kwargs["x"] = x
                kwargs["y"] = y
            self._backend.click(**kwargs)
            return ExecutionResult(action_id=action.id, success=True, data={"x": x, "y": y})

        if action_type == "move":
            x = params.get("x")
            y = params.get("y")
            if x is None or y is None:
                raise ActionError("Move action requires x and y")
            duration = float(params.get("duration", 0.0))
            self._backend.moveTo(x, y, duration=_scale(duration, speed))
            return ExecutionResult(action_id=action.id, success=True, data={"x": x, "y": y})

        if action_type == "type":
            text = params.get("text")
            if text is None:
                raise ActionError("Type action requires text")
            interval = float(params.get("interval", 0.0))
            writer = getattr(self._backend, "write", None) or getattr(self._backend, "typewrite")
            writer(str(text), interval=_scale(interval, speed))
            return ExecutionResult(action_id=action.id, success=True)

        if action_type == "hotkey":
            keys = params.get("keys")
            combo = params.get("combo")
            if keys is None and combo is None:
                raise ActionError("Hotkey action requires keys or combo")
            if combo is not None:
                keys = [item.strip() for item in str(combo).split("+") if item.strip()]
            if isinstance(keys, str):
                keys = [item.strip() for item in keys.split("+") if item.strip()]
            self._backend.hotkey(*list(keys))
            return ExecutionResult(action_id=action.id, success=True)

        if action_type == "wait":
            seconds = float(params.get("seconds", 0.0))
            time.sleep(_scale(seconds, speed))
            return ExecutionResult(action_id=action.id, success=True, data={"seconds": seconds})

        if action_type == "screenshot":
            region = params.get("region")
            path = params.get("path")
            if path:
                image = self._backend.screenshot(path, region=region)
            else:
                image = self._backend.screenshot(region=region)
            data: dict[str, Any] = {"region": region, "path": path}
            if path is None:
                data["size"] = getattr(image, "size", None)
            return ExecutionResult(action_id=action.id, success=True, data=data)

        if action_type == "key_down":
            key = params.get("key")
            if not key:
                raise ActionError("Key down action requires key")
            self._backend.keyDown(str(key))
            return ExecutionResult(action_id=action.id, success=True)

        if action_type == "key_up":
            key = params.get("key")
            if not key:
                raise ActionError("Key up action requires key")
            self._backend.keyUp(str(key))
            return ExecutionResult(action_id=action.id, success=True)

        if action_type == "mouse_down":
            x = params.get("x")
            y = params.get("y")
            button = params.get("button", "left")
            kwargs: dict[str, Any] = {"button": button}
            if x is not None and y is not None:
                kwargs["x"] = x
                kwargs["y"] = y
            self._backend.mouseDown(**kwargs)
            return ExecutionResult(action_id=action.id, success=True)

        if action_type == "mouse_up":
            x = params.get("x")
            y = params.get("y")
            button = params.get("button", "left")
            kwargs: dict[str, Any] = {"button": button}
            if x is not None and y is not None:
                kwargs["x"] = x
                kwargs["y"] = y
            self._backend.mouseUp(**kwargs)
            return ExecutionResult(action_id=action.id, success=True)

        if action_type == "scroll":
            x = params.get("x")
            y = params.get("y")
            dx = int(params.get("dx", 0))
            dy = int(params.get("dy", 0))
            if dy != 0:
                self._backend.scroll(dy, x=x, y=y)
            if dx != 0 and hasattr(self._backend, "hscroll"):
                self._backend.hscroll(dx, x=x, y=y)
            return ExecutionResult(
                action_id=action.id,
                success=True,
                data={"x": x, "y": y, "dx": dx, "dy": dy},
            )

        raise ActionError(f"Unsupported action type: {action_type}")
