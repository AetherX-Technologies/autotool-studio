from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4
import json
import time

import yaml

from ..listeners.event import Event
from ..utils.logger import get_logger


class RecorderError(RuntimeError):
    pass


class Recorder:
    def __init__(self, *, record_moves: bool = True, min_move_interval: float = 0.0) -> None:
        self._events: list[dict[str, Any]] = []
        self._recording = False
        self._last_ts: float | None = None
        self._last_move_ts: float | None = None
        self._record_moves = record_moves
        self._min_move_interval = min_move_interval
        self._started_at: float | None = None
        self._logger = get_logger("autotool.recorder")

    def start(self) -> None:
        self._events = []
        self._last_ts = None
        self._last_move_ts = None
        self._recording = True
        self._started_at = time.time()
        self._logger.info("Recorder started")

    def stop(self) -> list[dict[str, Any]]:
        self._recording = False
        self._logger.info("Recorder stopped (%s events)", len(self._events))
        return list(self._events)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def record_event(self, event: Event | Mapping[str, Any]) -> None:
        if not self._recording:
            return
        event_obj = self._coerce_event(event)
        if not self._should_record(event_obj):
            return
        delta = 0.0 if self._last_ts is None else max(0.0, event_obj.ts - self._last_ts)
        self._last_ts = event_obj.ts
        if event_obj.type == "mouse" and event_obj.action == "move":
            self._last_move_ts = event_obj.ts
        self._events.append(
            {
                **event_obj.to_dict(),
                "delta": delta,
            }
        )

    def export(self, path: str, *, fmt: str | None = None) -> Path:
        if not self._events:
            raise RecorderError("No recorded events to export")
        target = Path(path)
        format_name = (fmt or target.suffix.lstrip(".")).lower()
        if not format_name:
            raise RecorderError("Export format is required")
        payload = {
            "version": 1,
            "recorded_at": self._started_at or time.time(),
            "events": list(self._events),
        }
        if format_name in {"json"}:
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
            self._logger.info("Recorder exported JSON to %s", target)
            return target
        if format_name in {"yaml", "yml"}:
            target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            self._logger.info("Recorder exported YAML to %s", target)
            return target
        raise RecorderError(f"Unsupported export format: {format_name}")

    def _should_record(self, event: Event) -> bool:
        if event.type == "mouse" and event.action == "move":
            if not self._record_moves:
                return False
            if self._last_move_ts is not None:
                if (event.ts - self._last_move_ts) < self._min_move_interval:
                    return False
        return True

    def _coerce_event(self, value: Event | Mapping[str, Any]) -> Event:
        if isinstance(value, Event):
            return value
        if not isinstance(value, Mapping):
            raise RecorderError("Event must be a mapping or Event instance")
        event_type = value.get("type")
        action = value.get("action")
        if not event_type or not action:
            raise RecorderError("Event requires type and action")
        payload = value.get("payload", {})
        ts = float(value.get("ts", time.time()))
        event_id = str(value.get("id") or uuid4())
        return Event(
            id=event_id,
            ts=ts,
            type=str(event_type),
            action=str(action),
            payload=dict(payload),
        )
