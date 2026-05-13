import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.agents.task_queue import (
    VALID_STATUSES,
    get_task,
    load_tasks,
    read_run_metadata,
    save_tasks,
    update_task_status,
    upsert_task,
    write_run_metadata,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ledger(tmp_path):
    return tmp_path / "tasks.json"


@pytest.fixture
def runs(tmp_path):
    return tmp_path / "runs"


def _task(task_id="t-001", **kwargs):
    return {
        "task_id": task_id,
        "base_commit": "abc123",
        "title": "Test task",
        "description": "desc",
        "acceptance_criteria": ["it works"],
        **kwargs,
    }


# ---------------------------------------------------------------------------
# load_tasks / save_tasks
# ---------------------------------------------------------------------------

def test_load_tasks_missing_file_returns_empty(tmp_path):
    assert load_tasks(tmp_path / "nonexistent.json") == []


def test_save_and_load_roundtrip(ledger):
    tasks = [_task("t-001"), _task("t-002")]
    save_tasks(tasks, ledger)
    assert load_tasks(ledger) == tasks


def test_save_is_atomic(ledger):
    # File is replaced atomically; no partial write visible
    save_tasks([_task()], ledger)
    save_tasks([_task("t-002")], ledger)
    result = load_tasks(ledger)
    assert len(result) == 1
    assert result[0]["task_id"] == "t-002"


def test_load_tasks_rejects_non_array(tmp_path):
    bad = tmp_path / "tasks.json"
    bad.write_text('{"task_id": "x"}')
    with pytest.raises(ValueError, match="Expected a JSON array"):
        load_tasks(bad)


# ---------------------------------------------------------------------------
# upsert_task
# ---------------------------------------------------------------------------

def test_upsert_inserts_new_task(ledger):
    upsert_task(_task("t-001"), ledger)
    tasks = load_tasks(ledger)
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == "t-001"


def test_upsert_replaces_existing_task(ledger):
    upsert_task(_task("t-001", title="old"), ledger)
    upsert_task(_task("t-001", title="new"), ledger)
    tasks = load_tasks(ledger)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "new"


def test_upsert_preserves_other_tasks(ledger):
    upsert_task(_task("t-001"), ledger)
    upsert_task(_task("t-002"), ledger)
    upsert_task(_task("t-001", title="updated"), ledger)
    tasks = load_tasks(ledger)
    assert len(tasks) == 2
    ids = {t["task_id"] for t in tasks}
    assert ids == {"t-001", "t-002"}


def test_upsert_requires_task_id(ledger):
    with pytest.raises(ValueError, match="task_id"):
        upsert_task({"title": "no id"}, ledger)


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------

def test_get_task_returns_task(ledger):
    upsert_task(_task("t-001"), ledger)
    result = get_task("t-001", ledger)
    assert result is not None
    assert result["task_id"] == "t-001"


def test_get_task_returns_none_if_missing(ledger):
    assert get_task("nonexistent", ledger) is None


# ---------------------------------------------------------------------------
# update_task_status
# ---------------------------------------------------------------------------

def test_update_task_status_sets_status(ledger):
    upsert_task(_task("t-001"), ledger)
    updated = update_task_status("t-001", "running", ledger)
    assert updated["status"] == "running"
    assert "status_updated_at" in updated


def test_update_task_status_persists(ledger):
    upsert_task(_task("t-001"), ledger)
    update_task_status("t-001", "result_ready", ledger)
    assert get_task("t-001", ledger)["status"] == "result_ready"


@pytest.mark.parametrize("status", sorted(VALID_STATUSES))
def test_all_valid_statuses_accepted(ledger, status):
    upsert_task(_task("t-s"), ledger)
    updated = update_task_status("t-s", status, ledger)
    assert updated["status"] == status


def test_update_task_status_rejects_invalid(ledger):
    upsert_task(_task("t-001"), ledger)
    with pytest.raises(ValueError, match="Invalid status"):
        update_task_status("t-001", "bogus", ledger)


def test_update_task_status_raises_on_missing_task(ledger):
    with pytest.raises(KeyError, match="t-missing"):
        update_task_status("t-missing", "running", ledger)


# ---------------------------------------------------------------------------
# write_run_metadata / read_run_metadata
# ---------------------------------------------------------------------------

def test_write_and_read_run_metadata(runs):
    data = {"task_id": "t-001", "status": "success", "summary": "done"}
    path = write_run_metadata("t-001", data, runs)
    assert path.exists()
    result = read_run_metadata("t-001", runs)
    assert result == data


def test_read_run_metadata_returns_none_if_missing(runs):
    assert read_run_metadata("nonexistent", runs) is None


def test_write_run_metadata_creates_dir(tmp_path):
    deep = tmp_path / "a" / "b" / "runs"
    write_run_metadata("t-001", {"x": 1}, deep)
    assert read_run_metadata("t-001", deep) == {"x": 1}
