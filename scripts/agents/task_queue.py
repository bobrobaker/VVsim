"""Task queue helpers for Route B (Claude → Codex sync flow).

Single-dispatch only; no multi-worker locking. Atomic save via write-then-rename.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASKS_PATH = Path(".agents/tasks.json")
RUNS_DIR = Path(".agents/runs")

VALID_STATUSES = frozenset({
    "ready",
    "running",
    "result_ready",
    "applied",
    "failed",
    "needs_input",
    "cleaned",
})


# ---------------------------------------------------------------------------
# Low-level ledger I/O
# ---------------------------------------------------------------------------

def load_tasks(path: Path = TASKS_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}, got {type(data).__name__}")
    return data


def save_tasks(tasks: list[dict], path: Path = TASKS_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(tasks, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------

def upsert_task(task: dict, path: Path = TASKS_PATH) -> None:
    """Insert or replace a task by task_id."""
    if "task_id" not in task:
        raise ValueError("task must have a 'task_id' field")
    tasks = load_tasks(path)
    idx = next((i for i, t in enumerate(tasks) if t.get("task_id") == task["task_id"]), None)
    if idx is None:
        tasks.append(task)
    else:
        tasks[idx] = task
    save_tasks(tasks, path)


def get_task(task_id: str, path: Path = TASKS_PATH) -> dict | None:
    """Return the task dict for task_id, or None if not found."""
    for task in load_tasks(path):
        if task.get("task_id") == task_id:
            return task
    return None


def update_task_status(task_id: str, status: str, path: Path = TASKS_PATH) -> dict:
    """Set task['status'] and record a status_updated_at timestamp. Returns updated task."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status {status!r}. Valid: {sorted(VALID_STATUSES)}")
    tasks = load_tasks(path)
    for task in tasks:
        if task.get("task_id") == task_id:
            task["status"] = status
            task["status_updated_at"] = _now_iso()
            save_tasks(tasks, path)
            return task
    raise KeyError(f"task_id {task_id!r} not found in {path}")


# ---------------------------------------------------------------------------
# Run metadata helpers
# ---------------------------------------------------------------------------

def write_run_metadata(task_id: str, data: dict[str, Any], runs_dir: Path = RUNS_DIR) -> Path:
    """Write run metadata to .agents/runs/<task_id>.run.json. Returns the path written."""
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = runs_dir / f"{task_id}.run.json"
    tmp = run_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, run_path)
    return run_path


def read_run_metadata(task_id: str, runs_dir: Path = RUNS_DIR) -> dict | None:
    """Read run metadata for task_id. Returns None if not found."""
    run_path = Path(runs_dir) / f"{task_id}.run.json"
    if not run_path.exists():
        return None
    with open(run_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
