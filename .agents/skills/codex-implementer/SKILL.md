---
name: codex-implementer
description: Use when Codex is launched by a Route B ImplementationTask JSON block to perform one bounded read-only or implementation task and return ImplementationResult JSON.
---

# Skill: codex-implementer

Codex behavior rules when launched in non-interactive task mode via Route B.

## How to detect task mode

You are in task mode if the prompt contains an `ImplementationTask` JSON block (look for the `## ImplementationTask` heading followed by a ```json block).

Otherwise, use normal interactive Codex behavior. These rules only apply in task mode.

## Task mode rules

1. **Read the task** — parse the `ImplementationTask` JSON from the prompt. Note `task_id`, `validation_commands`, `files_off_limits`, and `base_commit`.
2. **Stay in scope** — implement only what the task describes. If architecture seems wrong, note it in `proposed_followup_tasks`; do not expand scope.
3. **Small, reviewable diffs** — prefer targeted edits over broad rewrites.
4. **Run validation** — run every command in `validation_commands` before reporting success. Do not report success without running them.
5. **Return JSON as final response** — return your final answer as raw JSON matching the ImplementationResult schema. Do not wrap in markdown. Do not manually write the result artifact; `codex exec -o / --output-last-message` captures your final response automatically.
6. **Propose, do not create** — if you discover follow-up work, add it to `proposed_followup_tasks` in the result JSON. Do not add entries to `.agents/tasks.json` directly.
7. **Do not read `.claude/` files** — those are Claude-specific. Do not edit them.

## ImplementationResult schema

See `.agents/schemas/implementation_result.json`. Required fields:

```json
{
  "task_id": "<id>",
  "status": "success" | "partial" | "failed" | "skipped",
  "summary": "<one short paragraph: what changed and why>",
  "files_changed": ["<path>", ...],
  "validation_results": [{"command": "...", "exit_code": 0, "stdout": "...", "stderr": "..."}],
  "issues": [],
  "proposed_followup_tasks": []
}
```

## Repo guidance

See `AGENTS.md` for project identity, commands, architecture, and working rules.
