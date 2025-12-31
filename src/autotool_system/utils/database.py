from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json
import sqlite3


class DatabaseError(RuntimeError):
    pass


class Database:
    def __init__(self, path: str | None = None) -> None:
        self._path = Path(path) if path else None
        self._conn: sqlite3.Connection | None = None

    def connect(self, path: str | None = None) -> None:
        if path is not None:
            self._path = Path(path)
        if self._path is None:
            raise DatabaseError("Database path is required")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row

    def migrate(self) -> None:
        conn = self._ensure_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_records (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                summary TEXT,
                data TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    def save_workflow(self, workflow: dict[str, Any]) -> None:
        conn = self._ensure_conn()
        workflow_id = workflow.get("id")
        name = workflow.get("name")
        if not workflow_id or not name:
            raise DatabaseError("workflow requires id and name")
        payload = json.dumps(workflow, ensure_ascii=True)
        conn.execute(
            """
            INSERT INTO workflows (id, name, data)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                data = excluded.data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (workflow_id, name, payload),
        )
        conn.commit()

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        conn = self._ensure_conn()
        row = conn.execute(
            "SELECT id, name, data, created_at, updated_at FROM workflows WHERE id = ?",
            (workflow_id,),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["data"])
        payload.setdefault("id", row["id"])
        payload.setdefault("name", row["name"])
        payload["created_at"] = row["created_at"]
        payload["updated_at"] = row["updated_at"]
        return payload

    def list_workflows(self) -> list[dict[str, Any]]:
        conn = self._ensure_conn()
        rows = conn.execute(
            "SELECT id, name, data, created_at, updated_at FROM workflows ORDER BY updated_at DESC"
        ).fetchall()
        return [self._row_to_workflow(row) for row in rows]

    def log_run(self, record: dict[str, Any]) -> None:
        conn = self._ensure_conn()
        record_id = record.get("id")
        if not record_id:
            raise DatabaseError("run record requires id")
        payload = json.dumps(record, ensure_ascii=True)
        conn.execute(
            """
            INSERT INTO run_records (id, workflow_id, status, started_at, ended_at, summary, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                record.get("workflow_id"),
                record.get("status"),
                record.get("started_at"),
                record.get("ended_at"),
                record.get("summary"),
                payload,
            ),
        )
        conn.commit()

    def update_run(
        self,
        record_id: str,
        *,
        status: str | None = None,
        ended_at: str | None = None,
        summary: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        conn = self._ensure_conn()
        if not record_id:
            raise DatabaseError("run record requires id")
        payload = json.dumps(data, ensure_ascii=True) if data is not None else None
        conn.execute(
            """
            UPDATE run_records
            SET status = COALESCE(?, status),
                ended_at = COALESCE(?, ended_at),
                summary = COALESCE(?, summary),
                data = COALESCE(?, data)
            WHERE id = ?
            """,
            (status, ended_at, summary, payload, record_id),
        )
        conn.commit()

    def get_run(self, record_id: str) -> dict[str, Any] | None:
        conn = self._ensure_conn()
        row = conn.execute(
            """
            SELECT id, workflow_id, status, started_at, ended_at, summary, data
            FROM run_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_run(row)

    def list_runs(self, workflow_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._ensure_conn()
        if workflow_id:
            rows = conn.execute(
                """
                SELECT id, workflow_id, status, started_at, ended_at, summary, data
                FROM run_records
                WHERE workflow_id = ?
                ORDER BY started_at DESC
                """,
                (workflow_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, workflow_id, status, started_at, ended_at, summary, data
                FROM run_records
                ORDER BY started_at DESC
                """
            ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def delete_workflow(self, workflow_id: str) -> bool:
        conn = self._ensure_conn()
        cursor = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def backup(self, path: str) -> None:
        conn = self._ensure_conn()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_conn = sqlite3.connect(target)
        conn.backup(backup_conn)
        backup_conn.close()

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise DatabaseError("Database is not connected")
        return self._conn

    def _row_to_workflow(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["data"])
        payload.setdefault("id", row["id"])
        payload.setdefault("name", row["name"])
        payload["created_at"] = row["created_at"]
        payload["updated_at"] = row["updated_at"]
        return payload

    def _row_to_run(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["data"]) if row["data"] else {}
        payload.update(
            {
                "id": row["id"],
                "workflow_id": row["workflow_id"],
                "status": row["status"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "summary": row["summary"],
            }
        )
        return payload
