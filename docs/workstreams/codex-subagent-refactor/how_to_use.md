# How to Use: Codex Subagent Refactor

**Status: implemented.** See `.agents/README.md` for permanent operational docs.

## Goal

Claude acts as planner/orchestrator. Codex acts as a bounded implementer. Claude creates one structured task, runs Codex synchronously in a temporary git worktree, reviews JSON/diff/patch artifacts, applies the patch after configured checks, and cleans up when accepted or rejected.

## Normal use

Use the Claude skill:

```text
Use the outsource-codex skill for this bounded implementation task.
```

The skill handles task creation, worktree Codex run, JSON result inspection, diff/patch review, patch application, validation, and optional cleanup.

## Manual commands

The scripts are recovery/debug tools. `apply` and `cleanup` are Python-import-only.

```bash
# Runner (has CLI)
python3 -m scripts.agents.run_codex_task --task-id <task_id> [--dry-run] [--repo-root .]

# Apply and cleanup (Python import only)
python3 -c "from scripts.agents.apply_codex_patch import apply; print(apply('<id>', repo_root='.', force=False))"
python3 -c "from scripts.agents.cleanup_codex_task import cleanup; print(cleanup('<id>', repo_root='.'))"
```

## Key config

Permanent config should live in:

```text
.agents/config.toml
```

Actual defaults (see `.agents/config.toml`):

```toml
[codex]
enabled = true
mode = "sync"
use_worktree = true

[review]
codex_result_review = "always"  # "always" | "claude_decides" (future)

[patch]
base_commit_policy = "warn"  # "warn" | "require" | "ignore"

[cleanup]
auto_cleanup_after_success = false
preserve_artifacts = true
```

## Artifact locations

```text
.agents/tasks.json
.agents/handoffs/claude_to_codex/task_<task_id>.json
.agents/handoffs/codex_to_claude/result_<task_id>.json
.agents/runs/<task_id>.run.json
.agents/runs/<task_id>.events.jsonl
.agents/runs/<task_id>.diff
.agents/runs/<task_id>.patch
.agents/worktrees/<task_id>/
```

## Worktree explanation

Codex edits a temporary checkout under `.agents/worktrees/<task_id>/`, not the main checkout. The wrapper computes `git diff` inside that worktree and saves review artifacts back into `.agents/runs/`. The patch file is the merge artifact applied to the main checkout after review checks.

## Codex role boundary

Codex may:
- implement the assigned task,
- run requested validation,
- write JSON result,
- propose follow-up tasks inside the result JSON.

Codex may not:
- directly add tasks to `.agents/tasks.json`,
- broaden scope beyond allowed edit paths,
- create downstream LLM work,
- silently skip required tests,
- edit the main checkout directly.

## Cleanup

Cleanup is explicit at first. It removes the temporary worktree/branch/status files but preserves review artifacts by default.

Use `--delete-artifacts` only when intentionally discarding audit history.

## Base commit policy

Each task records `base_commit`. Patch apply checks whether the main checkout still matches that base.

Default policy is `warn`: record and warn on mismatch, but allow apply if the patch still applies. Future parallel worker mode should probably switch to `refuse`.
