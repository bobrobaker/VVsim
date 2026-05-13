"""Route B synchronous runner: create worktree, run Codex (or dry-run), write result.

Usage:
    python3 scripts/agents/run_codex_task.py --task-id <id> [--dry-run] [--codex-bin <path>] [--repo-root <path>]

The task must already exist in .agents/tasks.json. Use --dry-run for tests and
local development; it emits a canned result without requiring Codex auth.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a script from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.agents.task_queue import (
    get_task,
    update_task_status,
    upsert_task,
    write_run_metadata,
)

WORKTREES_DIR = Path(".agents/worktrees")
HANDOFFS_DIR = Path(".agents/handoffs/claude_to_codex")
CODEX_TO_CLAUDE_DIR = Path(".agents/handoffs/codex_to_claude")
RUNS_DIR = Path(".agents/runs")


def _safe_name(task_id: str) -> str:
    """Sanitize task_id for use as a branch/directory name."""
    return re.sub(r"[^a-zA-Z0-9._-]", "-", task_id)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_commit(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _create_worktree(task_id: str, repo_root: Path) -> Path:
    safe = _safe_name(task_id)
    worktree_path = repo_root / WORKTREES_DIR / safe
    branch = f"codex/{safe}"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path)],
        cwd=repo_root,
        check=True,
    )
    return worktree_path


def _write_task_artifact(task: dict, worktree_path: Path) -> None:
    dest_dir = worktree_path / HANDOFFS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_name(task["task_id"])
    dest = dest_dir / f"task_{safe}.json"
    dest.write_text(json.dumps(task, indent=2) + "\n")


def _run_dry(task: dict) -> dict:
    return {
        "task_id": task["task_id"],
        "status": "success",
        "summary": "[dry-run] No real Codex execution. Simulated success.",
        "files_changed": [],
        "validation_results": [],
        "issues": [],
        "proposed_followup_tasks": [],
        "completed_at": _now_iso(),
        "metadata": {"dry_run": True},
    }


def _run_codex(task: dict, codex_bin: str, worktree_path: Path) -> dict:
    task_file = worktree_path / HANDOFFS_DIR / f"task_{task['task_id']}.json"
    proc = subprocess.run(
        [codex_bin, "--task-file", str(task_file)],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {
            "task_id": task["task_id"],
            "status": "failed",
            "summary": f"Codex exited with code {proc.returncode}",
            "issues": [proc.stderr.strip()],
            "completed_at": _now_iso(),
            "metadata": {"exit_code": proc.returncode},
        }
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {
            "task_id": task["task_id"],
            "status": "failed",
            "summary": "Codex output was not valid JSON",
            "issues": [str(e), proc.stdout[:500]],
            "completed_at": _now_iso(),
            "metadata": {},
        }


def _capture_diff(safe_id: str, worktree_path: Path, base_commit: str, runs_dir: Path) -> Path:
    proc = subprocess.run(
        ["git", "diff", f"{base_commit}..HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    diff_path = runs_dir / f"{safe_id}.diff"
    diff_path.write_text(proc.stdout)
    return diff_path


def _capture_patch(safe_id: str, worktree_path: Path, base_commit: str, runs_dir: Path) -> Path:
    proc = subprocess.run(
        ["git", "format-patch", "--stdout", base_commit],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    patch_path = runs_dir / f"{safe_id}.patch"
    patch_path.write_text(proc.stdout)
    return patch_path


def _copy_result(safe_id: str, result: dict, repo_root: Path) -> Path:
    dest_dir = repo_root / CODEX_TO_CLAUDE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"result_{safe_id}.json"
    dest.write_text(json.dumps(result, indent=2) + "\n")
    return dest


def _changed_files_from_diff(diff_text: str) -> list[str]:
    files = []
    for line in diff_text.splitlines():
        m = re.match(r"^diff --git a/.+ b/(.+)$", line)
        if m:
            files.append(m.group(1))
    return files


def run(
    task_id: str,
    *,
    dry_run: bool = False,
    codex_bin: str = "codex",
    repo_root: Path = Path("."),
    tasks_path: Path = Path(".agents/tasks.json"),
) -> dict:
    """Execute one task. Returns the result dict. Raises on missing task or git errors."""
    repo_root = Path(repo_root)

    task = get_task(task_id, path=tasks_path)
    if task is None:
        raise KeyError(f"task_id {task_id!r} not found in {tasks_path}. Add it to the ledger first.")

    # Record base_commit at dispatch time if not already set.
    if not task.get("base_commit"):
        task["base_commit"] = _current_commit(repo_root)
        upsert_task(task, path=tasks_path)

    update_task_status(task_id, "running", path=tasks_path)

    worktree_path = _create_worktree(task_id, repo_root)
    _write_task_artifact(task, worktree_path)

    try:
        if dry_run:
            result = _run_dry(task)
        else:
            result = _run_codex(task, codex_bin, worktree_path)
    except Exception as exc:
        result = {
            "task_id": task_id,
            "status": "failed",
            "summary": f"Runner exception: {exc}",
            "completed_at": _now_iso(),
            "metadata": {},
        }

    safe_id = _safe_name(task_id)
    runs_dir = repo_root / RUNS_DIR
    runs_dir.mkdir(parents=True, exist_ok=True)

    diff_path = _capture_diff(safe_id, worktree_path, task["base_commit"], runs_dir)
    patch_path = _capture_patch(safe_id, worktree_path, task["base_commit"], runs_dir)
    result_path = _copy_result(safe_id, result, repo_root)

    diff_text = diff_path.read_text()
    changed_files_actual = _changed_files_from_diff(diff_text)
    reported_files = result.get("files_changed") or []
    files_mismatch = sorted(reported_files) != sorted(changed_files_actual)

    write_run_metadata(
        safe_id,
        {
            "task_id": task_id,
            "worktree_path": str(worktree_path),
            "base_commit": task["base_commit"],
            "dry_run": dry_run,
            "result": result,
            "result_path": str(result_path),
            "diff_path": str(diff_path),
            "patch_path": str(patch_path),
            "changed_files_actual": changed_files_actual,
            "files_changed_mismatch": files_mismatch,
            "run_at": _now_iso(),
        },
        runs_dir=runs_dir,
    )

    final_status = "result_ready" if result.get("status") in ("success", "partial") else "failed"
    update_task_status(task_id, final_status, path=tasks_path)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single Codex task (Route B).")
    parser.add_argument("--task-id", required=True, help="Task ID from .agents/tasks.json")
    parser.add_argument("--dry-run", action="store_true", help="Simulate Codex without auth")
    parser.add_argument("--codex-bin", default="codex", help="Path to Codex binary")
    parser.add_argument("--repo-root", default=".", help="Repo root (default: cwd)")
    args = parser.parse_args()

    try:
        result = run(
            args.task_id,
            dry_run=args.dry_run,
            codex_bin=args.codex_bin,
            repo_root=Path(args.repo_root),
        )
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
