import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.agents.run_codex_task import _safe_name, _warn_protocol_staleness, main, run
from scripts.agents.task_queue import get_task, load_tasks, read_run_metadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def git_repo(tmp_path):
    """Minimal git repo with one commit — required for git worktree add."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"],
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


def _task(task_id="t-001", base_commit="abc123def456", **kwargs):
    return {
        "task_id": task_id,
        "base_commit": base_commit,
        "title": "Test task",
        "description": "Implement something.",
        "acceptance_criteria": ["Tests pass"],
        **kwargs,
    }


def _seed_task(tasks_path, task):
    from scripts.agents.task_queue import upsert_task
    upsert_task(task, path=tasks_path)


# ---------------------------------------------------------------------------
# _safe_name
# ---------------------------------------------------------------------------

def test_safe_name_alphanumeric():
    assert _safe_name("task-001") == "task-001"


def test_safe_name_spaces_and_slashes():
    assert _safe_name("task 01/sub") == "task-01-sub"


def test_safe_name_dots_preserved():
    assert _safe_name("task.001") == "task.001"


# ---------------------------------------------------------------------------
# Missing task → fail fast
# ---------------------------------------------------------------------------

def test_run_missing_task_raises(git_repo, tasks_path):
    with pytest.raises(KeyError, match="not found in"):
        run("nonexistent", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)


def test_run_empty_ledger_raises(git_repo, tasks_path):
    tasks_path.write_text("[]\n")
    with pytest.raises(KeyError):
        run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)


# ---------------------------------------------------------------------------
# Dry-run happy path
# ---------------------------------------------------------------------------

def test_dry_run_returns_success_result(git_repo, tasks_path):
    _seed_task(tasks_path, _task())
    result = run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    assert result["status"] == "success"
    assert result["metadata"]["dry_run"] is True
    assert result["task_id"] == "t-001"


def test_dry_run_creates_worktree(git_repo, tasks_path):
    _seed_task(tasks_path, _task())
    run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    worktree = git_repo / ".agents" / "worktrees" / "t-001"
    assert worktree.is_dir()


def test_dry_run_writes_task_artifact_in_worktree(git_repo, tasks_path):
    _seed_task(tasks_path, _task())
    run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    artifact = git_repo / ".agents" / "worktrees" / "t-001" / ".agents" / "handoffs" / "claude_to_codex" / "task_t-001.json"
    # safe_name("t-001") == "t-001" so filename is unchanged here
    assert artifact.exists()
    data = json.loads(artifact.read_text())
    assert data["task_id"] == "t-001"


def test_dry_run_writes_run_metadata(git_repo, tasks_path):
    runs_dir = git_repo / ".agents" / "runs"
    _seed_task(tasks_path, _task())
    run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    meta = read_run_metadata(_safe_name("t-001"), runs_dir=runs_dir)
    assert meta is not None
    assert meta["task_id"] == "t-001"
    assert meta["dry_run"] is True
    assert "worktree_path" in meta
    assert "base_commit" in meta


def test_dry_run_sets_status_result_ready(git_repo, tasks_path):
    _seed_task(tasks_path, _task())
    run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    task = get_task("t-001", path=tasks_path)
    assert task["status"] == "result_ready"


def test_dry_run_branch_name_uses_safe_task_id(git_repo, tasks_path):
    _seed_task(tasks_path, _task(task_id="task/with spaces"))
    run("task/with spaces", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    result = subprocess.run(
        ["git", "-C", str(git_repo), "branch", "--list", "codex/task-with-spaces"],
        capture_output=True, text=True,
    )
    assert "codex/task-with-spaces" in result.stdout


# ---------------------------------------------------------------------------
# base_commit auto-fill
# ---------------------------------------------------------------------------

def test_base_commit_filled_if_missing(git_repo, tasks_path):
    task = _task(base_commit="")
    _seed_task(tasks_path, task)
    run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    updated = get_task("t-001", path=tasks_path)
    assert len(updated["base_commit"]) == 40  # full SHA


def test_base_commit_preserved_if_set(git_repo, tasks_path):
    _seed_task(tasks_path, _task(base_commit="deadbeef" * 5))
    run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    updated = get_task("t-001", path=tasks_path)
    assert updated["base_commit"] == "deadbeef" * 5


# ---------------------------------------------------------------------------
# Fake codex binary (non-dry-run path)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_codex(tmp_path):
    """A fake codex binary: parses -o flag and writes a valid JSON result to that path."""
    result = {
        "task_id": "t-fake",
        "status": "success",
        "summary": "fake codex ran",
        "files_changed": [],
        "validation_results": [],
        "issues": [],
        "proposed_followup_tasks": [],
        "completed_at": "2026-01-01T00:00:00+00:00",
    }
    script = tmp_path / "fake_codex"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json\n"
        "args = sys.argv[1:]\n"
        "output_file = None\n"
        "i = 0\n"
        "while i < len(args):\n"
        "    if args[i] == '-o' and i + 1 < len(args):\n"
        "        output_file = args[i + 1]; i += 2\n"
        "    else:\n"
        "        i += 1\n"
        f"result = {json.dumps(result)}\n"
        "if output_file:\n"
        "    open(output_file, 'w').write(json.dumps(result))\n"
    )
    script.chmod(0o755)
    return str(script)


@pytest.fixture
def failing_codex(tmp_path):
    script = tmp_path / "failing_codex"
    script.write_text("#!/bin/sh\necho 'error output' >&2\nexit 1\n")
    script.chmod(0o755)
    return str(script)


def test_real_codex_path_success(git_repo, tasks_path, fake_codex):
    _seed_task(tasks_path, _task(task_id="t-fake"))
    result = run("t-fake", dry_run=False, codex_bin=fake_codex,
                 repo_root=git_repo, tasks_path=tasks_path)
    assert result["status"] == "success"
    task = get_task("t-fake", path=tasks_path)
    assert task["status"] == "result_ready"


def test_real_codex_path_failure(git_repo, tasks_path, failing_codex):
    _seed_task(tasks_path, _task(task_id="t-fail"))
    result = run("t-fail", dry_run=False, codex_bin=failing_codex,
                 repo_root=git_repo, tasks_path=tasks_path)
    assert result["status"] == "failed"
    task = get_task("t-fail", path=tasks_path)
    assert task["status"] == "failed"


def test_real_codex_no_result_file(git_repo, tasks_path, tmp_path):
    """Fake codex exits 0 but does not write to -o → harness reports failure."""
    no_result_codex = tmp_path / "no_result_codex"
    no_result_codex.write_text("#!/bin/sh\necho 'did nothing'\n")
    no_result_codex.chmod(0o755)
    _seed_task(tasks_path, _task(task_id="t-badjson"))
    result = run("t-badjson", dry_run=False, codex_bin=str(no_result_codex),
                 repo_root=git_repo, tasks_path=tasks_path)
    assert result["status"] == "failed"
    assert "no result file" in result["summary"]


# ---------------------------------------------------------------------------
# Editing codex — makes a real commit so diff/patch are non-empty
# (Tests that git diff <base> -- also captures committed changes.)
# ---------------------------------------------------------------------------

@pytest.fixture
def uncommitted_codex(tmp_path):
    """Fake codex that modifies a tracked file in the worktree WITHOUT staging or committing.

    Simulates real codex exec (-s workspace-write) behaviour: edits land in the working
    tree only.  README.md is guaranteed to exist in the worktree (seeded by git_repo).
    """
    result = {
        "task_id": "t-uncommitted",
        "status": "success",
        "summary": "modified README.md without committing",
        "files_changed": ["README.md"],
        "validation_results": [],
        "issues": [],
        "proposed_followup_tasks": [],
        "completed_at": "2026-01-01T00:00:00+00:00",
    }
    script = tmp_path / "uncommitted_codex"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json\n"
        "args = sys.argv[1:]\n"
        "output_file = None\n"
        "i = 0\n"
        "while i < len(args):\n"
        "    if args[i] == '-o' and i + 1 < len(args):\n"
        "        output_file = args[i + 1]; i += 2\n"
        "    else:\n"
        "        i += 1\n"
        "open('README.md', 'w').write('codex modified this\\n')\n"
        f"result = {json.dumps(result)}\n"
        "if output_file:\n"
        "    open(output_file, 'w').write(json.dumps(result))\n"
    )
    script.chmod(0o755)
    return str(script)


@pytest.fixture
def editing_codex(tmp_path):
    """Fake codex that writes and commits a file, then writes a valid JSON result to -o."""
    result = {
        "task_id": "t-edit",
        "status": "success",
        "summary": "wrote codex_output.txt",
        "files_changed": ["codex_output.txt"],
        "validation_results": [],
        "issues": [],
        "proposed_followup_tasks": [],
        "completed_at": "2026-01-01T00:00:00+00:00",
    }
    script = tmp_path / "editing_codex"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json, subprocess\n"
        "args = sys.argv[1:]\n"
        "output_file = None\n"
        "i = 0\n"
        "while i < len(args):\n"
        "    if args[i] == '-o' and i + 1 < len(args):\n"
        "        output_file = args[i + 1]; i += 2\n"
        "    else:\n"
        "        i += 1\n"
        "open('codex_output.txt', 'w').write('codex output\\n')\n"
        "subprocess.run(['git', 'add', 'codex_output.txt'], check=True, capture_output=True)\n"
        "subprocess.run(['git', 'commit', '-m', 'codex edit'], check=True, capture_output=True)\n"
        f"result = {json.dumps(result)}\n"
        "if output_file:\n"
        "    open(output_file, 'w').write(json.dumps(result))\n"
    )
    script.chmod(0o755)
    return str(script)


# ---------------------------------------------------------------------------
# Diff / patch capture
# ---------------------------------------------------------------------------

def test_diff_file_created(git_repo, tasks_path, editing_codex):
    _seed_task(tasks_path, _task(task_id="t-edit", base_commit=""))
    run("t-edit", dry_run=False, codex_bin=editing_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    diff = git_repo / ".agents" / "runs" / "t-edit.diff"
    assert diff.exists()
    assert "codex_output.txt" in diff.read_text()


def test_patch_file_created(git_repo, tasks_path, editing_codex):
    _seed_task(tasks_path, _task(task_id="t-edit", base_commit=""))
    run("t-edit", dry_run=False, codex_bin=editing_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    patch = git_repo / ".agents" / "runs" / "t-edit.patch"
    assert patch.exists()
    assert patch.read_text() != ""


def test_result_json_copied_to_handoff(git_repo, tasks_path, editing_codex):
    _seed_task(tasks_path, _task(task_id="t-edit", base_commit=""))
    run("t-edit", dry_run=False, codex_bin=editing_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    result_file = git_repo / ".agents" / "handoffs" / "codex_to_claude" / "result_t-edit.json"
    assert result_file.exists()
    data = json.loads(result_file.read_text())
    assert data["task_id"] == "t-edit"
    assert data["status"] == "success"


def test_run_metadata_includes_artifact_paths(git_repo, tasks_path, editing_codex):
    runs_dir = git_repo / ".agents" / "runs"
    _seed_task(tasks_path, _task(task_id="t-edit", base_commit=""))
    run("t-edit", dry_run=False, codex_bin=editing_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    meta = read_run_metadata(_safe_name("t-edit"), runs_dir=runs_dir)
    assert "diff_path" in meta
    assert "patch_path" in meta
    assert "result_path" in meta
    assert "changed_files_actual" in meta


def test_changed_files_actual_matches_diff(git_repo, tasks_path, editing_codex):
    runs_dir = git_repo / ".agents" / "runs"
    _seed_task(tasks_path, _task(task_id="t-edit", base_commit=""))
    run("t-edit", dry_run=False, codex_bin=editing_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    meta = read_run_metadata("t-edit", runs_dir=runs_dir)
    assert "codex_output.txt" in meta["changed_files_actual"]
    assert meta["files_changed_mismatch"] is False


# ---------------------------------------------------------------------------
# Uncommitted worktree edits — core scenario for real codex exec
# ---------------------------------------------------------------------------

def test_diff_nonempty_for_uncommitted_edit(git_repo, tasks_path, uncommitted_codex):
    _seed_task(tasks_path, _task(task_id="t-uncommitted", base_commit=""))
    run("t-uncommitted", dry_run=False, codex_bin=uncommitted_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    diff = git_repo / ".agents" / "runs" / "t-uncommitted.diff"
    assert diff.exists()
    assert "README.md" in diff.read_text()


def test_patch_nonempty_for_uncommitted_edit(git_repo, tasks_path, uncommitted_codex):
    _seed_task(tasks_path, _task(task_id="t-uncommitted", base_commit=""))
    run("t-uncommitted", dry_run=False, codex_bin=uncommitted_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    patch = git_repo / ".agents" / "runs" / "t-uncommitted.patch"
    assert patch.exists()
    assert patch.read_text().strip() != ""


def test_changed_files_captured_for_uncommitted_edit(git_repo, tasks_path, uncommitted_codex):
    runs_dir = git_repo / ".agents" / "runs"
    _seed_task(tasks_path, _task(task_id="t-uncommitted", base_commit=""))
    run("t-uncommitted", dry_run=False, codex_bin=uncommitted_codex,
        repo_root=git_repo, tasks_path=tasks_path)
    meta = read_run_metadata("t-uncommitted", runs_dir=runs_dir)
    assert "README.md" in meta["changed_files_actual"]


def test_apply_uncommitted_patch_changes_main_checkout(git_repo, tasks_path, uncommitted_codex, tmp_path):
    """End-to-end: uncommitted Codex edit → patch captured → apply → main checkout file changes."""
    from scripts.agents.apply_codex_patch import apply as apply_patch

    runs_dir = git_repo / ".agents" / "runs"
    cfg = tmp_path / "config.toml"
    cfg.write_text('[review]\ncodex_result_review = "always"\n[patch]\nbase_commit_policy = "warn"\n')

    _seed_task(tasks_path, _task(task_id="t-uncommitted", base_commit=""))
    run("t-uncommitted", dry_run=False, codex_bin=uncommitted_codex,
        repo_root=git_repo, tasks_path=tasks_path)

    result = apply_patch("t-uncommitted", force=True, repo_root=git_repo,
                         tasks_path=tasks_path, runs_dir=runs_dir, config_path=cfg)

    assert result["status"] == "applied", result.get("error")
    assert (git_repo / "README.md").read_text() == "codex modified this\n"


def test_files_changed_mismatch_flagged(git_repo, tasks_path, tmp_path):
    """Codex reports wrong files_changed — mismatch should be flagged."""
    result = {
        "task_id": "t-mismatch",
        "status": "success",
        "summary": "wrote a file",
        "files_changed": ["wrong_file.txt"],  # lie
        "validation_results": [],
        "issues": [],
        "proposed_followup_tasks": [],
        "completed_at": "2026-01-01T00:00:00+00:00",
    }
    script = tmp_path / "mismatch_codex"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json, subprocess\n"
        "args = sys.argv[1:]\n"
        "output_file = None\n"
        "i = 0\n"
        "while i < len(args):\n"
        "    if args[i] == '-o' and i + 1 < len(args):\n"
        "        output_file = args[i + 1]; i += 2\n"
        "    else:\n"
        "        i += 1\n"
        "open('actual_output.txt', 'w').write('actual output\\n')\n"
        "subprocess.run(['git', 'add', 'actual_output.txt'], check=True, capture_output=True)\n"
        "subprocess.run(['git', 'commit', '-m', 'codex edit'], check=True, capture_output=True)\n"
        f"result = {json.dumps(result)}\n"
        "if output_file:\n"
        "    open(output_file, 'w').write(json.dumps(result))\n"
    )
    script.chmod(0o755)
    _seed_task(tasks_path, _task(task_id="t-mismatch", base_commit=""))
    run("t-mismatch", dry_run=False, codex_bin=str(script),
        repo_root=git_repo, tasks_path=tasks_path)
    meta = read_run_metadata("t-mismatch", runs_dir=git_repo / ".agents" / "runs")
    assert meta["files_changed_mismatch"] is True


# ---------------------------------------------------------------------------
# Preflight staleness warning
# ---------------------------------------------------------------------------

def test_preflight_no_warning_on_clean_repo(git_repo, capsys):
    """Clean repo produces no staleness warning."""
    _warn_protocol_staleness(git_repo)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err


def test_preflight_warns_on_dirty_protocol_file(git_repo, capsys):
    """Uncommitted change to a protocol file triggers a warning."""
    agents_md = git_repo / "AGENTS.md"
    agents_md.write_text("dirty content\n")
    subprocess.run(["git", "-C", str(git_repo), "add", str(agents_md)], capture_output=True)
    _warn_protocol_staleness(git_repo)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "AGENTS.md" in captured.err


def test_preflight_no_warning_for_unrelated_dirty_file(git_repo, capsys):
    """Uncommitted change outside protocol paths produces no warning."""
    other = git_repo / "unrelated.txt"
    other.write_text("irrelevant\n")
    subprocess.run(["git", "-C", str(git_repo), "add", str(other)], capture_output=True)
    _warn_protocol_staleness(git_repo)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err


def test_dry_run_artifacts_created(git_repo, tasks_path):
    """Dry-run still creates diff/patch/result artifacts (diff is empty, patch is empty)."""
    runs_dir = git_repo / ".agents" / "runs"
    _seed_task(tasks_path, _task())
    run("t-001", dry_run=True, repo_root=git_repo, tasks_path=tasks_path)
    meta = read_run_metadata("t-001", runs_dir=runs_dir)
    assert Path(meta["diff_path"]).exists()
    assert Path(meta["patch_path"]).exists()
    assert Path(meta["result_path"]).exists()


# ---------------------------------------------------------------------------
# --reset-status CLI flag
# ---------------------------------------------------------------------------

def test_reset_status_updates_task(tmp_path, monkeypatch, capsys):
    """--reset-status rewrites the task's status and prints JSON confirmation."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    tp = agents_dir / "tasks.json"
    _seed_task(tp, _task(status="running"))

    monkeypatch.setattr(
        "sys.argv",
        ["run_codex_task", "--task-id", "t-001", "--reset-status", "failed"],
    )
    monkeypatch.chdir(tmp_path)

    main()

    out = json.loads(capsys.readouterr().out)
    assert out == {"task_id": "t-001", "status": "failed"}
    assert get_task("t-001", path=tp)["status"] == "failed"


def test_reset_status_invalid_status_exits(tmp_path, monkeypatch, capsys):
    """--reset-status with an unknown status exits with code 1 and prints an error."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    tp = agents_dir / "tasks.json"
    _seed_task(tp, _task(status="running"))

    monkeypatch.setattr(
        "sys.argv",
        ["run_codex_task", "--task-id", "t-001", "--reset-status", "bogus"],
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    assert "bogus" in capsys.readouterr().err


def test_reset_status_missing_task_exits(tmp_path, monkeypatch, capsys):
    """--reset-status with an unknown task_id exits with code 1."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "tasks.json").write_text("[]\n")

    monkeypatch.setattr(
        "sys.argv",
        ["run_codex_task", "--task-id", "no-such-task", "--reset-status", "ready"],
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
