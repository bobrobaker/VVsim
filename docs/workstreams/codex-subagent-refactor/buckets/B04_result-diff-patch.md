# Bucket B04: Result Diff Patch

Parent: ../workstream.md
State: done
Goal for session: Capture review artifacts.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- This bucket turns Codex/worktree output into Claude-reviewable artifacts.
- It focuses on JSON result validation, objective diff/patch capture, and metadata consistency.

## Tasks

- [ ] Extend `run_codex_task.py` to capture real/fake Codex JSON result.
- [ ] Copy result JSON from worktree to `.agents/handoffs/codex_to_claude/result_<task_id>.json`.
- [ ] Generate `.agents/runs/<task_id>.diff` from the worktree.
- [ ] Generate `.agents/runs/<task_id>.patch` as the merge artifact.
- [ ] Record changed files from git diff in run metadata.
- [ ] Compare result JSON `files_changed` to actual diff files and warn on mismatch.
- [ ] Update task status to `result_ready`, `failed`, or `needs_input`.
- [ ] Add tests for result/diff/patch capture using fake Codex edits.

## Required touchpoints

- `[scripts/agents/run_codex_task.py]  full file  runner`
  Main edit surface.
- `[scripts/agents/task_queue.py]  full file  status/run helpers`
  Update status and metadata.
- `[.agents/schemas/implementation_result.schema.json]  full file  result schema`
  Validate JSON-only Codex result.
- `[tests/agents/test_run_codex_task.py]  full file  runner tests`
  Extend fake-result coverage.

## Conditional touchpoints

- `[.agents/config.toml]  grep: preserve_artifacts|review|patch  artifact defaults`
  Read if artifact paths/policies are unclear.

## Do-not-read / avoid

- `mtg_sim/sim/*`
  Diff/patch mechanics are repo-generic.
- `.claude/skills/outsource-codex/SKILL.md`
  Skill orchestration belongs to B06.

## Design direction

- Result JSON is Codex self-report; diff/patch are objective evidence.
- Keep both `diff_path` and `patch_path` in run metadata.
- Preserve artifacts even when Codex fails, if any are available.
- Patch creation should not apply the patch.
- `proposed_followup_tasks` may appear in result JSON but must not mutate `.agents/tasks.json`.

## Validation

- `python3 -m pytest tests/agents/test_run_codex_task.py -q`
- Dry-run smoke that creates a fake edit and verifies result JSON, diff, patch, and run metadata exist.
- Expected: artifacts are generated in main checkout and point back to the correct worktree/task.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- [2026-05-13 13:00] Created. Handoff: none yet. Gotchas: none yet.
- [2026-05-13 16:00] Done. 23 tests pass (47 total in tests/agents/). Added: `_capture_diff` (git diff base..HEAD), `_capture_patch` (git format-patch --stdout), `_copy_result` (copies result JSON to codex_to_claude handoff dir), `_changed_files_from_diff` (parses diff --git lines). Run metadata now includes `diff_path`, `patch_path`, `result_path`, `changed_files_actual`, `files_changed_mismatch`. Gotcha: test tasks that exercise diff/patch must use `base_commit=""` so auto-fill records the actual repo HEAD; a hardcoded fake SHA causes `git diff <sha>..HEAD` to silently return empty.
