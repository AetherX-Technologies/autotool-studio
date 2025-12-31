from __future__ import annotations

from typing import Any

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    import pygetwindow
except Exception as exc:  # pragma: no cover - import-time guard
    pygetwindow = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class WindowManager:
    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend or pyautogui

    def focus_window(self, title: str) -> bool:
        windows = self._get_windows(title)
        if not windows:
            return False
        window = windows[0]
        if hasattr(window, "activate"):
            window.activate()
        elif hasattr(window, "focus"):
            window.focus()
        return True

    def _get_windows(self, title: str) -> list[Any]:
        if self._backend is not None and hasattr(self._backend, "getWindowsWithTitle"):
            return list(self._backend.getWindowsWithTitle(title))
        if pygetwindow is None:
            raise RuntimeError(f"pygetwindow is not available: {_IMPORT_ERROR}")
        return list(pygetwindow.getWindowsWithTitle(title))
