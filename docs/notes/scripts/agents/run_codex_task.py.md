---
name: run_codex_task.py notes
description: Gotchas and touchpoints for scripts/agents/run_codex_task.py
type: project
---

## Touchpoints

- `run(task_id, *, dry_run, codex_bin, repo_root, tasks_path)` — main entry; raises `KeyError` if task not in ledger
- `_safe_name(task_id)` — sanitize for all filesystem paths (worktree dir, branch name, run metadata filename)
- `_capture_diff` / `_capture_patch` — `git diff <base>..HEAD` and `git format-patch --stdout <base>` in worktree
- `_copy_result` — copies result JSON to `.agents/handoffs/codex_to_claude/result_<safe_id>.json`
- `_changed_files_from_diff` — parses `diff --git` lines; stored as `changed_files_actual` in run metadata

## Gotchas

- Tests that exercise diff/patch capture must seed tasks with `base_commit=""` so auto-fill records the actual repo HEAD. A hardcoded fake SHA causes `git diff <sha>..HEAD` to silently return empty output — no error, just an empty diff.
- `_run_codex` parses `proc.stdout` as JSON. Any stdout from the codex script (e.g. `git commit` output) will break parsing. Redirect git/tool output to stderr in fake codex scripts.
- `_safe_name` must be applied before passing `task_id` to `write_run_metadata` — that helper does not sanitize.
