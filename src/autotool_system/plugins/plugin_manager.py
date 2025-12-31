from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable
import importlib.util
import json
import re

from ..utils.logger import get_logger


MANIFEST_NAME = "plugin.json"


class PluginError(RuntimeError):
    pass


@dataclass(frozen=True)
class PluginSpec:
    plugin_id: str
    name: str
    version: str
    entry: str
    root: Path
    description: str | None = None
    author: str | None = None

    @property
    def id(self) -> str:
        return self.plugin_id

    @property
    def entry_path(self) -> Path:
        entry_path = Path(self.entry)
        if entry_path.is_absolute():
            return entry_path
        return (self.root / entry_path).resolve()


class PluginBase:
    def __init__(self, spec: PluginSpec) -> None:
        self.spec = spec

    @property
    def plugin_id(self) -> str:
        return self.spec.plugin_id

    def register(self, registry: PluginRegistry) -> None:  # pragma: no cover - override point
        return None

    def shutdown(self) -> None:  # pragma: no cover - override point
        return None


class PluginRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, tuple[Callable[..., Any], str]] = {}
        self._triggers: dict[str, tuple[Callable[..., Any], str]] = {}
        self._ui_components: dict[str, tuple[Callable[..., Any], str]] = {}

    def register_action(self, action_type: str, handler: Callable[..., Any], *, plugin_id: str) -> None:
        if action_type in self._actions:
            raise PluginError(f"Action already registered: {action_type}")
        self._actions[action_type] = (handler, plugin_id)

    def register_trigger(self, name: str, handler: Callable[..., Any], *, plugin_id: str) -> None:
        if name in self._triggers:
            raise PluginError(f"Trigger already registered: {name}")
        self._triggers[name] = (handler, plugin_id)

    def register_ui_component(self, name: str, builder: Callable[..., Any], *, plugin_id: str) -> None:
        if name in self._ui_components:
            raise PluginError(f"UI component already registered: {name}")
        self._ui_components[name] = (builder, plugin_id)

    def get_action(self, action_type: str) -> Callable[..., Any] | None:
        entry = self._actions.get(action_type)
        return entry[0] if entry else None

    def get_trigger(self, name: str) -> Callable[..., Any] | None:
        entry = self._triggers.get(name)
        return entry[0] if entry else None

    def get_ui_component(self, name: str) -> Callable[..., Any] | None:
        entry = self._ui_components.get(name)
        return entry[0] if entry else None

    def list_actions(self) -> list[str]:
        return sorted(self._actions.keys())

    def list_triggers(self) -> list[str]:
        return sorted(self._triggers.keys())

    def list_ui_components(self) -> list[str]:
        return sorted(self._ui_components.keys())

    def remove_plugin(self, plugin_id: str) -> None:
        self._actions = {key: value for key, value in self._actions.items() if value[1] != plugin_id}
        self._triggers = {key: value for key, value in self._triggers.items() if value[1] != plugin_id}
        self._ui_components = {
            key: value for key, value in self._ui_components.items() if value[1] != plugin_id
        }


class PluginManager:
    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self._registry = registry or PluginRegistry()
        self._logger = get_logger("autotool.plugins")
        self._catalog: dict[str, PluginSpec] = {}
        self._loaded: dict[str, PluginBase] = {}
        self._errors: dict[str, str] = {}

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    def discover(self, path: str | Path) -> list[PluginSpec]:
        root = Path(path)
        manifests = self._find_manifests(root)
        found: list[PluginSpec] = []
        for manifest in manifests:
            try:
                spec = self._load_manifest(manifest)
            except PluginError as exc:
                self._logger.warning("Skipping plugin manifest %s: %s", manifest, exc)
                continue
            if spec.plugin_id in self._catalog:
                self._logger.warning("Duplicate plugin id %s ignored", spec.plugin_id)
                continue
            self._catalog[spec.plugin_id] = spec
            found.append(spec)
        return found

    def load(self, plugin_id: str) -> PluginBase | None:
        if plugin_id in self._loaded:
            return self._loaded[plugin_id]
        spec = self._catalog.get(plugin_id)
        if spec is None:
            self._errors[plugin_id] = "Plugin not discovered"
            return None
        try:
            module = self._load_module(spec)
            plugin = self._create_plugin(module, spec)
            plugin.register(self._registry)
        except Exception as exc:
            self._errors[plugin_id] = str(exc)
            self._logger.warning("Failed to load plugin %s: %s", plugin_id, exc)
            return None
        self._loaded[plugin_id] = plugin
        self._errors.pop(plugin_id, None)
        return plugin

    def unload(self, plugin_id: str) -> bool:
        plugin = self._loaded.pop(plugin_id, None)
        if plugin is None:
            return False
        try:
            plugin.shutdown()
        except Exception as exc:
            self._logger.warning("Plugin %s shutdown error: %s", plugin_id, exc)
        self._registry.remove_plugin(plugin_id)
        return True

    def get_error(self, plugin_id: str) -> str | None:
        return self._errors.get(plugin_id)

    def list_discovered(self) -> list[PluginSpec]:
        return list(self._catalog.values())

    def list_loaded(self) -> list[str]:
        return sorted(self._loaded.keys())

    def _find_manifests(self, root: Path) -> list[Path]:
        manifests: list[Path] = []
        if root.is_file():
            if root.name == MANIFEST_NAME:
                manifests.append(root)
            return manifests
        if not root.exists():
            return manifests
        if (root / MANIFEST_NAME).exists():
            manifests.append(root / MANIFEST_NAME)
        for child in root.iterdir():
            if child.is_dir():
                manifest = child / MANIFEST_NAME
                if manifest.exists():
                    manifests.append(manifest)
        return manifests

    def _load_manifest(self, path: Path) -> PluginSpec:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            raise PluginError(f"Invalid manifest: {exc}") from exc

        plugin_id = str(payload.get("id", "")).strip()
        name = str(payload.get("name", "")).strip()
        version = str(payload.get("version", "")).strip()
        entry = str(payload.get("entry", "")).strip()
        if not plugin_id or not name or not version or not entry:
            raise PluginError("Manifest requires id, name, version, and entry")

        description = payload.get("description")
        author = payload.get("author")
        return PluginSpec(
            plugin_id=plugin_id,
            name=name,
            version=version,
            entry=entry,
            root=path.parent,
            description=str(description) if description else None,
            author=str(author) if author else None,
        )

    def _load_module(self, spec: PluginSpec) -> ModuleType:
        entry_path = spec.entry_path
        if not entry_path.exists():
            raise PluginError(f"Entry file not found: {entry_path}")
        module_name = f"autotool_plugin_{_slugify(spec.plugin_id)}"
        module_spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if module_spec is None or module_spec.loader is None:
            raise PluginError("Failed to load plugin module spec")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    def _create_plugin(self, module: ModuleType, spec: PluginSpec) -> PluginBase:
        creator = getattr(module, "create_plugin", None)
        if creator is None:
            raise PluginError("Plugin entry must define create_plugin(spec)")
        plugin = creator(spec)
        if plugin is None or not hasattr(plugin, "register"):
            raise PluginError("create_plugin must return a plugin instance")
        if not hasattr(plugin, "shutdown"):
            raise PluginError("Plugin instance requires shutdown()")
        return plugin


def _slugify(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]+", "_", value)
