from __future__ import annotations

from autotool_system.utils.database import Database


def test_database_save_and_get(tmp_path) -> None:
    db_path = tmp_path / "automation.db"
    db = Database()
    db.connect(str(db_path))
    db.migrate()

    workflow = {"id": "wf1", "name": "Test Workflow", "steps": [{"type": "wait", "params": {"seconds": 1}}]}
    db.save_workflow(workflow)

    loaded = db.get_workflow("wf1")
    assert loaded is not None
    assert loaded["name"] == "Test Workflow"


def test_database_log_run(tmp_path) -> None:
    db_path = tmp_path / "automation.db"
    db = Database()
    db.connect(str(db_path))
    db.migrate()

    record = {
        "id": "run1",
        "workflow_id": "wf1",
        "status": "success",
        "started_at": "2025-01-01T00:00:00Z",
        "ended_at": "2025-01-01T00:00:10Z",
        "summary": "OK",
        "extra": {"count": 1},
    }
    db.log_run(record)

    runs = db.list_runs()
    assert len(runs) == 1
    assert runs[0]["status"] == "success"


def test_database_update_and_delete(tmp_path) -> None:
    db_path = tmp_path / "automation.db"
    db = Database()
    db.connect(str(db_path))
    db.migrate()

    workflow = {"id": "wf2", "name": "Temp Workflow", "steps": [{"type": "wait", "params": {"seconds": 1}}]}
    db.save_workflow(workflow)
    assert db.delete_workflow("wf2") is True
    assert db.get_workflow("wf2") is None

    record = {
        "id": "run2",
        "workflow_id": "wf1",
        "status": "running",
        "started_at": "2025-01-01T00:00:00Z",
        "ended_at": None,
        "summary": None,
        "extra": {"count": 1},
    }
    db.log_run(record)
    db.update_run("run2", status="success", ended_at="2025-01-01T00:00:10Z", summary="OK", data={"ok": True})
    loaded = db.get_run("run2")
    assert loaded is not None
    assert loaded["status"] == "success"
