from __future__ import annotations

from typing import Callable

from .event import Event

try:
    from pynput import keyboard as pynput_keyboard
except Exception as exc:  # pragma: no cover - import-time guard
    pynput_keyboard = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "cmd": "cmd",
    "command": "cmd",
    "win": "cmd",
    "super": "cmd",
    "meta": "cmd",
    "esc": "esc",
    "escape": "esc",
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "pageup": "page_up",
    "pagedown": "page_down",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
}


def _normalize_combo(combo: str) -> str:
    parts = [item.strip().lower() for item in combo.split("+") if item.strip()]
    normalized: list[str] = []
    for part in parts:
        token = _ALIASES.get(part, part)
        if len(token) == 1 and token.isalnum():
            normalized.append(token)
        elif token.startswith("f") and token[1:].isdigit():
            normalized.append(f"<{token}>")
        else:
            normalized.append(f"<{token}>")
    return "+".join(normalized)


def _key_payload(key: object) -> dict:
    if pynput_keyboard is None:
        return {"key": "unknown"}

    if isinstance(key, pynput_keyboard.KeyCode):
        key_name = key.char if key.char else str(key.vk)
        return {"key": key_name, "char": key.char, "vk": key.vk}

    if isinstance(key, pynput_keyboard.Key):
        return {"key": key.name}

    return {"key": str(key)}


class KeyboardListener:
    def __init__(self, on_event: Callable[[Event], None] | None = None) -> None:
        self._on_event = on_event
        self._listener: "pynput_keyboard.Listener | None" = None
        self._running = False
        self._hotkeys: dict[str, "pynput_keyboard.HotKey"] = {}

    def register_hotkey(self, combo: str, callback: Callable[[], None]) -> str:
        self._ensure_backend()
        normalized = _normalize_combo(combo)
        if normalized in self._hotkeys:
            raise ValueError(f"Hotkey already registered: {combo}")
        try:
            parsed = pynput_keyboard.HotKey.parse(normalized)
        except Exception as exc:
            raise ValueError(f"Invalid hotkey combo: {combo}") from exc
        self._hotkeys[normalized] = pynput_keyboard.HotKey(parsed, callback)
        return normalized

    def start(self) -> None:
        self._ensure_backend()
        if self._running:
            return
        self._listener = pynput_keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
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
        if pynput_keyboard is None:
            raise RuntimeError(f"pynput is not available: {_IMPORT_ERROR}")

    def _emit(self, event: Event) -> None:
        if self._on_event is not None:
            self._on_event(event)

    def _on_press(self, key: object) -> None:
        event = Event.create("keyboard", "press", _key_payload(key))
        self._emit(event)
        for hotkey in self._hotkeys.values():
            hotkey.press(key)

    def _on_release(self, key: object) -> None:
        event = Event.create("keyboard", "release", _key_payload(key))
        self._emit(event)
        for hotkey in self._hotkeys.values():
            hotkey.release(key)
