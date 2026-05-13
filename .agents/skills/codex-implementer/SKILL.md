# Skill: codex-implementer

Codex behavior rules when launched in non-interactive task mode via Route B.

## How to detect task mode

You are in task mode if:
- You were launched by `run_codex_task.py` (a task artifact is present), OR
- The prompt contains a `ImplementationTask` JSON object or a path to one under `.agents/runs/`.

Otherwise, use normal interactive Codex behavior. These rules only apply in task mode.

## Task mode rules

1. **Read the task** — load the `ImplementationTask` from the path provided. Note `task_id`, `scope`, `validation_commands`, and `base_commit`.
2. **Stay in scope** — implement only what the task describes. If architecture seems wrong, note it in `follow_up_tasks`; do not expand scope.
3. **Small, reviewable diffs** — prefer targeted edits over broad rewrites.
4. **Run validation** — run every command in `validation_commands` before writing the result. Do not report success without running them.
5. **Write JSON result only** — write an `ImplementationResult` JSON to the path specified in the task (or to `.agents/runs/<task_id>/<task_id>.result.json`). Do not write free-form prose as the primary output.
6. **Propose, do not create** — if you discover follow-up work, add it to `follow_up_tasks` in the result JSON. Do not add entries to `.agents/tasks.json` directly.
7. **Do not read `.claude/` files** — those are Claude-specific. Do not edit them.

## ImplementationResult schema

See `.agents/schemas/implementation_result.schema.json`. Required fields:

```json
{
  "task_id": "<id>",
  "status": "success" | "failure" | "partial",
  "files_changed": ["<path>", ...],
  "validation_output": "<stdout/stderr summary>",
  "summary": "<one short paragraph: what changed and why>",
  "follow_up_tasks": []
}
```

## Repo guidance

See `AGENTS.md` for project identity, commands, architecture, and working rules.
