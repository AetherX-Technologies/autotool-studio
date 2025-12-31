from __future__ import annotations

from typing import Callable

from .event import Event

try:
    from pynput import mouse as pynput_mouse
except Exception as exc:  # pragma: no cover - import-time guard
    pynput_mouse = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _button_name(button: object) -> str:
    if pynput_mouse is None:
        return str(button)
    return getattr(button, "name", str(button))


class MouseListener:
    def __init__(self, on_event: Callable[[Event], None] | None = None) -> None:
        self._on_event = on_event
        self._listener: "pynput_mouse.Listener | None" = None
        self._running = False

    def start(self) -> None:
        self._ensure_backend()
        if self._running:
            return
        self._listener = pynput_mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._listener.start()
        self._running = True

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def _ensure_backend(self) -> None:
        if pynput_mouse is None:
            raise RuntimeError(f"pynput is not available: {_IMPORT_ERROR}")

    def _emit(self, event: Event) -> None:
        if self._on_event is not None:
            self._on_event(event)

    def _on_move(self, x: int, y: int) -> None:
        event = Event.create("mouse", "move", {"x": x, "y": y})
        self._emit(event)

    def _on_click(self, x: int, y: int, button: object, pressed: bool) -> None:
        payload = {"x": x, "y": y, "button": _button_name(button), "pressed": pressed}
        event = Event.create("mouse", "click", payload)
        self._emit(event)

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        payload = {"x": x, "y": y, "dx": dx, "dy": dy}
        event = Event.create("mouse", "scroll", payload)
        self._emit(event)
