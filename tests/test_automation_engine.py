from types import SimpleNamespace

from autotool_system.automation import Action, AutomationEngine


class BackendStub:
    FAILSAFE = True
    PAUSE = 0

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def click(self, **kwargs: object) -> None:
        self.calls.append(("click", kwargs))

    def moveTo(self, x: int, y: int, duration: float = 0.0) -> None:
        self.calls.append(("moveTo", {"x": x, "y": y, "duration": duration}))

    def write(self, text: str, interval: float = 0.0) -> None:
        self.calls.append(("write", {"text": text, "interval": interval}))

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey", list(keys)))

    def screenshot(self, *args: object, **kwargs: object) -> SimpleNamespace:
        self.calls.append(("screenshot", {"args": args, "kwargs": kwargs}))
        return SimpleNamespace(size=(320, 200))

    def keyDown(self, key: str) -> None:
        self.calls.append(("keyDown", key))

    def keyUp(self, key: str) -> None:
        self.calls.append(("keyUp", key))

    def mouseDown(self, **kwargs: object) -> None:
        self.calls.append(("mouseDown", kwargs))

    def mouseUp(self, **kwargs: object) -> None:
        self.calls.append(("mouseUp", kwargs))

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        self.calls.append(("scroll", {"clicks": clicks, "x": x, "y": y}))

    def hscroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        self.calls.append(("hscroll", {"clicks": clicks, "x": x, "y": y}))


def test_execute_click() -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)

    result = engine.execute({"type": "click", "params": {"x": 10, "y": 20}})

    assert result.success is True
    assert backend.calls[0][0] == "click"
    assert backend.calls[0][1]["x"] == 10


def test_execute_move_speed_scales_duration() -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)

    action = Action.create("move", {"x": 5, "y": 7, "duration": 1.0})
    engine.execute(action, speed=2.0)

    _, payload = backend.calls[0]
    assert payload["duration"] == 0.5


def test_execute_hotkey_combo() -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)

    result = engine.execute({"type": "hotkey", "params": {"combo": "ctrl+shift+s"}})

    assert result.success is True
    assert backend.calls[0] == ("hotkey", ["ctrl", "shift", "s"])


def test_execute_screenshot_returns_size() -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)

    result = engine.execute({"type": "screenshot", "params": {}})

    assert result.success is True
    assert result.data is not None
    assert result.data["size"] == (320, 200)


def test_execute_key_down_and_up() -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)

    down = engine.execute({"type": "key_down", "params": {"key": "enter"}})
    up = engine.execute({"type": "key_up", "params": {"key": "enter"}})

    assert down.success is True
    assert up.success is True
    assert backend.calls[0] == ("keyDown", "enter")
    assert backend.calls[1] == ("keyUp", "enter")


def test_execute_scroll_and_hscroll() -> None:
    backend = BackendStub()
    engine = AutomationEngine(backend=backend, pause=0)

    result = engine.execute({"type": "scroll", "params": {"dx": 120, "dy": -240}})

    assert result.success is True
    assert backend.calls[0][0] == "scroll"
    assert backend.calls[1][0] == "hscroll"
