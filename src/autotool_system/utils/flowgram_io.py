from __future__ import annotations

from typing import Any, Mapping


class FlowGramError(ValueError):
    pass


def extract_flowgram_graph(payload: Mapping[str, Any]) -> dict[str, Any]:
    graph = payload.get("graph") if isinstance(payload, Mapping) else None
    if graph is None and isinstance(payload, Mapping) and "nodes" in payload:
        graph = payload
    if not isinstance(graph, Mapping):
        raise FlowGramError("FlowGram payload must include a graph mapping")

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise FlowGramError("FlowGram graph requires 'nodes' and 'edges' lists")

    return {"nodes": nodes, "edges": edges}


def normalize_flowgram_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    graph = extract_flowgram_graph(payload)
    workflow_id = payload.get("id") if isinstance(payload, Mapping) else None
    name = payload.get("name") if isinstance(payload, Mapping) else None
    return {"id": str(workflow_id or ""), "name": str(name or ""), "graph": graph}


def graph_counts(graph: Mapping[str, Any]) -> tuple[int, int]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    return (len(nodes) if isinstance(nodes, list) else 0, len(edges) if isinstance(edges, list) else 0)
