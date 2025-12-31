from __future__ import annotations

import time

import autotool_system.core.replayer as replayer_module
from autotool_system.automation import AutomationEngine
from autotool_system.core.replayer import Replayer


class BackendStub:
    FAILSAFE = True
    PAUSE = 0

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def click(self, **kwargs: object) -> None:
        self.calls.append(("click", kwargs))

    def moveTo(self, x: int, y: int, duration: float = 0.0) -> None:
        self.calls.append(("moveTo", {"x": x, "y": y, "duration": duration}))

    def mouseDown(self, **kwargs: object) -> None:
        self.calls.append(("mouseDown", kwargs))

    def mouseUp(self, **kwargs: object) -> None:
        self.calls.append(("mouseUp", kwargs))

    def keyDown(self, key: str) -> None:
        self.calls.append(("keyDown", key))

    def keyUp(self, key: str) -> None:
        self.calls.append(("keyUp", key))

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        self.calls.append(("scroll", {"clicks": clicks, "x": x, "y": y}))

    def hscroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        self.calls.append(("hscroll", {"clicks": clicks, "x": x, "y": y}))

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey", list(keys)))


def test_replayer_plays_actions() -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)
    replayer = Replayer(engine)

    results = replayer.play(
        [
            {"type": "click", "params": {"x": 5, "y": 6}},
            {"type": "hotkey", "params": {"combo": "ctrl+shift+s"}},
        ],
        speed=1.0,
    )

    assert results[0].success is True
    assert backend.calls[0][0] == "click"
    assert backend.calls[1] == ("hotkey", ["ctrl", "shift", "s"])


def test_replayer_event_mapping_and_delta(monkeypatch) -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)
    replayer = Replayer(engine)

    sleeps: list[float] = []

    def _sleep(value: float) -> None:
        sleeps.append(value)

    monkeypatch.setattr(replayer_module.time, "sleep", _sleep)

    events = [
        {"id": "m1", "type": "mouse", "action": "move", "payload": {"x": 1, "y": 2}, "delta": 1.0},
        {"id": "m2", "type": "mouse", "action": "click", "payload": {"x": 1, "y": 2, "button": "left", "pressed": True}, "delta": 0.2},
        {"id": "m3", "type": "mouse", "action": "click", "payload": {"x": 1, "y": 2, "button": "left", "pressed": False}, "delta": 0.2},
        {"id": "k1", "type": "keyboard", "action": "press", "payload": {"key": "enter"}, "delta": 0.1},
        {"id": "k2", "type": "keyboard", "action": "release", "payload": {"key": "enter"}, "delta": 0.1},
    ]

    replayer.play(events, speed=2.0)

    assert sleeps[:2] == [0.5, 0.1]
    assert backend.calls[0][0] == "moveTo"
    assert backend.calls[1][0] == "mouseDown"
    assert backend.calls[2][0] == "mouseUp"
    assert backend.calls[3] == ("keyDown", "enter")
    assert backend.calls[4] == ("keyUp", "enter")
