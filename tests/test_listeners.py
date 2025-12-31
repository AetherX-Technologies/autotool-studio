from autotool_system.listeners.event import Event
from autotool_system.listeners.event_dispatcher import EventDispatcher


def test_event_create() -> None:
    event = Event.create("keyboard", "press", {"key": "a"})
    assert event.type == "keyboard"
    assert event.action == "press"
    assert event.payload["key"] == "a"
    assert event.id
    assert event.ts > 0
    data = event.to_dict()
    assert data["type"] == "keyboard"


def test_dispatcher_filters_and_handlers() -> None:
    dispatcher = EventDispatcher()
    seen: list[Event] = []

    dispatcher.add_filter(lambda evt: evt.type != "mouse")
    dispatcher.add_handler(seen.append)

    dispatcher.dispatch(Event.create("keyboard", "press", {"key": "a"}))
    dispatcher.dispatch(Event.create("mouse", "move", {"x": 1, "y": 2}))

    assert len(seen) == 1
