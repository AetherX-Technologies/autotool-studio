from autotool_system.core.safety import SafetyController


class DummyEngine:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class DummyListener:
    def __init__(self) -> None:
        self.combo = None
        self.callback = None

    def register_hotkey(self, combo, callback):
        self.combo = combo
        self.callback = callback
        return combo


def test_safety_trigger_calls_handlers() -> None:
    controller = SafetyController()
    engine = DummyEngine()
    called = []

    controller.register_engine(engine)
    controller.add_handler(lambda: called.append("hit"))
    controller.trigger()

    assert controller.triggered is True
    assert engine.stopped is True
    assert called == ["hit"]


def test_safety_register_hotkey() -> None:
    controller = SafetyController()
    listener = DummyListener()
    combo = controller.register_hotkey(listener, "ctrl+shift+esc")

    assert combo == "ctrl+shift+esc"
    assert listener.callback == controller.trigger
