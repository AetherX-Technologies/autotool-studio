from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4
import random
import threading
import time
import json

from ..automation import AutomationEngine
from ..core import Replayer, WorkflowBuilder
from ..core.recorder import Recorder
from ..listeners.keyboard_listener import KeyboardListener
from ..listeners.mouse_listener import MouseListener
from ..plugins import PluginManager
from ..utils.config_manager import ConfigManager
from ..utils.database import Database
from ..utils.logger import get_logger


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_node_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("nodes", [])
    return [item for item in items if isinstance(item, dict)]


class ApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "BAD_REQUEST",
        status_code: int = 400,
        details: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = details or []


@dataclass
class RunEntry:
    run_id: str
    workflow_id: str | None
    status: str
    started_at: str
    ended_at: str | None = None
    summary: str | None = None
    data: dict[str, Any] | None = None
    engine: AutomationEngine | None = None
    thread: threading.Thread | None = None
    stop_requested: bool = False


class RunManager:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._runs: dict[str, RunEntry] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("autotool.api.run")

    def start_workflow(
        self,
        workflow_id: str,
        actions: list[Mapping[str, Any]],
        *,
        speed: float = 1.0,
        stop_on_error: bool = False,
    ) -> RunEntry:
        run_id = str(uuid4())
        started_at = _now_iso()
        engine = AutomationEngine()
        entry = RunEntry(
            run_id=run_id,
            workflow_id=workflow_id,
            status="running",
            started_at=started_at,
            engine=engine,
        )
        with self._lock:
            self._runs[run_id] = entry

        self._db.log_run(
            {
                "id": run_id,
                "workflow_id": workflow_id,
                "status": "running",
                "started_at": started_at,
                "ended_at": None,
                "summary": None,
                "data": {"type": "workflow"},
            }
        )

        thread = threading.Thread(
            target=self._run_actions,
            args=(entry, actions, speed, stop_on_error),
            daemon=True,
        )
        entry.thread = thread
        thread.start()
        return entry

    def stop_run(self, run_id: str) -> bool:
        entry = self._runs.get(run_id)
        if entry is None:
            return False
        entry.stop_requested = True
        if entry.engine is not None:
            entry.engine.stop()
        return True

    def get_run(self, run_id: str) -> RunEntry | None:
        return self._runs.get(run_id)

    def _run_actions(
        self,
        entry: RunEntry,
        actions: list[Mapping[str, Any]],
        speed: float,
        stop_on_error: bool,
    ) -> None:
        engine = entry.engine
        if engine is None:
            return
        results = engine.execute_sequence(actions, speed=speed)
        success_count = len([result for result in results if result.success])
        if entry.stop_requested:
            status = "stopped"
        else:
            status = "success" if success_count == len(results) else "failed"
        summary = f"{success_count}/{len(results)} succeeded"
        ended_at = _now_iso()

        entry.status = status
        entry.summary = summary
        entry.ended_at = ended_at
        entry.data = {"results": [result.to_dict() for result in results]}

        self._db.update_run(
            entry.run_id,
            status=status,
            ended_at=ended_at,
            summary=summary,
            data=entry.data,
        )
        self._logger.info("Run %s finished with status %s", entry.run_id, status)


class RecorderSession:
    def __init__(self) -> None:
        self._recorder: Recorder | None = None
        self._keyboard: KeyboardListener | None = None
        self._mouse: MouseListener | None = None
        self._lock = threading.Lock()
        self._logger = get_logger("autotool.api.recording")

    def start(self, *, record_moves: bool = True, min_move_interval: float = 0.0) -> None:
        with self._lock:
            if self._recorder is not None:
                raise ApiError("Recording already running", code="CONFLICT", status_code=409)
            recorder = Recorder(record_moves=record_moves, min_move_interval=min_move_interval)
            recorder.start()
            keyboard = KeyboardListener(recorder.record_event)
            mouse = MouseListener(recorder.record_event)
            keyboard.start()
            mouse.start()
            self._recorder = recorder
            self._keyboard = keyboard
            self._mouse = mouse
        self._logger.info("Recording started")

    def stop(self) -> list[dict[str, Any]]:
        with self._lock:
            if self._recorder is None:
                raise ApiError("No active recording", code="BAD_REQUEST", status_code=400)
            if self._keyboard is not None:
                self._keyboard.stop()
            if self._mouse is not None:
                self._mouse.stop()
            events = self._recorder.stop()
            self._recorder = None
            self._keyboard = None
            self._mouse = None
        self._logger.info("Recording stopped (%s events)", len(events))
        return events

    def status(self) -> str:
        return "running" if self._recorder is not None else "idle"


class ReplaySession:
    def __init__(self) -> None:
        self._replayer = Replayer()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._status = "idle"
        self._last_results: list[dict[str, Any]] | None = None
        self._logger = get_logger("autotool.api.replay")

    def start(
        self,
        items: list[Mapping[str, Any]],
        *,
        speed: float = 1.0,
        stop_on_error: bool = False,
    ) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise ApiError("Replay already running", code="CONFLICT", status_code=409)
            self._status = "running"
            self._thread = threading.Thread(
                target=self._run,
                args=(items, speed, stop_on_error),
                daemon=True,
            )
            self._thread.start()
        self._logger.info("Replay started")

    def stop(self) -> None:
        with self._lock:
            self._replayer.stop()
            self._status = "stopped"
        self._logger.info("Replay stop requested")

    def status(self) -> str:
        return self._status

    def last_results(self) -> list[dict[str, Any]] | None:
        return self._last_results

    def _run(self, items: list[Mapping[str, Any]], speed: float, stop_on_error: bool) -> None:
        results = self._replayer.play(items, speed=speed, stop_on_error=stop_on_error)
        self._last_results = [result.to_dict() for result in results]
        self._status = "idle"
        self._logger.info("Replay finished (%s results)", len(results))


class AutoClickerSession:
    def __init__(self) -> None:
        self._backend: Any | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._status = "idle"
        self._clicks = 0
        self._started_at: str | None = None
        self._ended_at: str | None = None
        self._settings: dict[str, Any] = {}
        self._error: str | None = None
        self._lock = threading.Lock()
        self._logger = get_logger("autotool.api.autoclicker")

    def _get_backend(self) -> Any:
        if self._backend is None:
            try:
                import pyautogui
            except Exception as exc:
                raise ApiError(f"pyautogui is not available: {exc}", code="INTERNAL_ERROR", status_code=500)
            self._backend = pyautogui
        return self._backend

    def start(
        self,
        *,
        cps: float,
        button: str = "left",
        duration: float | None = None,
        max_clicks: int | None = None,
        jitter_ms: float | None = None,
    ) -> None:
        if cps <= 0:
            raise ApiError("CPS must be greater than 0", code="BAD_REQUEST")
        if duration is not None and duration <= 0:
            raise ApiError("Duration must be greater than 0", code="BAD_REQUEST")
        if max_clicks is not None and max_clicks <= 0:
            raise ApiError("Max clicks must be greater than 0", code="BAD_REQUEST")
        if jitter_ms is not None and jitter_ms < 0:
            raise ApiError("Jitter must be non-negative", code="BAD_REQUEST")
        button = (button or "left").lower()
        if button not in {"left", "right", "middle"}:
            raise ApiError("Unsupported mouse button", code="BAD_REQUEST")

        backend = self._get_backend()
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise ApiError("Autoclicker already running", code="CONFLICT", status_code=409)
            self._stop_event.clear()
            self._status = "running"
            self._clicks = 0
            self._error = None
            self._started_at = _now_iso()
            self._ended_at = None
            self._settings = {
                "cps": cps,
                "button": button,
                "duration": duration,
                "max_clicks": max_clicks,
                "jitter_ms": jitter_ms,
            }
            thread = threading.Thread(
                target=self._run,
                args=(backend, cps, button, duration, max_clicks, jitter_ms),
                daemon=True,
            )
            self._thread = thread
            thread.start()
        self._logger.info("Autoclicker started (cps=%s button=%s)", cps, button)

    def stop(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                return
            self._stop_event.set()
            self._status = "stopping"
        self._logger.info("Autoclicker stop requested")

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "clicks": self._clicks,
                "started_at": self._started_at,
                "ended_at": self._ended_at,
                "settings": dict(self._settings),
                "error": self._error,
            }

    def _run(
        self,
        backend: Any,
        cps: float,
        button: str,
        duration: float | None,
        max_clicks: int | None,
        jitter_ms: float | None,
    ) -> None:
        interval = 1.0 / cps
        jitter = (jitter_ms or 0.0) / 1000.0
        clicks = 0
        start_time = time.perf_counter()
        next_time = start_time
        error: str | None = None
        status = "idle"
        try:
            while not self._stop_event.is_set():
                now = time.perf_counter()
                if duration is not None and now - start_time >= duration:
                    break
                if max_clicks is not None and clicks >= max_clicks:
                    break
                if now < next_time:
                    time.sleep(min(0.01, next_time - now))
                    continue
                backend.click(button=button)
                clicks += 1
                if clicks % 10 == 0:
                    with self._lock:
                        self._clicks = clicks
                if jitter > 0:
                    offset = random.uniform(-jitter, jitter)
                    next_time += max(0.001, interval + offset)
                else:
                    next_time += interval
        except Exception as exc:
            error = str(exc)
            status = "error"
            self._logger.error("Autoclicker failed: %s", exc)
        finally:
            with self._lock:
                self._clicks = clicks
                self._ended_at = _now_iso()
                self._error = error
                self._status = status
                self._thread = None
                self._stop_event.clear()


@dataclass
class ApiState:
    config_path: Path
    config: dict[str, Any]
    config_manager: ConfigManager
    db: Database
    workflow_builder: WorkflowBuilder
    plugin_manager: PluginManager
    run_manager: RunManager
    recorder: RecorderSession
    replay: ReplaySession
    autoclicker: AutoClickerSession
    node_registry: list[dict[str, Any]]
