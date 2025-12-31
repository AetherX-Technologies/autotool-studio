from pathlib import Path

from autotool_system.plugins import PluginManager


def _write_plugin(tmp_path: Path, plugin_id: str, body: str) -> Path:
    plugin_dir = tmp_path / plugin_id
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(
        (
            "{\n"
            f'  "id": "{plugin_id}",\n'
            f'  "name": "{plugin_id}",\n'
            '  "version": "0.1.0",\n'
            '  "entry": "plugin.py"\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(body, encoding="utf-8")
    return plugin_dir


def test_plugin_discover_load_and_unload(tmp_path: Path) -> None:
    body = (
        "class SamplePlugin:\n"
        "    def __init__(self, spec):\n"
        "        self.spec = spec\n"
        "    def register(self, registry):\n"
        "        registry.register_action('sample.echo', lambda params: params, plugin_id=self.spec.plugin_id)\n"
        "    def shutdown(self):\n"
        "        return None\n"
        "\n"
        "def create_plugin(spec):\n"
        "    return SamplePlugin(spec)\n"
    )
    _write_plugin(tmp_path, "sample-plugin", body)

    manager = PluginManager()
    discovered = manager.discover(tmp_path)
    assert discovered

    plugin = manager.load("sample-plugin")
    assert plugin is not None
    assert manager.registry.get_action("sample.echo") is not None

    assert manager.unload("sample-plugin") is True
    assert manager.registry.get_action("sample.echo") is None


def test_plugin_load_error_does_not_raise(tmp_path: Path) -> None:
    body = (
        "def create_plugin(spec):\n"
        "    raise RuntimeError('boom')\n"
    )
    _write_plugin(tmp_path, "bad-plugin", body)

    manager = PluginManager()
    manager.discover(tmp_path)
    assert manager.load("bad-plugin") is None
    assert "boom" in (manager.get_error("bad-plugin") or "")
