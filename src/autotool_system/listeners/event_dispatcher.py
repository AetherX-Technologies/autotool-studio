from __future__ import annotations

from typing import Callable

from .event import Event

EventFilter = Callable[[Event], bool]
EventHandler = Callable[[Event], None]


class EventDispatcher:
    def __init__(self) -> None:
        self._filters: list[EventFilter] = []
        self._handlers: list[EventHandler] = []

    def add_filter(self, filter_fn: EventFilter) -> None:
        self._filters.append(filter_fn)

    def add_handler(self, handler_fn: EventHandler) -> None:
        self._handlers.append(handler_fn)

    def dispatch(self, event: Event) -> None:
        for filter_fn in self._filters:
            if not filter_fn(event):
                return
        for handler_fn in self._handlers:
            handler_fn(event)
