# Bucket B02: Task Queue Helpers

Parent: ../workstream.md
State: done
Goal for session: Add queue helpers.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- This bucket adds deterministic task/status utilities used by runner, apply, cleanup, and future worker queue.
- It avoids Codex execution and git worktree mechanics.

## Tasks

- [x] Create `scripts/agents/task_queue.py`.
- [x] Add helpers to load/save `.agents/tasks.json` atomically enough for single-dispatch Route B.
- [x] Add helper to create/update a task by `task_id`.
- [x] Add helper to record task status transitions: `ready`, `running`, `result_ready`, `applied`, `failed`, `needs_input`, `cleaned`.
- [x] Add helper to write/read `.agents/runs/<task_id>.run.json`.
- [x] Add minimal tests for task load/save/status/update behavior.

## Required touchpoints

- `[.agents/tasks.json]  full file  task ledger`
  Match current scaffold shape.
- `[.agents/schemas/implementation_task.schema.json]  full file  task schema`
  Keep helper output schema-compatible.
- `[scripts/agents/]  ls/find  existing scripts`
  Avoid duplicate helper names.
- `[tests/ or test config]  grep: agents|pytest|tmp_path  test style`
  Place focused tests consistently.

## Conditional touchpoints

- `[pyproject.toml or setup.cfg or pytest.ini]  grep: pytest|pythonpath  pytest config`
  Read only if test import paths are unclear.
- `[.agents/config.toml]  full file  config defaults`
  Read only if helpers need path/config constants.

## Do-not-read / avoid

- `mtg_sim/sim/*`
  Queue helpers should not depend on simulator internals.
- `.claude/skills/*`
  Skill behavior is not needed until B06.

## Design direction

- Keep helper APIs boring and script-friendly.
- Do not implement multi-worker atomic locking yet; leave a clear seam for future A/C.
- Preserve completed tasks; do not delete successful tasks.
- Use `base_commit` as data, not policy enforcement, in this bucket.

## Validation

- `python3 -m pytest tests/agents/test_task_queue.py -q`
- `python3 -m json.tool .agents/tasks.json`
- Expected: task helpers create/update/read ledger and run metadata without touching simulator code.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- [2026-05-13 09:30] Created. Handoff: none yet. Gotchas: none yet.
- [2026-05-13 10:00] Done. 24/24 tests pass. Created `scripts/agents/task_queue.py` and `tests/agents/test_task_queue.py`. Also created `scripts/__init__.py`, `scripts/agents/__init__.py`, `tests/__init__.py`, `tests/agents/__init__.py`. Handoff: B03 can import from `scripts.agents.task_queue`; `upsert_task`, `update_task_status`, `write_run_metadata` are the primary APIs. Gotcha: no `pyproject.toml` — tests must use `sys.path.insert` for root-level imports.
