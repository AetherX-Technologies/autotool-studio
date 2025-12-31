from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import json
import time

import yaml

from ..automation import Action, AutomationEngine, ExecutionResult
from ..utils.logger import get_logger

StateCallback = Callable[[str], None]
ResultCallback = Callable[[ExecutionResult], None]


class ReplayerError(RuntimeError):
    pass


class Replayer:
    def __init__(
        self,
        engine: AutomationEngine | None = None,
        *,
        on_state_change: StateCallback | None = None,
        on_result: ResultCallback | None = None,
    ) -> None:
        self._engine = engine or AutomationEngine()
        self._on_state_change = on_state_change
        self._on_result = on_result
        self._state = "idle"
        self._paused = False
        self._stopped = False
        self._items: list[Mapping[str, Any]] | None = None
        self._logger = get_logger("autotool.replayer")

    @property
    def state(self) -> str:
        return self._state

    def load(self, path: str | Path) -> list[Mapping[str, Any]]:
        target = Path(path)
        if not target.exists():
            raise ReplayerError(f"Replay file not found: {target}")
        content = target.read_text(encoding="utf-8")
        if target.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        if isinstance(data, dict) and "events" in data:
            items = data["events"]
        else:
            items = data
        if not isinstance(items, list):
            raise ReplayerError("Replay file must contain a list of events/actions")
        self._items = items
        self._logger.info("Replay file loaded: %s (%s items)", target, len(items))
        return items

    def play(
        self,
        items: Iterable[Action | Mapping[str, Any]] | None = None,
        *,
        speed: float = 1.0,
        stop_on_error: bool = False,
    ) -> list[ExecutionResult]:
        if speed <= 0:
            raise ReplayerError("Speed must be greater than 0")
        if items is None:
            if self._items is None:
                raise ReplayerError("No replay items loaded")
            items_to_play = list(self._items)
        else:
            items_to_play = list(items)

        self._stopped = False
        self._paused = False
        self._set_state("running")
        results: list[ExecutionResult] = []
        self._logger.info("Replay started (%s items)", len(items_to_play))

        for item in items_to_play:
            while self._paused and not self._stopped:
                time.sleep(0.05)
            if self._stopped:
                break

            result = self._execute_item(item, speed=speed)
            results.append(result)
            if self._on_result is not None:
                self._on_result(result)
            if stop_on_error and not result.success:
                self._stopped = True
                break

        self._set_state("stopped" if self._stopped else "idle")
        self._logger.info("Replay finished (%s results)", len(results))
        return results

    def pause(self) -> None:
        if self._state == "running":
            self._paused = True
            self._set_state("paused")
            self._logger.info("Replay paused")

    def resume(self) -> None:
        if self._state == "paused":
            self._paused = False
            self._set_state("running")
            self._logger.info("Replay resumed")

    def stop(self) -> None:
        self._stopped = True
        self._paused = False
        self._set_state("stopped")
        self._logger.warning("Replay stopped")

    def _set_state(self, state: str) -> None:
        self._state = state
        if self._on_state_change is not None:
            self._on_state_change(state)

    def _execute_item(self, item: Action | Mapping[str, Any], *, speed: float) -> ExecutionResult:
        if isinstance(item, Action):
            return self._engine.execute(item, speed=speed)

        if not isinstance(item, Mapping):
            return ExecutionResult(action_id="unknown", success=False, message="Invalid replay item")

        if "params" in item or "type" in item and item.get("type") in _ACTION_TYPES:
            if "delta" in item:
                self._sleep_delta(item, speed)
            return self._engine.execute(item, speed=speed)

        if "type" in item and "action" in item:
            self._sleep_delta(item, speed)
            action = self._event_to_action(item)
            if action is None:
                return ExecutionResult(action_id=str(item.get("id", "unknown")), success=False, message="Unsupported event")
            return self._engine.execute(action, speed=speed)

        return ExecutionResult(action_id=str(item.get("id", "unknown")), success=False, message="Unknown replay item")

    def _sleep_delta(self, item: Mapping[str, Any], speed: float) -> None:
        delta = float(item.get("delta", 0.0))
        if delta > 0:
            time.sleep(delta / speed)

    def _event_to_action(self, item: Mapping[str, Any]) -> Action | None:
        event_type = item.get("type")
        action = item.get("action")
        payload = item.get("payload", {})
        action_id = item.get("id")

        if event_type == "mouse":
            if action == "move":
                return Action.create("move", {"x": payload.get("x"), "y": payload.get("y")}, action_id=action_id)
            if action == "scroll":
                return Action.create(
                    "scroll",
                    {"x": payload.get("x"), "y": payload.get("y"), "dx": payload.get("dx", 0), "dy": payload.get("dy", 0)},
                    action_id=action_id,
                )
            if action == "click":
                button = payload.get("button", "left")
                if payload.get("pressed") is True:
                    return Action.create(
                        "mouse_down",
                        {"x": payload.get("x"), "y": payload.get("y"), "button": button},
                        action_id=action_id,
                    )
                if payload.get("pressed") is False:
                    return Action.create(
                        "mouse_up",
                        {"x": payload.get("x"), "y": payload.get("y"), "button": button},
                        action_id=action_id,
                    )
                return None

        if event_type == "keyboard":
            key = payload.get("key") or payload.get("char")
            if not key:
                return None
            if action == "press":
                return Action.create("key_down", {"key": key}, action_id=action_id)
            if action == "release":
                return Action.create("key_up", {"key": key}, action_id=action_id)

        return None


_ACTION_TYPES = {
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
