---
name: task_queue.py notes
description: Gotchas and touchpoints for scripts/agents/task_queue.py
type: project
---

## Touchpoints

- `load_tasks` / `save_tasks` — atomic write via `.tmp` + `os.replace`; always takes explicit `path=`
- `write_run_metadata` — writes to `<runs_dir>/<task_id>.run.json`; **does not sanitize `task_id`**
- `update_task_status` — sets `status` + `status_updated_at`; raises `KeyError` if task missing

## Gotchas

- `write_run_metadata` passes `task_id` directly into the filename. If `task_id` contains slashes or spaces it will break the path. Callers must sanitize (e.g. `_safe_name(task_id)`) before passing.
- All path args default to cwd-relative constants (`TASKS_PATH`, `RUNS_DIR`). In tests, always pass explicit `path=` / `runs_dir=` pointing at `tmp_path`-based dirs.
