from __future__ import annotations

from typing import Callable

from ..listeners.keyboard_listener import KeyboardListener
from ..utils.logger import get_logger


class SafetyController:
    def __init__(self) -> None:
        self._handlers: list[Callable[[], None]] = []
        self._triggered = False
        self._logger = get_logger("autotool.safety")

    @property
    def triggered(self) -> bool:
        return self._triggered

    def add_handler(self, handler: Callable[[], None]) -> None:
        self._handlers.append(handler)

    def register_hotkey(self, listener: KeyboardListener, combo: str) -> str:
        return listener.register_hotkey(combo, self.trigger)

    def register_engine(self, engine: object) -> None:
        stop = getattr(engine, "stop", None)
        if callable(stop):
            self.add_handler(stop)

    def register_replayer(self, replayer: object) -> None:
        stop = getattr(replayer, "stop", None)
        if callable(stop):
            self.add_handler(stop)

    def trigger(self) -> None:
        if not self._triggered:
            self._triggered = True
        self._logger.warning("Emergency stop triggered")
        for handler in list(self._handlers):
            try:
                handler()
            except Exception as exc:
                self._logger.warning("Emergency handler failed: %s", exc)

    def reset(self) -> None:
        self._triggered = False
