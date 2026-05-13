# Bucket B03: Worktree Runner Dry-Run

Parent: ../workstream.md
State: done
Goal for session: Build dry-run runner.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- This bucket builds the one-task executor shell without real Codex dependency.
- It groups task creation, temporary worktree creation, dry-run/fake command support, and run metadata.

## Tasks

- [x] Create `scripts/agents/run_codex_task.py`.
- [x] Implement CLI args: `--task-id`, optional `--codex-bin`, optional `--dry-run`, optional `--repo-root`.
- [x] Read task from `.agents/tasks.json` (ledger required; no auto-import from handoffs).
- [x] Record `base_commit` if missing at dispatch time.
- [x] Create branch/worktree under `.agents/worktrees/<task_id>` without modifying main checkout.
- [x] Copy/write the task artifact into the worktree.
- [x] In dry-run/fake mode, simulate Codex result JSON without requiring Codex auth.
- [x] Write `.agents/runs/<task_id>.run.json`.
- [x] Add focused tests using a temporary git repo and fake Codex command.

## Required touchpoints

- `[scripts/agents/task_queue.py]  full file  queue helpers`
  Reuse status/run metadata helpers.
- `[.agents/config.toml]  full file  worktree/dry-run defaults`
  Use configured worktree and review defaults.
- `[.agents/schemas/implementation_task.schema.json]  full file  task schema`
  Validate task fields used by runner.
- `[tests/agents/test_task_queue.py]  full file  test style`
  Reuse fixtures/patterns if present.

## Conditional touchpoints

- `[.gitignore]  grep: .agents/worktrees|.agents/runs  ignored artifacts`
  Read only if runner-created paths are not ignored.
- `[AGENTS.md]  full file if present  Codex guidance`
  Read only if dry-run prompt wording depends on existing Codex instructions.
- `[Codex CLI availability]  command: codex --version`
  Check only for manual smoke; tests must not require real Codex.

## Do-not-read / avoid

- `mtg_sim/sim/*`
  Runner plumbing does not need simulator internals.
- `.agents/skills/codex-implementer/SKILL.md`
  Codex instruction details are B06 unless a placeholder already exists.

## Design direction

- Synchronous only: the script waits for Codex/fake command to exit.
- Dry-run/fake mode is required and should be usable in tests.
- Worktree path and branch name must be deterministic from `task_id`.
- Use safe branch names; sanitize `task_id`.
- Do not apply patches in this bucket.
- Leave worktree in place after run.

## Validation

- `python3 -m pytest tests/agents/test_run_codex_task.py -q`
- Manual smoke if safe: create a demo task, run `run_codex_task.py --task-id demo --dry-run`.
- Expected: worktree created, run metadata written, fake result generated, no main-checkout code edits.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- [2026-05-13 10:00] Created. Handoff: none yet. Gotchas: none yet.
- [2026-05-13 13:00] Done. 16 tests pass (40 total in tests/agents/). Gotchas: (1) task_id must be sanitized via _safe_name() for both worktree/branch names AND run metadata filenames — raw task_id with slashes/spaces breaks filesystem paths; (2) runs_dir must be passed as repo_root/RUNS_DIR in tests, not left as default cwd-relative; (3) write_run_metadata in task_queue.py does not sanitize task_id — caller must sanitize before passing. Handoff to B04: worktree is left in place at .agents/worktrees/<safe_id>; result is in .agents/runs/<safe_id>.run.json; task status is result_ready or failed.
