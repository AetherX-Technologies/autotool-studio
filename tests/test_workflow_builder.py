from __future__ import annotations

import pytest

from autotool_system.core.workflow_builder import WorkflowBuilder, WorkflowError


def test_workflow_steps_compile() -> None:
    builder = WorkflowBuilder()
    workflow = {
        "id": "wf_steps",
        "name": "Steps Workflow",
        "steps": [
            {"type": "click", "params": {"x": 1, "y": 2}},
            {"type": "wait", "params": {"seconds": 1}},
        ],
    }
    actions = builder.compile(workflow)
    assert actions[0].type == "click"
    assert actions[1].type == "wait"


def test_workflow_graph_compile_flowgram_style() -> None:
    builder = WorkflowBuilder()
    workflow = {
        "id": "wf_graph",
        "name": "Graph Workflow",
        "graph": {
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "n1", "type": "action", "data": {"action": {"type": "click", "params": {"x": 1, "y": 2}}}},
                {"id": "n2", "type": "action", "data": {"type": "wait", "params": {"seconds": 0.5}}},
            ],
            "edges": [
                {"from": "start", "to": "n1"},
                {"from": "n1", "to": "n2"},
            ],
        },
    }
    actions = builder.compile(workflow)
    assert [action.id for action in actions] == ["n1", "n2"]


def test_workflow_detects_cycles() -> None:
    builder = WorkflowBuilder()
    workflow = {
        "id": "wf_cycle",
        "name": "Cycle Workflow",
        "graph": {
            "nodes": [
                {"id": "a", "type": "action", "data": {"type": "click", "params": {"x": 1, "y": 2}}},
                {"id": "b", "type": "action", "data": {"type": "click", "params": {"x": 2, "y": 3}}},
            ],
            "edges": [
                {"from": "a", "to": "b"},
                {"from": "b", "to": "a"},
            ],
        },
    }
    with pytest.raises(WorkflowError):
        builder.compile(workflow)
