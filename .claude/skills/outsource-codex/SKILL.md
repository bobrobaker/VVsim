# Skill: outsource-codex

Claude orchestration entry point for the Route B Codex delegation flow.

## Flow

1. **Create task** — write one `ImplementationTask` entry to `.agents/tasks.json`.
2. **Run Codex** — call `run_codex_task.py` with `--task-id`; Codex runs in an isolated worktree.
3. **Inspect result** — read `.agents/runs/<task_id>/<task_id>.result.json` and `.agents/runs/<task_id>/<task_id>.diff`.
4. **Apply patch** — call `apply_codex_patch.apply(task_id)` after review; passes policy checks before touching main checkout.
5. **Cleanup** — call `cleanup_codex_task.cleanup(task_id)` to remove worktree/branch/lock.

## Script invocations

### Run Codex (CLI)

```
python3 scripts/agents/run_codex_task.py \
    --task-id <id> \
    [--dry-run]            # simulate without real Codex auth
    [--codex-bin <path>]   # default: "codex"
    [--repo-root <path>]   # default: cwd
```

### Apply patch (Python)

```python
from scripts.agents.apply_codex_patch import apply
apply(task_id)             # raises ReviewRequiredError if review policy == "always"
apply(task_id, force=True) # override "always" review gate after manual inspection
```

### Cleanup (Python)

```python
from scripts.agents.cleanup_codex_task import cleanup
cleanup(task_id)                        # preserves result JSON, diff, patch, events, run metadata
cleanup(task_id, delete_artifacts=True) # removes all artifacts
```

## Key paths

| Path | Purpose |
|---|---|
| `.agents/tasks.json` | Task ledger |
| `.agents/config.toml` | User-editable config (review, patch, cleanup policy) |
| `.agents/schemas/` | ImplementationTask / ImplementationResult schemas |
| `.agents/runs/<task_id>/` | Result JSON, diff, patch, event log, run metadata |
| `.agents/worktrees/<task_id>/` | Volatile worktree (gitignored) |
| `.agents/locks/<task_id>.lock` | Volatile lock (gitignored) |

## Config knobs (`.agents/config.toml`)

| Key | Values | Default |
|---|---|---|
| `review.codex_result_review` | `"always"` / `"claude_decides"` (future) | `"always"` |
| `patch.base_commit_policy` | `"warn"` / `"require"` / `"ignore"` | `"warn"` |
| `cleanup.auto_cleanup_after_success` | bool | `false` |
| `cleanup.preserve_artifacts` | bool | `true` |

`review.codex_result_review = "always"` means Claude must inspect diff and result JSON before calling `apply(..., force=True)`.

## Review checklist (before apply)

- Diff is within task scope (no unrelated files changed).
- Result JSON has `status: "success"` and no unexpected `follow_up_tasks`.
- Validation commands in result JSON passed.
- Base commit matches HEAD or policy is `"warn"` (acceptable deviation logged).

## Role boundaries

- Claude owns: task creation, diff review, apply decision, cleanup initiation.
- Codex owns: implementation in worktree, validation, JSON result writing.
- Codex must NOT add tasks to `.agents/tasks.json` directly; follow-ups go in result JSON only.
