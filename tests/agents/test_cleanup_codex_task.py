"""Tests for cleanup_codex_task.py"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.agents.cleanup_codex_task import cleanup
from scripts.agents.task_queue import get_task, upsert_task, write_run_metadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t.com"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "T"],
                   check=True, capture_output=True)
    readme = tmp_path / "README.md"
    readme.write_text("init\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "init"],
                   check=True, capture_output=True)
    return tmp_path


@pytest.fixture
def tasks_path(tmp_path):
    return tmp_path / "tasks.json"


@pytest.fixture
def runs_dir(tmp_path):
    d = tmp_path / "runs"
    d.mkdir()
    return d


@pytest.fixture
def locks_dir(tmp_path):
    d = tmp_path / "locks"
    d.mkdir()
    return d


def _seed_task(tasks_path, task_id="t-001"):
    task = {"task_id": task_id, "base_commit": "", "title": "T",
            "description": "D", "acceptance_criteria": []}
    upsert_task(task, path=tasks_path)
    return task


def _make_worktree(git_repo, safe_id="t-001"):
    wt_dir = git_repo / ".agents" / "worktrees"
    wt_dir.mkdir(parents=True, exist_ok=True)
    wt_path = wt_dir / safe_id
    branch = f"codex/{safe_id}"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(wt_path)],
        cwd=git_repo, check=True, capture_output=True,
    )
    return wt_path, branch


# ---------------------------------------------------------------------------
# No-op when nothing exists
# ---------------------------------------------------------------------------

def test_cleanup_no_worktree_no_error(git_repo, tasks_path, runs_dir, locks_dir):
    result = cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
                     runs_dir=runs_dir, locks_dir=locks_dir)
    assert result["task_id"] == "t-001"
    assert result["errors"] == []


def test_cleanup_idempotent(git_repo, tasks_path, runs_dir, locks_dir):
    """Second cleanup call on already-cleaned task does not raise."""
    cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
            runs_dir=runs_dir, locks_dir=locks_dir)
    cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
            runs_dir=runs_dir, locks_dir=locks_dir)


# ---------------------------------------------------------------------------
# Worktree removal
# ---------------------------------------------------------------------------

def test_cleanup_removes_worktree(git_repo, tasks_path, runs_dir, locks_dir):
    wt_path, _ = _make_worktree(git_repo)
    assert wt_path.exists()

    result = cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
                     runs_dir=runs_dir, locks_dir=locks_dir,
                     worktrees_dir=wt_path.parent)
    assert not wt_path.exists()
    assert str(wt_path) in result["removed"]


def test_cleanup_removes_branch(git_repo, tasks_path, runs_dir, locks_dir):
    _make_worktree(git_repo)
    branches_before = subprocess.run(
        ["git", "-C", str(git_repo), "branch"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "codex/t-001" in branches_before

    wt_dir = git_repo / ".agents" / "worktrees"
    cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
            runs_dir=runs_dir, locks_dir=locks_dir, worktrees_dir=wt_dir)

    branches_after = subprocess.run(
        ["git", "-C", str(git_repo), "branch"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "codex/t-001" not in branches_after


# ---------------------------------------------------------------------------
# Lock file removal
# ---------------------------------------------------------------------------

def test_cleanup_removes_lock(git_repo, tasks_path, runs_dir, locks_dir):
    lock = locks_dir / "t-001.lock"
    lock.write_text("")
    result = cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
                     runs_dir=runs_dir, locks_dir=locks_dir)
    assert not lock.exists()
    assert str(lock) in result["removed"]


# ---------------------------------------------------------------------------
# Artifact preservation and deletion
# ---------------------------------------------------------------------------

def test_cleanup_preserves_artifacts_by_default(git_repo, tasks_path, runs_dir, locks_dir):
    for suffix in (".run.json", ".diff", ".patch", ".result.json"):
        (runs_dir / f"t-001{suffix}").write_text("data")

    cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
            runs_dir=runs_dir, locks_dir=locks_dir)

    for suffix in (".run.json", ".diff", ".patch", ".result.json"):
        assert (runs_dir / f"t-001{suffix}").exists()


def test_cleanup_deletes_artifacts_when_requested(git_repo, tasks_path, runs_dir, locks_dir):
    for suffix in (".run.json", ".diff", ".patch", ".result.json"):
        (runs_dir / f"t-001{suffix}").write_text("data")

    result = cleanup("t-001", delete_artifacts=True, repo_root=git_repo,
                     tasks_path=tasks_path, runs_dir=runs_dir, locks_dir=locks_dir)

    for suffix in (".run.json", ".diff", ".patch", ".result.json"):
        assert not (runs_dir / f"t-001{suffix}").exists()
    assert result["artifacts_deleted"] is True


# ---------------------------------------------------------------------------
# Task status → cleaned
# ---------------------------------------------------------------------------

def test_cleanup_sets_status_cleaned(git_repo, tasks_path, runs_dir, locks_dir):
    _seed_task(tasks_path)
    cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
            runs_dir=runs_dir, locks_dir=locks_dir)
    task = get_task("t-001", path=tasks_path)
    assert task["status"] == "cleaned"


def test_cleanup_no_task_no_error(git_repo, tasks_path, runs_dir, locks_dir):
    """cleanup is best-effort on status; missing task should not raise."""
    result = cleanup("t-001", repo_root=git_repo, tasks_path=tasks_path,
                     runs_dir=runs_dir, locks_dir=locks_dir)
    assert result["task_id"] == "t-001"
