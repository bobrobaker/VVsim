# Workstream: Codex Subagent Refactor

Progress: B07/done; workstream complete
Blocked: none

## Objective

Build Route B: Claude creates one bounded Codex implementation task, runs Codex synchronously in a temporary git worktree, receives JSON-only results, captures diff/patch artifacts, applies the patch after review policy checks, and leaves cleanup explicit. Preserve upgrade paths to a future Codex worker queue, worker pool, and configurable token-routing policy without implementing those modes now.

## Execution Protocol (do not change)

1. Read this workstream first.
2. Use `Progress` and `Bucket Index` to select the active bucket; if none is active, select the next bucket.
3. Open only the selected bucket file.
4. Read only that bucket's required touchpoints before reporting.
5. Report first: selected bucket, required touchpoints read, current behavior, proposed edits, validation plan, and extra touchpoints if needed.
6. Only edit after the plan is clear.
7. Run the bucket's validation.
8. Update the bucket file's `Updates` section with completed tasks, discoveries, gotchas, test results, and handoff notes. Use timestamp format `[YYYY-MM-DD HH:MM]` for all entries.
9. Update this workstream's `Progress`, `Bucket Index`, and `Updates` only for progress, sequencing changes, cross-bucket discoveries, and cross-bucket gotchas. Use timestamp format `[YYYY-MM-DD HH:MM]` for all entries.
10. Keep only one bucket active at a time unless the user explicitly authorizes parallel execution.

## Bucket Index

| B | State | File | Goal | Depends |
|---|---|---|---|---|
| B01 | done | buckets/B01_scaffold-agents.md | Create agent scaffolding/config/schemas | — |
| B02 | done | buckets/B02_task-queue-helpers.md | Add task queue helpers | B01 |
| B03 | done | buckets/B03_worktree-runner-dry-run.md | Create worktree runner dry-run | B02 |
| B04 | done | buckets/B04_result-diff-patch.md | Capture result/diff/patch | B03 |
| B05 | done | buckets/B05_apply-review-cleanup.md | Apply patch and cleanup | B04 |
| B06 | done | buckets/B06_claude-codex-instructions.md | Add Claude/Codex instructions | B05 |
| B07 | done | buckets/B07_docs-smoke-validation.md | Document and smoke-test flow | B06 |

States: `next`, `active`, `blocked`, `done`, `deferred`, `later`.

## Cross-Bucket Invariants

- Claude owns planning, review, and task creation; Codex is a bounded implementer.
- Codex may propose follow-up tasks in JSON results but must not directly add downstream LLM tasks to `.agents/tasks.json`.
- Route B is synchronous only: one Claude-created task, one Codex execution, one result review/apply path.
- Codex always runs in a temporary git worktree; do not let Codex edit the main checkout directly.
- Result artifacts are JSON-only; human-readable explanation belongs in structured string/list fields.
- Every task records `base_commit`; patch application checks it using configurable policy.
- Default review policy is `always`; later config may allow `claude_decides`.
- Default cleanup preserves result JSON, diff, patch, event log, and run metadata.
- Bucket/task implementation must be testable without real Codex by using dry-run/fake Codex mode.
- Patch application is explicit and validated; do not silently mutate main checkout before review checks.

## Deferred / Non-Goals

- Persistent Codex worker queue/daemon.
- Multi-window or tmux Codex worker pool.
- Automatic parallel task assignment.
- Automatic merge without review policy checks.
- Claude-as-external-worker orchestration.
- Codex-created executable task expansion.
- Full token-budget routing beyond config placeholders.

## Global Implementation Notes

- Use `.agents/` for neutral cross-agent state, schemas, handoffs, runs, worktrees, and docs.
- Use `.claude/skills/outsource-codex/SKILL.md` as the Claude entry point.
- Use `AGENTS.md` for stable Codex repo guidance; include strict task-artifact behavior only when Codex is launched in non-interactive task mode.
- Prefer wrapper scripts over fragile shell composed by Claude.
- Keep worktree, patch, apply, and cleanup paths deterministic from `task_id`.
- Add `.agents/worktrees/` and volatile run/lock/status files to `.gitignore`; preserve artifacts by default.

## Updates

- [2026-05-13 09:00] Initial plan created. Next: B01/scaffold agents.
- [2026-05-13 09:30] B01 done. Created: `.agents/config.toml`, `.agents/tasks.json`, `.agents/schemas/` (2 schemas), `.agents/handoffs/`, `.agents/runs/`, `.agents/locks/` (with .gitkeep), `.claude/skills/outsource-codex/SKILL.md`. Updated `.gitignore` for worktrees and lock volatiles. Pre-existing `.agents/skills/introspect/` preserved.
- [2026-05-13 10:00] B02 done. Created `scripts/agents/task_queue.py` (load/save/upsert/status/run-metadata helpers), `tests/agents/test_task_queue.py` (24 tests pass). No pyproject.toml — tests use sys.path.insert.
- [2026-05-13 13:00] B03 done. Created `scripts/agents/run_codex_task.py` and `tests/agents/test_run_codex_task.py` (16 tests). Cross-bucket gotcha: task_id must be sanitized via _safe_name() for all filesystem paths (worktree dir, branch name, run metadata filename); write_run_metadata in task_queue.py does NOT sanitize — caller responsibility.
- [2026-05-13 16:00] B04 done. Extended run_codex_task.py with diff/patch capture and result handoff copy. 23 runner tests pass (47 total). Gotcha: diff/patch tests must seed tasks with base_commit="" so actual repo HEAD is recorded; fake SHA causes silent empty diff.
- [2026-05-13] B05 done. Created apply_codex_patch.py and cleanup_codex_task.py; 72 agents tests pass. Next: B06/claude-codex-instructions.
- [2026-05-13] B07 done. Created .agents/README.md. Fixed two apply_codex_patch.py bugs (patch_path key mismatch; empty patch crash). Dry-run Route B flow verified end-to-end. 72 agents tests pass. Workstream complete.
- [2026-05-13] B06 done. Updated .claude/skills/outsource-codex/SKILL.md (full flow, flags, imports, config table, review checklist). Created .agents/skills/codex-implementer/SKILL.md. Added Codex Task Mode section to AGENTS.md. Gotcha: apply/cleanup have no CLI — Python import only. Next: B07/docs-smoke-validation.
