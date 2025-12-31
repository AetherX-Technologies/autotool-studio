from pathlib import Path

from fastapi.testclient import TestClient

from autotool_system.api.server import create_app
from autotool_system.utils.config_manager import ConfigManager


def test_health_and_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    manager = ConfigManager()
    manager.save(
        config_path,
        {
            "automation": {"failsafe": True, "pause_interval": 0.1},
            "hotkeys": {"stop_all": "ctrl+shift+esc"},
            "storage": {"db_path": str(tmp_path / "automation.db")},
            "logging": {"level": "INFO"},
        },
    )

    app = create_app(config_path=config_path, db_path=str(tmp_path / "automation.db"), plugin_path=tmp_path)
    client = TestClient(app)

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    config = client.get("/api/v1/config")
    assert config.status_code == 200
    assert config.json()["data"]["storage"]["db_path"].endswith("automation.db")

    nodes = client.get("/api/v1/flowgram/nodes")
    assert nodes.status_code == 200
    payload = nodes.json()["data"]
    assert isinstance(payload, list)
    assert payload
    assert "type" in payload[0]
    action_click = next(node for node in payload if node["type"] == "action.click")
    assert "form" in action_click
    assert isinstance(action_click["form"].get("fields"), list)
    assert action_click["form"]["fields"]
