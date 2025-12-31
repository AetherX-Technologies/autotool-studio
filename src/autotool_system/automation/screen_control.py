from __future__ import annotations

from typing import Any

try:
    import pyautogui
except Exception as exc:  # pragma: no cover - import-time guard
    pyautogui = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _get_backend() -> Any:
    if pyautogui is None:
        raise RuntimeError(f"pyautogui is not available: {_IMPORT_ERROR}")
    return pyautogui


class ScreenControl:
    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend or _get_backend()

    def screenshot(
        self,
        region: tuple[int, int, int, int] | None = None,
        *,
        path: str | None = None,
    ) -> object:
        if path:
            return self._backend.screenshot(path, region=region)
        return self._backend.screenshot(region=region)

    def locate_on_screen(
        self,
        image_path: str,
        *,
        region: tuple[int, int, int, int] | None = None,
        confidence: float | None = None,
    ) -> object:
        return self._backend.locateOnScreen(image_path, region=region, confidence=confidence)
