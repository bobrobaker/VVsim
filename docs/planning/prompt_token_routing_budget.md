# Prompt: Token Allocation and Routing Policy

You are continuing planning inside the MTG simulator project. The user has chosen to implement Route B first, but wants this document to preserve enough context to later build Route D: configurable token allocation between Claude and Codex.

## Project context

The user has multiple capable LLM surfaces: ChatGPT Project / GPT-5.5 Thinking for architecture, prompt design, and long-form reasoning; Claude Code CLI for planning/orchestration, native task handling, and high-risk implementation/review; and Codex for extra implementation/test/log-analysis capacity.

The user believes Codex may be weaker than Claude for some coding/architecture tasks, but it effectively increases available token budget. The goal is to keep token usage high on Codex when useful, while reserving Claude for architecture, orchestration, ambiguous design, and final review.

## Route D concept

Token allocation should be controlled by configuration, not repeated prompt wording.

Claude should decide whether to outsource a task to Codex by reading a repo-local config and applying routing rules.

Potential config file:

```text
.agents/config.toml
```

Example:

```toml
[budget]
codex_bias = "high"        # off | low | medium | high
max_parallel_codex = 3
claude_owns_architecture = true
require_claude_review_for_codex = true

[routing]
codex_default_for = [
  "bounded_implementation",
  "test_writing",
  "log_analysis",
  "mechanical_refactor",
  "bucket_task",
  "touchpoint_scout"
]

claude_default_for = [
  "architecture",
  "task_decomposition",
  "policy_design",
  "final_review",
  "ambiguous_rules_question",
  "multi_file_refactor"
]

[thresholds]
codex_max_risk = "medium"
codex_requires_tests = true
codex_forbidden_if_scope_unclear = true
```

## Routing principles

Codex is preferred for bounded implementation, mechanical refactors, test writing, log analysis, policy observation clustering, card bucket implementation with clear specs, focused bugfixes with known touchpoints, and scout reports that produce no code changes.

Claude is preferred for architecture decisions, ambiguous simulator semantics, Magic rules interpretation, policy design when win-rate implications are unclear, broad refactors involving action generation/resolver/state/policy together, final review of Codex changes, and deciding whether a policy problem is actually an action-generation or resolver bug.

ChatGPT Project is preferred for high-level planning, workstream design, compressed context, prompt baking, and evaluating agent architecture tradeoffs.

## Codex bias settings

Suggested behavior:

```text
codex_bias = off
  Claude does not outsource to Codex unless explicitly requested.

codex_bias = low
  Claude outsources only obvious bounded tasks with low risk and clear tests.

codex_bias = medium
  Claude outsources bounded implementation, tests, scout reports, and log analysis.

codex_bias = high
  Claude aggressively decomposes work into Codex-ready tasks while retaining architecture and review ownership.
```

## Task creation implications

When `codex_bias = high`, Claude should create more smaller tasks, push implementation/test/log-analysis to Codex, avoid doing Codex-suitable edits itself, reserve its own tokens for planning/review, and prefer Codex scout tasks before reading broad files itself.

When `codex_bias = low`, Claude should create fewer Codex tasks, outsource only clearly safe work, do more implementation itself, and avoid overhead from excessive handoff artifacts.

## Claude-as-agent option

The user has considered allowing Claude to run Claude as an external agent for itself, but this is less likely to be ideal because Claude already has native subagents/task mechanisms.

Default position: use Claude native subagents for Claude-internal delegation; use external `claude -p` only for special scripted workflows or when a clean isolated Claude worker is useful; do not build Claude-as-external-worker before Codex outsourcing is working.

## Config consumers

The following should read `.agents/config.toml`: Claude outsource skill, Codex dispatch wrapper, future Codex worker pool, and future task creation/prebake workflows.

## Files likely needed later

```text
.agents/config.toml
.claude/skills/outsource-codex/SKILL.md
.agents/skills/codex-implementer/SKILL.md
scripts/agents/routing.py
scripts/agents/run_codex_task.py
scripts/agents/task_queue.py
tests/agents/test_routing.py
```

## Key design rule

Token allocation should affect task routing, not task correctness. Every implementation task still requires scoped touchpoints, acceptance criteria, and tests.

## Open design questions

- What should the initial default `codex_bias` be?
- Should Claude ask before outsourcing, or only report after creating/running a Codex task?
- Which categories are never allowed for Codex?
- Should Codex ever create new tasks itself, or only propose them in result artifacts?
- Should task routing be deterministic from config, or advisory to Claude?
