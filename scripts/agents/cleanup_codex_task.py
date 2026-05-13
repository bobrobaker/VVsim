"""Remove worktree, branch, lock, and status files for a completed Codex task.

Preserves result/diff/patch/events/run metadata by default.
Pass delete_artifacts=True to remove those too.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.agents.run_codex_task import WORKTREES_DIR, _safe_name
from scripts.agents.task_queue import (
    RUNS_DIR,
    TASKS_PATH,
    get_task,
    read_run_metadata,
    update_task_status,
)

LOCKS_DIR = Path(".agents/locks")

# Artifact suffixes preserved by default
_ARTIFACT_SUFFIXES = (".run.json", ".diff", ".patch", ".result.json")
# Events file pattern (matches <id>.events.jsonl if present)
_EVENTS_SUFFIX = ".events.jsonl"


def cleanup(
    task_id: str,
    *,
    delete_artifacts: bool = False,
    repo_root: Path | None = None,
    tasks_path: Path = TASKS_PATH,
    runs_dir: Path = RUNS_DIR,
    locks_dir: Path = LOCKS_DIR,
    worktrees_dir: Path | None = None,
) -> dict:
    """Remove worktree/branch/lock for task_id. Returns a summary dict.

    Safe to rerun: missing paths are skipped, not errors.
    """
    repo_root = Path(repo_root) if repo_root else Path.cwd()
    runs_dir = Path(runs_dir)
    locks_dir = Path(locks_dir)
    wt_dir = Path(worktrees_dir) if worktrees_dir else repo_root / WORKTREES_DIR

    safe_id = _safe_name(task_id)
    worktree_path = wt_dir / safe_id
    branch_name = f"codex/{safe_id}"
    lock_path = locks_dir / f"{safe_id}.lock"

    removed = []
    skipped = []
    errors = []

    # 1. Remove worktree (git worktree remove is safe even if not registered)
    if worktree_path.exists():
        result = subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            removed.append(str(worktree_path))
        else:
            errors.append(f"worktree remove: {result.stderr.strip()}")
    else:
        skipped.append(str(worktree_path))

    # 2. Delete branch
    result = subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        removed.append(branch_name)
    else:
        # Branch may not exist; treat as skipped
        skipped.append(branch_name)

    # 3. Remove lock file
    if lock_path.exists():
        lock_path.unlink()
        removed.append(str(lock_path))
    else:
        skipped.append(str(lock_path))

    # 4. Remove artifacts if requested
    if delete_artifacts:
        for suffix in _ARTIFACT_SUFFIXES + (_EVENTS_SUFFIX,):
            artifact = runs_dir / f"{safe_id}{suffix}"
            if artifact.exists():
                artifact.unlink()
                removed.append(str(artifact))
            else:
                skipped.append(str(artifact))

    # 5. Update task status to cleaned (best-effort; task may not exist)
    try:
        task = get_task(task_id, path=tasks_path)
        if task is not None:
            update_task_status(task_id, "cleaned", path=tasks_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"status update: {exc}")

    return {
        "task_id": task_id,
        "removed": removed,
        "skipped": skipped,
        "errors": errors,
        "artifacts_deleted": delete_artifacts,
    }
