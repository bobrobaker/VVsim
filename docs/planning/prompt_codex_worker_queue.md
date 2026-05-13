# Prompt: Codex Worker Queue Mode

You are continuing planning inside the MTG simulator project. The user has chosen to implement Route B first, but wants this document to preserve enough context to later build Route A: an independent Codex implementer loop.

## Project context

The repo is an MTG/Vivi simulator. Core architecture includes action generation, action resolution, card-specific behavior classes, policy scoring, manual-mode policy observations, and focused pytest tests for every behavioral bucket.

The user uses ChatGPT Project / GPT-5.5 Thinking for architecture and prompt design, Claude Code CLI as planner/orchestrator, and Codex as extra implementation/test/log-analysis capacity. The user wants to maximize useful Codex token usage without letting Codex own architecture.

## Route A concept

Claude prepares tasks for Codex through filesystem artifacts. Codex runs independently in another terminal as an implementer. It reads the shared task queue, claims the first compatible ready task, updates the task to show it is claimed/in progress, executes the task with minimal further input, produces a structured result artifact, updates task status to review-ready/done/blocked, clears its local context or starts a fresh run, and repeats.

Codex should not directly call Claude task tools. Claude built-in task management is treated as a session-local mirror, not the source of truth.

## Canonical source of truth

Use a neutral repo-owned ledger:

```text
.agents/tasks.json
```

Do not make Claude's task list canonical. Codex cannot call Claude's TaskCreate/TaskUpdate functions. Claude can later import selected `.agents/tasks.json` entries into its built-in task board when convenient.

## Status model

Use explicit status transitions:

```text
ready -> claimed -> in_progress -> needs_input | failed | review_ready -> done
```

Do not remove completed tasks from the ledger by default. Keep history for audit/introspection.

## Atomic claiming requirement

Route A must solve race conditions. Multiple Codex workers must not claim the same task.

Future implementation should include `.agents/locks/`, file-based locking or atomic rename, task status/version fields, worker_id, claimed_at timestamp, heartbeat/status file, and crash recovery policy.

The simplest safe pattern is: worker reads a ready task; worker attempts atomic lock creation for task_id; on success, updates task status to claimed/in_progress; on failure, rereads queue and tries next task.

## Task shape

Tasks should be compatible with Route B and C:

```json
{
  "schema_version": "1.0",
  "task_id": "bucket-fetchlands-001",
  "status": "ready",
  "created_by": "claude",
  "assigned_to": "codex",
  "mode": "implement",
  "priority": "medium",
  "risk": "low",
  "goal": "Implement and test fetchland bucket behavior.",
  "scope": {
    "required_touchpoints": [],
    "conditional_touchpoints": [],
    "forbidden_touchpoints": [],
    "allowed_edit_paths": [],
    "expected_test_paths": []
  },
  "acceptance": [],
  "commands": {
    "focused_tests": [],
    "full_tests": []
  },
  "handoff": {
    "result_path": ".agents/handoffs/codex_to_claude/result_<task_id>.json",
    "events_path": ".agents/runs/<task_id>.events.jsonl"
  }
}
```

## Result shape

Codex should write a structured result artifact:

```json
{
  "schema_version": "1.0",
  "task_id": "bucket-fetchlands-001",
  "status": "review_ready",
  "summary": [],
  "files_changed": [],
  "tests_run": [],
  "tests_failed": [],
  "deviations_from_scope": [],
  "risks": [],
  "needs_input": false,
  "followup_tasks": []
}
```

## Codex worker behavior

Codex should be instructed through a skill or prompt to obey task artifact scope, never broaden architecture unless explicitly allowed, add focused tests for every implementation task, run requested tests, write the result artifact even on failure, mark `needs_input` rather than guessing when blocked, avoid editing files outside `allowed_edit_paths`, and report deviations explicitly.

## Files likely needed later

```text
.agents/tasks.json
.agents/locks/.gitkeep
.agents/status/.gitkeep
.agents/handoffs/claude_to_codex/.gitkeep
.agents/handoffs/codex_to_claude/.gitkeep
.agents/schemas/implementation_task.schema.json
.agents/schemas/implementation_result.schema.json
.agents/schemas/task_status.schema.json
.agents/skills/codex-implementer/SKILL.md
scripts/agents/task_queue.py
scripts/agents/codex_worker.py
tests/agents/test_task_queue.py
tests/agents/test_result_schema.py
```

## Key design rule

Route A should be built only after Route B works. Route B should use the same task/result schemas so Route A becomes a worker-pool extension, not a rewrite.

## Open design questions

- Should workers mark successful tasks `review_ready` or `done`?
- Should Claude be required to review every Codex result before `done`?
- Should task claiming use Python locks, atomic file creation, or git worktrees?
- Should each worker operate in its own worktree from the beginning?
- How much autonomy should Codex have to create follow-up tasks?
