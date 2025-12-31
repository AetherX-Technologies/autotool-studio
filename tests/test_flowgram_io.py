import pytest

from autotool_system.utils.flowgram_io import FlowGramError, graph_counts, normalize_flowgram_payload


def test_normalize_flowgram_graph_payload() -> None:
    payload = {"nodes": [{"id": "n1"}], "edges": []}
    workflow = normalize_flowgram_payload(payload)

    assert workflow["graph"]["nodes"] == payload["nodes"]
    assert workflow["graph"]["edges"] == payload["edges"]
    assert workflow["id"] == ""
    assert workflow["name"] == ""


def test_normalize_flowgram_workflow_payload() -> None:
    payload = {"id": "wf-1", "name": "Demo", "graph": {"nodes": [], "edges": []}}
    workflow = normalize_flowgram_payload(payload)

    assert workflow["id"] == "wf-1"
    assert workflow["name"] == "Demo"
    assert workflow["graph"]["nodes"] == []
    assert workflow["graph"]["edges"] == []


def test_normalize_flowgram_invalid_payload() -> None:
    with pytest.raises(FlowGramError):
        normalize_flowgram_payload({"nodes": "bad", "edges": []})


def test_graph_counts() -> None:
    nodes, edges = graph_counts({"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": [{"id": "e1"}]})
    assert nodes == 2
    assert edges == 1
