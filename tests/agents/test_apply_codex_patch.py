"""Tests for apply_codex_patch.py"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.agents.apply_codex_patch import (
    BaseCommitMismatchError,
    PatchCheckError,
    ReviewRequiredError,
    apply,
    _check_base_commit,
    _check_review_policy,
)
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
def config_path(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[review]\ncodex_result_review = "always"\n'
        '[patch]\nbase_commit_policy = "warn"\n'
    )
    return cfg


def _seed_task(tasks_path, task_id="t-001", base_commit="", **kwargs):
    task = {"task_id": task_id, "base_commit": base_commit,
            "title": "T", "description": "D", "acceptance_criteria": [], **kwargs}
    upsert_task(task, path=tasks_path)
    return task


def _seed_run_meta(runs_dir, task_id, patch_path):
    write_run_metadata(task_id, {"artifacts": {"patch_path": str(patch_path)}},
                       runs_dir=runs_dir)


def _make_patch(git_repo, filename="new_file.py", content="x = 1\n"):
    """Add a file and produce a patch string, then reset so the patch is unapplied."""
    f = git_repo / filename
    f.write_text(content)
    subprocess.run(["git", "-C", str(git_repo), "add", filename],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(git_repo), "commit", "-m", "add file"],
                   check=True, capture_output=True)
    patch = subprocess.run(
        ["git", "-C", str(git_repo), "format-patch", "--stdout", "HEAD~1"],
        check=True, capture_output=True, text=True,
    ).stdout
    # Reset to before the commit so patch is not applied
    subprocess.run(["git", "-C", str(git_repo), "reset", "--hard", "HEAD~1"],
                   check=True, capture_output=True)
    return patch


# ---------------------------------------------------------------------------
# Review policy
# ---------------------------------------------------------------------------

def test_review_always_raises():
    with pytest.raises(ReviewRequiredError, match="always"):
        _check_review_policy("always")


def test_review_claude_decides_does_not_raise():
    _check_review_policy("claude_decides")  # should not raise


def test_review_unknown_raises():
    with pytest.raises(ReviewRequiredError):
        _check_review_policy("mystery_policy")


# ---------------------------------------------------------------------------
# Base-commit policy
# ---------------------------------------------------------------------------

def test_base_commit_ignore_no_raise(git_repo):
    task = {"task_id": "t", "base_commit": "deadbeef1234"}
    _check_base_commit(task, git_repo, "ignore")  # should not raise


def test_base_commit_warn_prints_warning(git_repo, capsys):
    task = {"task_id": "t", "base_commit": "deadbeef1234"}
    _check_base_commit(task, git_repo, "warn")
    captured = capsys.readouterr()
    assert "WARNING" in captured.err


def test_base_commit_require_raises(git_repo):
    task = {"task_id": "t", "base_commit": "deadbeef1234"}
    with pytest.raises(BaseCommitMismatchError):
        _check_base_commit(task, git_repo, "require")


def test_base_commit_match_no_raise(git_repo):
    head = subprocess.run(
        ["git", "-C", str(git_repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    task = {"task_id": "t", "base_commit": head}
    _check_base_commit(task, git_repo, "require")  # should not raise


def test_base_commit_empty_no_raise(git_repo):
    task = {"task_id": "t", "base_commit": ""}
    _check_base_commit(task, git_repo, "require")  # empty → skip check


# ---------------------------------------------------------------------------
# Missing task / run-meta → error
# ---------------------------------------------------------------------------

def test_apply_missing_task_raises(git_repo, tasks_path, runs_dir, config_path):
    with pytest.raises(KeyError):
        apply("t-001", force=True, repo_root=git_repo, tasks_path=tasks_path,
              runs_dir=runs_dir, config_path=config_path)


def test_apply_missing_run_meta_raises(git_repo, tasks_path, runs_dir, config_path):
    _seed_task(tasks_path)
    with pytest.raises(FileNotFoundError, match="run metadata"):
        apply("t-001", force=True, repo_root=git_repo, tasks_path=tasks_path,
              runs_dir=runs_dir, config_path=config_path)


def test_apply_missing_patch_file_raises(git_repo, tasks_path, runs_dir, config_path):
    _seed_task(tasks_path)
    _seed_run_meta(runs_dir, "t-001", runs_dir / "nonexistent.patch")
    with pytest.raises(FileNotFoundError, match="Patch file"):
        apply("t-001", force=True, repo_root=git_repo, tasks_path=tasks_path,
              runs_dir=runs_dir, config_path=config_path)


# ---------------------------------------------------------------------------
# Review gate: force=False raises, force=True bypasses
# ---------------------------------------------------------------------------

def test_apply_review_always_raises_without_force(git_repo, tasks_path, runs_dir, config_path):
    patch_text = _make_patch(git_repo)
    patch_path = runs_dir / "t-001.patch"
    patch_path.write_text(patch_text)
    _seed_task(tasks_path)
    _seed_run_meta(runs_dir, "t-001", patch_path)
    with pytest.raises(ReviewRequiredError):
        apply("t-001", force=False, repo_root=git_repo, tasks_path=tasks_path,
              runs_dir=runs_dir, config_path=config_path)


# ---------------------------------------------------------------------------
# Happy path: apply succeeds, status → applied
# ---------------------------------------------------------------------------

def test_apply_happy_path(git_repo, tasks_path, runs_dir, config_path):
    patch_text = _make_patch(git_repo)
    patch_path = runs_dir / "t-001.patch"
    patch_path.write_text(patch_text)
    _seed_task(tasks_path)
    _seed_run_meta(runs_dir, "t-001", patch_path)

    result = apply("t-001", force=True, repo_root=git_repo, tasks_path=tasks_path,
                   runs_dir=runs_dir, config_path=config_path)

    assert result["status"] == "applied"
    assert result["error"] is None
    task = get_task("t-001", path=tasks_path)
    assert task["status"] == "applied"


# ---------------------------------------------------------------------------
# Bad patch → PatchCheckError, status unchanged
# ---------------------------------------------------------------------------

def test_apply_bad_patch_raises(git_repo, tasks_path, runs_dir, config_path):
    patch_path = runs_dir / "t-001.patch"
    patch_path.write_text("this is not a valid patch\n")
    _seed_task(tasks_path)
    _seed_run_meta(runs_dir, "t-001", patch_path)
    with pytest.raises(PatchCheckError):
        apply("t-001", force=True, repo_root=git_repo, tasks_path=tasks_path,
              runs_dir=runs_dir, config_path=config_path)


# ---------------------------------------------------------------------------
# Validation commands: failure → status=failed
# ---------------------------------------------------------------------------

def test_apply_validation_failure_sets_failed_status(git_repo, tasks_path, runs_dir, config_path):
    patch_text = _make_patch(git_repo)
    patch_path = runs_dir / "t-001.patch"
    patch_path.write_text(patch_text)
    _seed_task(tasks_path, validation_commands=["exit 1"])
    _seed_run_meta(runs_dir, "t-001", patch_path)

    result = apply("t-001", force=True, repo_root=git_repo, tasks_path=tasks_path,
                   runs_dir=runs_dir, config_path=config_path)

    assert result["status"] == "failed"
    assert result["error"] is not None
    task = get_task("t-001", path=tasks_path)
    assert task["status"] == "failed"


def test_apply_validation_success(git_repo, tasks_path, runs_dir, config_path):
    patch_text = _make_patch(git_repo)
    patch_path = runs_dir / "t-001.patch"
    patch_path.write_text(patch_text)
    _seed_task(tasks_path, validation_commands=["echo ok"])
    _seed_run_meta(runs_dir, "t-001", patch_path)

    result = apply("t-001", force=True, repo_root=git_repo, tasks_path=tasks_path,
                   runs_dir=runs_dir, config_path=config_path)

    assert result["status"] == "applied"
    assert result["validation_results"][0]["returncode"] == 0
