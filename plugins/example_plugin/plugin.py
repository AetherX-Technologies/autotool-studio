from __future__ import annotations

from typing import Any, Mapping

from autotool_system.plugins import PluginBase, PluginRegistry, PluginSpec


class ExamplePlugin(PluginBase):
    def register(self, registry: PluginRegistry) -> None:
        def echo_action(params: Mapping[str, Any]) -> dict[str, Any]:
            message = params.get("message", "hello")
            return {"message": str(message)}

        registry.register_action("example.echo", echo_action, plugin_id=self.plugin_id)

    def shutdown(self) -> None:
        return None


def create_plugin(spec: PluginSpec) -> ExamplePlugin:
    return ExamplePlugin(spec)
