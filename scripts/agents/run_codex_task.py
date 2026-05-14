"""Route B synchronous runner: create worktree, run Codex (or dry-run), write result.

Usage:
    python3 scripts/agents/run_codex_task.py --task-id <id> [--dry-run] [--codex-bin <path>] [--repo-root <path>]

The task must already exist in .agents/tasks.json. Use --dry-run for tests and
local development; it emits a canned result without requiring Codex auth.

Codex invocation (non-dry-run):
    codex exec -C <worktree> -s workspace-write -o <result_file> [--output-schema <schema>] -
    Prompt is piped via stdin. Result is captured by -o; Codex must NOT manually write
    the result artifact. The harness reads result_file after Codex exits.
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


def _build_prompt(task: dict) -> str:
    lines = [
        f"# Task: {task['title']}",
        "",
        "## ImplementationTask",
        "",
        "```json",
        json.dumps(task, indent=2),
        "```",
        "",
        task["description"],
        "",
    ]

    criteria = task.get("acceptance_criteria") or []
    if criteria:
        lines.append("## Acceptance criteria")
        for c in criteria:
            lines.append(f"- {c}")
        lines.append("")

    off_limits = task.get("files_off_limits") or []
    if off_limits:
        lines.append("## Files off-limits (do not modify)")
        for f in off_limits:
            lines.append(f"- {f}")
        lines.append("")

    validation = task.get("validation_commands") or []
    if validation:
        lines.append("## Validation commands")
        for cmd in validation:
            lines.append(f"- `{cmd}`")
        lines.append("")

    lines += [
        "## Output",
        "Return your final answer as raw JSON matching ImplementationResult.",
        "Do not wrap in markdown. Do not manually write the result artifact;",
        "`codex exec --output-last-message / -o` captures your final response.",
    ]
    return "\n".join(lines)


def _run_codex(task: dict, codex_bin: str, worktree_path: Path) -> dict:
    worktree_path = Path(worktree_path).resolve()  # absolute so -o and -C are unambiguous
    safe = _safe_name(task["task_id"])
    result_file = worktree_path / f"codex_result_{safe}.json"
    schema_path = worktree_path / ".agents" / "schemas" / "implementation_result.json"

    prompt = _build_prompt(task)

    cmd = [
        codex_bin, "exec",
        "-C", str(worktree_path),
        "-s", "workspace-write",
        "-o", str(result_file),
    ]
    if schema_path.exists():
        cmd += ["--output-schema", str(schema_path)]
    cmd.append("-")  # read prompt from stdin

    proc = subprocess.run(
        cmd,
        input=prompt,
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return {
            "task_id": task["task_id"],
            "status": "failed",
            "summary": f"Codex exited with code {proc.returncode}",
            "issues": [proc.stderr.strip() or proc.stdout.strip()],
            "completed_at": _now_iso(),
            "metadata": {"exit_code": proc.returncode},
        }

    if not result_file.exists():
        return {
            "task_id": task["task_id"],
            "status": "failed",
            "summary": "Codex produced no result file (expected via -o / --output-last-message)",
            "issues": [proc.stdout[:500]] if proc.stdout.strip() else [],
            "completed_at": _now_iso(),
            "metadata": {},
        }

    try:
        result = json.loads(result_file.read_text())
    except json.JSONDecodeError as e:
        return {
            "task_id": task["task_id"],
            "status": "failed",
            "summary": "Result file was not valid JSON",
            "issues": [str(e), result_file.read_text()[:500]],
            "completed_at": _now_iso(),
            "metadata": {},
        }

    if "status" not in result:
        result["status"] = "success"
    if "task_id" not in result:
        result["task_id"] = task["task_id"]

    return result


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


# Directories/files that Codex reads from the worktree for protocol behaviour.
# Uncommitted changes here won't reach the worktree and will silently stale Codex.
_PROTOCOL_PATHS = (
    ".agents/schemas/",
    ".agents/skills/",
    ".agents/config.toml",
    ".claude/skills/",
    "AGENTS.md",
    "scripts/agents/",
    "tests/agents/",
)


def _warn_protocol_staleness(repo_root: Path) -> None:
    """Warn if uncommitted working-tree changes touch Route B protocol files.

    The worktree is created from HEAD; any uncommitted edits to protocol files
    won't be present, so Codex may run against stale schemas or instructions.
    """
    proc = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return  # not a git repo or git unavailable; skip silently
    dirty = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    stale = [f for f in dirty if any(f.startswith(p) for p in _PROTOCOL_PATHS)]
    if stale:
        print(
            "WARNING: uncommitted changes to Route B protocol files will NOT be present "
            "in the Codex worktree. Commit them before running to avoid stale behaviour.\n"
            "  Stale files: " + ", ".join(stale),
            file=sys.stderr,
        )


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

    _warn_protocol_staleness(repo_root)
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
    parser.add_argument(
        "--reset-status",
        metavar="STATUS",
        help="Reset task status to STATUS and exit (no Codex run). "
             "Valid: applied, cleaned, failed, needs_input, ready, result_ready, running",
    )
    args = parser.parse_args()

    if args.reset_status:
        try:
            task = update_task_status(
                args.task_id,
                args.reset_status,
                path=Path(".agents/tasks.json"),
            )
        except (KeyError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps({"task_id": task["task_id"], "status": task["status"]}, indent=2))
        return

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
