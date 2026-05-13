# Bucket B05: Apply Review Cleanup

Parent: ../workstream.md
State: later
Goal for session: Apply and clean.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- This bucket owns post-Codex lifecycle: review-policy gate, patch application, test command execution, and worktree cleanup.
- It keeps application separate from Codex execution so review remains explicit.

## Tasks

- [x] Create `scripts/agents/apply_codex_patch.py`.
- [x] Enforce configurable `review.codex_result_review`: default `always`; support `claude_decides` and `manual_only` as data values.
- [x] Enforce configurable `patch.base_commit_policy`: `ignore`, `warn`, `refuse`; default `warn`.
- [x] Run `git apply --check` before applying patch.
- [x] Apply `.agents/runs/<task_id>.patch` to main checkout.
- [x] Run task-configured validation commands after apply.
- [x] Update task status to `applied` or `failed`.
- [x] Create `scripts/agents/cleanup_codex_task.py`.
- [x] Cleanup removes worktree/branch/status/lock files but preserves result/diff/patch/events/run metadata by default.
- [x] Add tests for base-commit policy, patch apply, and cleanup behavior.

## Required touchpoints

- `[.agents/config.toml]  full file  review/patch/cleanup defaults`
  Policy source for apply/cleanup.
- `[scripts/agents/task_queue.py]  full file  task/run metadata helpers`
  Use run metadata and status updates.
- `[scripts/agents/run_codex_task.py]  grep: run metadata|patch_path|worktree_path  producer contract`
  Consume paths exactly as written by runner.
- `[tests/agents/test_run_codex_task.py]  full file  worktree fixtures`
  Reuse temp repo/fake patch setup.

## Conditional touchpoints

- `[.agents/runs/<task_id>.run.json]  sample if present  runtime metadata`
  Read only if manual smoke artifacts exist.
- `[pyproject.toml or pytest.ini]  grep: pytest  validation command style`
  Read only if applying task tests needs default command fallback.

## Do-not-read / avoid

- `mtg_sim/sim/*`
  Apply/cleanup should be repo-generic.
- `.agents/skills/codex-implementer/SKILL.md`
  Codex behavior is not needed for patch apply.

## Design direction

- Applying the patch is part of Route B, but should happen after review-policy gate.
- Do not auto-clean after success by default; config default is `auto_cleanup_after_success=false`.
- Cleanup should be manually callable and safe to rerun.
- Preserve artifacts unless `--delete-artifacts` is explicitly passed.
- If main `HEAD` differs from task `base_commit`, obey `base_commit_policy`.

## Validation

- `python3 -m pytest tests/agents/test_apply_codex_patch.py tests/agents/test_cleanup_codex_task.py -q`
- Manual dry-run chain: fake Codex task -> patch exists -> apply script applies -> cleanup script removes worktree.
- Expected: patch applied only after checks; cleanup preserves review artifacts by default.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- [2026-05-13 09:00] Created. Handoff: none yet. Gotchas: none yet.
- [2026-05-13] Done. Created apply_codex_patch.py (review/base-commit policy, git apply --check, validation cmds, status update) and cleanup_codex_task.py (worktree/branch/lock removal, artifact preservation). 25 new tests; 72 total agents tests pass. Gotcha: `tomllib` is stdlib in 3.11+; added `tomli` fallback import for 3.10.
