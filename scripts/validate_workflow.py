from __future__ import annotations

import json
from pathlib import Path
import sys

from autotool_system.core.workflow_builder import WorkflowBuilder, WorkflowError


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_workflow.py <workflow.json>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Workflow file not found: {path}")
        return 1

    workflow = json.loads(path.read_text(encoding="utf-8"))
    builder = WorkflowBuilder()
    errors = builder.validate(workflow)
    if errors:
        print("Validation errors:")
        for err in errors:
            print(f"- {err}")
        return 2

    try:
        actions = builder.compile(workflow)
    except WorkflowError as exc:
        print(f"Compile failed: {exc}")
        return 3

    print(f"Validation passed. Actions: {len(actions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
