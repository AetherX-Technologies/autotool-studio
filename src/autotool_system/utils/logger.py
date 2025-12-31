from __future__ import annotations

from pathlib import Path
import logging


def configure_logging(level: str = "INFO", log_file: str | None = None, *, force: bool = False) -> None:
    root = logging.getLogger()
    level_name = str(level).upper()
    if root.handlers and not force:
        root.setLevel(level_name)
        return

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        target = Path(log_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(target, encoding="utf-8"))

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    for handler in handlers:
        handler.setFormatter(formatter)

    root.handlers = handlers
    root.setLevel(level_name)


def get_logger(name: str = "autotool") -> logging.Logger:
    root = logging.getLogger()
    if not root.handlers:
        configure_logging()
    return logging.getLogger(name)
