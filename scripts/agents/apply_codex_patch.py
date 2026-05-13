"""Apply a Codex-produced patch to the main checkout after review-policy checks.

Route B post-execution step: reads config, enforces review/base-commit policy,
runs git apply, executes validation commands, and updates task status.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-reattr]

from scripts.agents.task_queue import (
    RUNS_DIR,
    TASKS_PATH,
    get_task,
    read_run_metadata,
    update_task_status,
)

CONFIG_PATH = Path(".agents/config.toml")


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_config(config_path: Path = CONFIG_PATH) -> dict:
    config_path = Path(config_path)
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def _review_policy(cfg: dict) -> str:
    return cfg.get("review", {}).get("codex_result_review", "always")


def _base_commit_policy(cfg: dict) -> str:
    return cfg.get("patch", {}).get("base_commit_policy", "warn")


# ---------------------------------------------------------------------------
# Policy checks
# ---------------------------------------------------------------------------

def _check_review_policy(policy: str) -> None:
    """Raise if policy blocks automated apply."""
    if policy == "always":
        raise ReviewRequiredError(
            "review.codex_result_review=always: human review required before apply. "
            "Pass --force to override."
        )
    # "claude_decides" and "manual_only" are future values; treat unknown as always.
    if policy not in ("claude_decides",):
        raise ReviewRequiredError(
            f"Unknown review policy {policy!r}; treating as 'always'. "
            "Pass --force to override."
        )


def _check_base_commit(task: dict, repo_root: Path, policy: str) -> None:
    """Warn or refuse if HEAD differs from task's base_commit."""
    base = task.get("base_commit", "")
    if not base:
        return
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    head = result.stdout.strip()
    if head == base:
        return
    msg = (
        f"HEAD ({head[:12]}) differs from task base_commit ({base[:12]}). "
        "Patch may not apply cleanly."
    )
    if policy == "ignore":
        return
    if policy == "warn":
        print(f"WARNING: {msg}", file=sys.stderr)
        return
    # "require" or unknown → refuse
    raise BaseCommitMismatchError(msg)


# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------

def _git_apply_check(patch_path: Path, repo_root: Path) -> None:
    """Run git apply --check; raise PatchCheckError on failure."""
    result = subprocess.run(
        ["git", "apply", "--check", str(patch_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise PatchCheckError(
            f"git apply --check failed:\n{result.stderr.strip()}"
        )


def _git_apply(patch_path: Path, repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "apply", str(patch_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise PatchApplyError(
            f"git apply failed:\n{result.stderr.strip()}"
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _run_validation(commands: list[str], repo_root: Path) -> list[dict]:
    results = []
    for cmd in commands:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        results.append({
            "command": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        })
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def apply(
    task_id: str,
    *,
    force: bool = False,
    repo_root: Path | None = None,
    tasks_path: Path = TASKS_PATH,
    runs_dir: Path = RUNS_DIR,
    config_path: Path = CONFIG_PATH,
) -> dict:
    """Apply patch for task_id to repo_root.

    Returns a result dict with keys: task_id, status, validation_results, error.
    Raises ReviewRequiredError unless force=True.
    """
    repo_root = Path(repo_root) if repo_root else Path.cwd()
    cfg = _load_config(config_path)

    task = get_task(task_id, path=tasks_path)
    if task is None:
        raise KeyError(f"task_id {task_id!r} not found in {tasks_path}")

    run_meta = read_run_metadata(task_id, runs_dir=runs_dir)
    if run_meta is None:
        raise FileNotFoundError(f"No run metadata found for task {task_id!r}")

    raw_patch = run_meta.get("patch_path") or run_meta.get("artifacts", {}).get("patch_path", "")
    patch_path = Path(raw_patch)
    if not patch_path.exists():
        raise FileNotFoundError(f"Patch file not found: {patch_path}")

    # Review policy gate
    review_pol = _review_policy(cfg)
    if not force:
        _check_review_policy(review_pol)

    # Base-commit check
    base_pol = _base_commit_policy(cfg)
    _check_base_commit(task, repo_root, base_pol)

    # Empty patch means no changes; skip apply
    if patch_path.stat().st_size == 0:
        update_task_status(task_id, "applied", path=tasks_path)
        return {"task_id": task_id, "status": "applied", "validation_results": [], "error": None, "note": "empty patch, nothing to apply"}

    # Dry-run patch check
    _git_apply_check(patch_path, repo_root)

    # Apply
    try:
        _git_apply(patch_path, repo_root)
    except PatchApplyError as e:
        update_task_status(task_id, "failed", path=tasks_path)
        return {"task_id": task_id, "status": "failed", "validation_results": [], "error": str(e)}

    # Validation
    validation_cmds = task.get("validation_commands", [])
    val_results = _run_validation(validation_cmds, repo_root)
    failed_cmds = [r for r in val_results if r["returncode"] != 0]

    if failed_cmds:
        update_task_status(task_id, "failed", path=tasks_path)
        return {
            "task_id": task_id,
            "status": "failed",
            "validation_results": val_results,
            "error": f"{len(failed_cmds)} validation command(s) failed",
        }

    update_task_status(task_id, "applied", path=tasks_path)
    return {"task_id": task_id, "status": "applied", "validation_results": val_results, "error": None}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ReviewRequiredError(RuntimeError):
    pass


class BaseCommitMismatchError(RuntimeError):
    pass


class PatchCheckError(RuntimeError):
    pass


class PatchApplyError(RuntimeError):
    pass
