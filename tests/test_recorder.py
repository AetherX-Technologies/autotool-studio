from __future__ import annotations

import json

import yaml

from autotool_system.core.recorder import Recorder
from autotool_system.listeners.event import Event


def test_recorder_records_delta() -> None:
    recorder = Recorder()
    recorder.start()

    recorder.record_event(Event(id="e1", ts=100.0, type="keyboard", action="press", payload={}))
    recorder.record_event(Event(id="e2", ts=101.5, type="keyboard", action="release", payload={}))

    events = recorder.stop()
    assert events[0]["delta"] == 0.0
    assert events[1]["delta"] == 1.5


def test_recorder_filters_mouse_move() -> None:
    recorder = Recorder(record_moves=True, min_move_interval=0.5)
    recorder.start()

    recorder.record_event(Event(id="m1", ts=10.0, type="mouse", action="move", payload={"x": 1, "y": 1}))
    recorder.record_event(Event(id="m2", ts=10.2, type="mouse", action="move", payload={"x": 2, "y": 2}))
    recorder.record_event(Event(id="m3", ts=10.6, type="mouse", action="move", payload={"x": 3, "y": 3}))

    events = recorder.stop()
    assert len(events) == 2
    assert events[0]["id"] == "m1"
    assert events[1]["id"] == "m3"


def test_recorder_export_json_and_yaml(tmp_path) -> None:
    recorder = Recorder()
    recorder.start()
    recorder.record_event(Event(id="e1", ts=1.0, type="keyboard", action="press", payload={"key": "a"}))

    json_path = recorder.export(tmp_path / "recording.json")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["events"][0]["payload"]["key"] == "a"

    yaml_path = recorder.export(tmp_path / "recording.yaml")
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert data["events"][0]["payload"]["key"] == "a"
