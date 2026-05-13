# .agents — Route B: Claude → Codex Sync Flow

## Overview

Route B lets Claude act as planner/orchestrator and Codex as a bounded implementer. Claude creates one structured task, Codex runs it in an isolated git worktree, and Claude reviews the JSON result and diff/patch before applying anything to the main checkout.

## Normal use

Invoke from Claude via the `outsource-codex` skill:

```text
Use the outsource-codex skill for this bounded implementation task.
```

The skill handles task creation, worktree run, result inspection, patch review, apply, and optional cleanup. See `.claude/skills/outsource-codex/SKILL.md` for full flow.

## Manual / recovery commands

Use these when debugging or recovering from a partial run:

```bash
# Run Codex in a worktree (--dry-run skips real Codex)
python3 -m scripts.agents.run_codex_task --task-id <task_id> [--dry-run] [--codex-bin codex] [--repo-root .]

# Apply the patch after review (--force bypasses review gate)
python3 -c "from scripts.agents.apply_codex_patch import apply; print(apply('<task_id>', repo_root='.', force=False))"

# Clean up worktree and branch (artifacts preserved by default)
python3 -c "from scripts.agents.cleanup_codex_task import cleanup; print(cleanup('<task_id>', repo_root='.'))"
```

Note: `apply` and `cleanup` are Python-import-only; they have no CLI entry point.

## Worktrees explained

Codex edits a **temporary checkout** under `.agents/worktrees/<task_id>/`, never the main repo. The runner captures `git diff` and `git format-patch` from inside that worktree and saves them to `.agents/runs/`. Only `apply_codex_patch` touches the main checkout, and only after review checks pass.

## Artifact locations

```
.agents/tasks.json                            # task registry
.agents/config.toml                           # Route B config
.agents/handoffs/claude_to_codex/task_<id>.json   # task handed to Codex
.agents/handoffs/codex_to_claude/result_<id>.json # Codex result
.agents/runs/<id>.run.json                    # run metadata
.agents/runs/<id>.diff                        # human-readable diff
.agents/runs/<id>.patch                       # git-format-patch output
.agents/worktrees/<id>/                       # temp worktree (removed by cleanup)
```

## Config knobs (.agents/config.toml)

| Key | Default | Options | Effect |
|---|---|---|---|
| `codex.enabled` | `true` | `true`/`false` | Enable/disable Codex execution |
| `codex.mode` | `"sync"` | `"sync"` | Synchronous only (worker queue is future) |
| `codex.use_worktree` | `true` | — | Always isolate Codex in a worktree |
| `review.codex_result_review` | `"always"` | `"always"`, `"claude_decides"` | When to require human review before apply |
| `patch.base_commit_policy` | `"warn"` | `"warn"`, `"require"`, `"ignore"` | What to do when base commit drifted |
| `cleanup.auto_cleanup_after_success` | `false` | — | Auto-remove worktree after apply |
| `cleanup.preserve_artifacts` | `true` | — | Keep result JSON, diff, patch after cleanup |

## Review policy

Default is `always`: human must confirm before patch is applied. Pass `force=True` (Python) to the `apply` function to bypass (only for scripted/dry-run use). Future `claude_decides` mode is a placeholder.

## Base-commit policy

Each task records `base_commit` at creation time. On apply, the runner checks whether the main checkout still matches. Default `warn`: mismatch is logged but apply proceeds if the patch still applies cleanly. Use `require` for stricter safety in parallel workflows.

## Dry-run mode

Pass `--dry-run` to `run_codex_task` (or `dry_run=True` in Python) to simulate a Codex run without executing real Codex. Result JSON is a simulated success; diff and patch are empty.

## Troubleshooting

- **`ReviewRequiredError`**: review gate is `always`; pass `force=True` to apply or change config.
- **`PatchCheckError`**: patch does not apply cleanly to current HEAD — check for upstream drift.
- **Empty patch on apply**: dry-run or Codex made no changes; apply skips with `status: applied`.
- **Worktree already exists**: a previous run did not clean up; run `cleanup` first or delete `.agents/worktrees/<task_id>` manually.
- **Lock file stale**: delete `.agents/locks/<task_id>.lock` if the runner crashed.

## Planned extensions (not yet implemented)

- Persistent Codex worker queue / daemon.
- Parallel task assignment / worker pool.
- `claude_decides` review policy.
- Automatic merge without explicit review gate.
