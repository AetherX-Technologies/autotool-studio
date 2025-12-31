from __future__ import annotations

from collections import deque
from typing import Any, Mapping

from ..automation import Action, ActionError


class WorkflowError(RuntimeError):
    pass


class WorkflowBuilder:
    def validate(self, workflow: Mapping[str, Any]) -> list[str]:
        errors: list[str] = []
        if not isinstance(workflow, Mapping):
            return ["workflow must be a mapping"]

        if not workflow.get("id"):
            errors.append("workflow.id is required")
        if not workflow.get("name"):
            errors.append("workflow.name is required")

        if "steps" in workflow:
            steps = workflow.get("steps")
            if not isinstance(steps, list):
                errors.append("workflow.steps must be a list")
            else:
                for idx, step in enumerate(steps):
                    try:
                        Action.from_obj(step)
                    except ActionError as exc:
                        errors.append(f"steps[{idx}] invalid: {exc}")

        elif "graph" in workflow:
            graph = workflow.get("graph")
            if not isinstance(graph, Mapping):
                errors.append("workflow.graph must be a mapping")
            else:
                nodes = graph.get("nodes")
                edges = graph.get("edges")
                if not isinstance(nodes, list) or not nodes:
                    errors.append("workflow.graph.nodes must be a non-empty list")
                if not isinstance(edges, list):
                    errors.append("workflow.graph.edges must be a list")
                if isinstance(nodes, list):
                    ids = [node.get("id") for node in nodes if isinstance(node, Mapping)]
                    if any(not node_id for node_id in ids):
                        errors.append("workflow.graph.nodes require id")
                    if len(set(ids)) != len(ids):
                        errors.append("workflow.graph.nodes ids must be unique")
                if isinstance(nodes, list) and isinstance(edges, list):
                    node_ids = {node.get("id") for node in nodes if isinstance(node, Mapping)}
                    for edge in edges:
                        if not isinstance(edge, Mapping):
                            errors.append("workflow.graph.edges entries must be mappings")
                            continue
                        source = _edge_from(edge)
                        target = _edge_to(edge)
                        if source not in node_ids or target not in node_ids:
                            errors.append(f"edge references missing node: {source} -> {target}")
                    if not errors and _has_cycle(nodes, edges):
                        errors.append("workflow.graph contains cycles")
                    if isinstance(nodes, list):
                        for node in nodes:
                            if not isinstance(node, Mapping):
                                continue
                            action_data = _extract_action_data(node)
                            if action_data is None:
                                continue
                            try:
                                Action.from_obj(action_data)
                            except ActionError as exc:
                                errors.append(f"node {node.get('id')} invalid action: {exc}")
        else:
            errors.append("workflow.steps or workflow.graph is required")

        return errors

    def compile(self, workflow: Mapping[str, Any]) -> list[Action]:
        errors = self.validate(workflow)
        if errors:
            raise WorkflowError("; ".join(errors))

        if "steps" in workflow:
            steps = workflow.get("steps", [])
            return [Action.from_obj(step) for step in steps]

        graph = workflow.get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_map = {node["id"]: node for node in nodes if isinstance(node, Mapping)}

        ordered_ids = _toposort(node_map, edges)
        actions: list[Action] = []
        for node_id in ordered_ids:
            node = node_map[node_id]
            action_data = _extract_action_data(node)
            if action_data is None:
                continue
            action_payload = dict(action_data)
            action_payload.setdefault("id", node_id)
            actions.append(Action.from_obj(action_payload))

        if not actions:
            raise WorkflowError("workflow contains no executable actions")
        return actions


def _edge_from(edge: Mapping[str, Any]) -> str | None:
    return (
        edge.get("from")
        or edge.get("source")
        or edge.get("src")
        or edge.get("start")
        or edge.get("sourceId")
        or edge.get("sourceNodeID")
        or edge.get("sourceNodeId")
    )


def _edge_to(edge: Mapping[str, Any]) -> str | None:
    return (
        edge.get("to")
        or edge.get("target")
        or edge.get("dst")
        or edge.get("end")
        or edge.get("targetId")
        or edge.get("targetNodeID")
        or edge.get("targetNodeId")
    )


def _node_type(node: Mapping[str, Any]) -> str:
    return str(node.get("type") or "").lower()


def _extract_action_data(node: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if "action" in node:
        return node.get("action")
    data = node.get("data")
    if isinstance(data, Mapping):
        if "action" in data:
            return data.get("action")
        if "type" in data:
            return {"type": data.get("type"), "params": data.get("params", {})}
    if "type" in node and "params" in node:
        return {"type": node.get("type"), "params": node.get("params", {})}
    return None


def _has_cycle(nodes: list[Mapping[str, Any]], edges: list[Mapping[str, Any]]) -> bool:
    node_map = {node["id"]: node for node in nodes if isinstance(node, Mapping) and node.get("id")}
    ordered = _toposort(node_map, edges, allow_partial=True)
    return len(ordered) != len(node_map)


def _toposort(
    nodes: Mapping[str, Mapping[str, Any]],
    edges: list[Mapping[str, Any]],
    *,
    allow_partial: bool = False,
) -> list[str]:
    in_degree = {node_id: 0 for node_id in nodes}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes}

    for edge in edges:
        if not isinstance(edge, Mapping):
            continue
        source = _edge_from(edge)
        target = _edge_to(edge)
        if source in nodes and target in nodes:
            adjacency[source].append(target)
            in_degree[target] += 1

    def sort_key(node_id: str) -> tuple[int, str]:
        return (0 if _node_type(nodes[node_id]) == "start" else 1, node_id)

    queue = deque(sorted([nid for nid, degree in in_degree.items() if degree == 0], key=sort_key))
    ordered: list[str] = []

    while queue:
        current = queue.popleft()
        ordered.append(current)
        for neighbor in sorted(adjacency[current]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if allow_partial:
        return ordered

    if len(ordered) != len(nodes):
        raise WorkflowError("workflow graph contains cycles or disconnected nodes")
    return ordered
