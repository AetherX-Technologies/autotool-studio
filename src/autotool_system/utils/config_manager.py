from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml


class ConfigError(RuntimeError):
    pass


class ConfigManager:
    def load(self, path: str) -> dict[str, Any]:
        target = Path(path)
        if not target.exists():
            raise ConfigError(f"Config file not found: {target}")
        content = target.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
        if not isinstance(data, dict):
            raise ConfigError("Config file must contain a mapping")
        errors = self.validate(data)
        if errors:
            raise ConfigError("; ".join(errors))
        return data

    def save(self, path: str, config: Mapping[str, Any]) -> None:
        errors = self.validate(config)
        if errors:
            raise ConfigError("; ".join(errors))
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(dict(config), sort_keys=False), encoding="utf-8")

    def merge(self, base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = deepcopy(dict(base))
        for key, value in override.items():
            if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
                result[key] = self.merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    def validate(self, config: Mapping[str, Any]) -> list[str]:
        errors: list[str] = []
        if not isinstance(config, Mapping):
            return ["config must be a mapping"]

        automation = config.get("automation", {})
        if automation and not isinstance(automation, Mapping):
            errors.append("automation must be a mapping")
        if isinstance(automation, Mapping):
            if "failsafe" in automation and not isinstance(automation.get("failsafe"), bool):
                errors.append("automation.failsafe must be a bool")
            if "pause_interval" in automation:
                if not _is_number(automation.get("pause_interval")):
                    errors.append("automation.pause_interval must be a number")

        hotkeys = config.get("hotkeys", {})
        if hotkeys and not isinstance(hotkeys, Mapping):
            errors.append("hotkeys must be a mapping")
        if isinstance(hotkeys, Mapping):
            for key, value in hotkeys.items():
                if not isinstance(value, str):
                    errors.append(f"hotkeys.{key} must be a string")

        storage = config.get("storage", {})
        if storage and not isinstance(storage, Mapping):
            errors.append("storage must be a mapping")
        if isinstance(storage, Mapping):
            if "db_path" in storage and not isinstance(storage.get("db_path"), str):
                errors.append("storage.db_path must be a string")

        logging_cfg = config.get("logging", {})
        if logging_cfg and not isinstance(logging_cfg, Mapping):
            errors.append("logging must be a mapping")
        if isinstance(logging_cfg, Mapping):
            if "level" in logging_cfg and not isinstance(logging_cfg.get("level"), str):
                errors.append("logging.level must be a string")
            if "file" in logging_cfg and not isinstance(logging_cfg.get("file"), str):
                errors.append("logging.file must be a string")

        return errors


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))
