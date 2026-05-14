---
name: run_codex_task.py notes
description: Gotchas and touchpoints for scripts/agents/run_codex_task.py
type: project
---

## Touchpoints

- `run(task_id, *, dry_run, codex_bin, repo_root, tasks_path)` — main entry; raises `KeyError` if task not in ledger
- `_run_codex(task, codex_bin, worktree_path)` — resolves worktree_path to absolute; runs `codex exec -C <wt> -s workspace-write -o <result_file> [--output-schema <schema>] -`; reads result from file (not stdout)
- `_build_prompt(task)` — embeds full task JSON in ```json block; Output section instructs Codex to return raw JSON (captured via -o, not manually written)
- `_warn_protocol_staleness(repo_root)` — preflight; runs `git diff --name-only HEAD`; warns if dirty files match `_PROTOCOL_PATHS`
- `_safe_name(task_id)` — sanitize for all filesystem paths (worktree dir, branch name, run metadata filename)
- `_capture_diff` / `_capture_patch` — `git diff <base> --` and `git diff --binary <base> --` in worktree (worktree state vs base_commit; captures uncommitted Codex edits)
- `_copy_result` — copies result JSON to `.agents/handoffs/codex_to_claude/result_<safe_id>.json`
- `_changed_files_from_diff` — parses `diff --git` lines; stored as `changed_files_actual` in run metadata

## Gotchas

- Worktrees are created from HEAD. Uncommitted changes to protocol files (schemas, SKILL.md, AGENTS.md, scripts/agents/) do NOT propagate. Commit before running or Codex sees stale files.
- `-o` must be an absolute path. With `-C worktree_path`, a relative path resolves inside Codex's workspace root rather than where the harness expects it. `worktree_path.resolve()` at the top of `_run_codex` fixes this.
- `codex exec -s workspace-write` edits files without committing. `git diff <base>..HEAD` (commit-only) silently produces an empty diff; use `git diff <base> --` (worktree vs commit) instead.
- Tests that exercise diff/patch capture must seed tasks with `base_commit=""` so auto-fill records the actual repo HEAD. A hardcoded fake SHA causes `git diff <sha> --` to fail with nonzero exit (unknown revision); the empty-patch guard uses `HEAD` (always resolvable in worktree) to avoid this.
- Empty patch for implementation task → `apply()` returns `status: failed`. Empty patch for scout/read-only task (`metadata.read_only=True` or `mode in ("scout","read_only")`) → `status: applied` with note.
- `_safe_name` must be applied before passing `task_id` to `write_run_metadata` — that helper does not sanitize.
- Run result JSONs (`.agents/runs/<id>.run.json`) can be 50–200 KB. Grep for the specific field you need (`grep "field_name" .agents/runs/<id>.run.json`) rather than reading the whole file.
