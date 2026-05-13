# Prompt: Multi-Window Codex Worker Pool

You are continuing planning inside the MTG simulator project. The user has chosen to implement Route B first, but wants this document to preserve enough context to later build Route C: a multi-window Codex worker pool.

## Project context

The repo is an MTG/Vivi simulator. The user wants Claude Code CLI to plan/orchestrate and Codex to provide additional implementation/test/log-analysis throughput. The user wants to eventually run one command that spawns multiple Codex agents, each visible in its own terminal pane/window, each claiming compatible tasks and producing structured results.

The current plan is to implement Route B first: Claude creates one Codex task, Claude runs `codex exec`, Codex writes a result artifact, and Claude reviews the result.

Route C must reuse the same `.agents/tasks.json` queue and task/result schemas.

## Route C concept

A command such as:

```bash
python scripts/agents/codex_pool.py --workers 4 --mode implement
```

would start a main controller window, spawn N Codex worker windows/panes where N is chosen by the user, assign or let each worker claim a ready task, display each worker’s progress in a visible pane, detect `needs_input` status and notify the user, watch for task completion/result artifacts, launch new tasks when workers finish and compatible tasks remain, and keep the main controller in a stable terminal location.

## Recommended terminal implementation

Use tmux or equivalent terminal multiplexer later. Do not implement terminal UI before the single-task dispatch flow is reliable.

Potential structure:

```text
scripts/agents/codex_pool.py        # controller process
scripts/agents/codex_worker.py      # one worker loop
scripts/agents/worktree_manager.py  # per-worker worktree lifecycle
scripts/agents/task_queue.py        # task claim/status helpers
```

## Worktree requirement

Parallel Codex agents should not edit the same checkout.

Use one git worktree per worker:

```text
.agents/worktrees/worker-1/
.agents/worktrees/worker-2/
.agents/worktrees/worker-3/
...
```

The main repo remains the planner/control repo. Workers edit isolated worktrees. This prevents two agents from modifying the same working tree and makes diff/review/merge handling cleaner.

## Task compatibility

Each task should include declared edit surfaces:

```json
{
  "scope": {
    "allowed_edit_paths": [
      "mtg_sim/sim/card_behaviors.py",
      "mtg_sim/tests/test_fetchlands.py"
    ],
    "forbidden_touchpoints": [],
    "required_touchpoints": [],
    "conditional_touchpoints": []
  }
}
```

The pool controller should avoid running tasks in parallel when their `allowed_edit_paths` overlap, unless explicitly allowed.

## Worker status files

Each worker should write status:

```text
.agents/status/worker-1.json
.agents/status/worker-2.json
.agents/status/task_<task_id>.json
```

Suggested status fields:

```json
{
  "worker_id": "worker-1",
  "task_id": "bucket-fetchlands-001",
  "status": "in_progress",
  "started_at": "...",
  "last_heartbeat_at": "...",
  "needs_input": false,
  "message": "Running focused tests"
}
```

## Needs-input behavior

Codex should not silently guess when blocked. It should write a result/status artifact with `needs_input: true`, include the exact question, include current diff/test state, and stop or pause. The controller should notify the user and leave the pane visible.

## Result and review flow

Codex workers write:

```text
.agents/handoffs/codex_to_claude/result_<task_id>.json
.agents/runs/<task_id>.events.jsonl
```

Claude or the user reviews result artifacts and diffs. Successful tasks move to `review_ready`, not automatically `done`, unless the user later permits automatic finalization.

## Files likely needed later

```text
scripts/agents/codex_pool.py
scripts/agents/codex_worker.py
scripts/agents/worktree_manager.py
scripts/agents/task_queue.py
.agents/tasks.json
.agents/config.toml
.agents/status/.gitkeep
.agents/locks/.gitkeep
.agents/worktrees/README.md
.agents/schemas/task_status.schema.json
.agents/schemas/implementation_task.schema.json
.agents/schemas/implementation_result.schema.json
tests/agents/test_task_queue.py
tests/agents/test_result_schema.py
```

## Safety/defaults

Default to one task per worker, one worktree per worker, no automatic merge, no deleting result artifacts, no marking `done` without review, tests required for all bucket tasks, and no broad architecture changes by Codex.

## Key design rule

Route C should be a wrapper around Route B/A artifacts, not a separate agent system. The worker pool should consume the same task queue and produce the same result artifacts.

## Open design questions

- Should workers use `codex exec` or interactive Codex panes?
- Should the controller spawn tmux panes or separate terminals?
- Should worker worktrees be persistent or ephemeral?
- What should happen when two tasks touch the same file?
- Should the pool ever auto-merge completed work?
