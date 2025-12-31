from __future__ import annotations

import pytest

from autotool_system.utils.config_manager import ConfigError, ConfigManager


def test_load_and_merge(tmp_path) -> None:
    manager = ConfigManager()
    base = {
        "automation": {"failsafe": True, "pause_interval": 0.1},
        "hotkeys": {"stop_all": "ctrl+shift+esc"},
        "storage": {"db_path": "data/automation.db"},
    }
    override = {"automation": {"pause_interval": 0.5}}
    merged = manager.merge(base, override)
    assert merged["automation"]["pause_interval"] == 0.5

    config_path = tmp_path / "config.yaml"
    manager.save(config_path, merged)
    loaded = manager.load(config_path)
    assert loaded["automation"]["failsafe"] is True


def test_validate_rejects_invalid_types() -> None:
    manager = ConfigManager()
    with pytest.raises(ConfigError):
        manager.save("config.yaml", {"automation": {"failsafe": "yes"}})
