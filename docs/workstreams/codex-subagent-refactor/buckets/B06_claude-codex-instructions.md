# Bucket B06: Claude Codex Instructions

Parent: ../workstream.md
State: done
Goal for session: Add agent instructions.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- This bucket adds human/model-facing instructions after deterministic scripts exist.
- It groups Claude orchestration skill, Codex implementer rules, and minimal `AGENTS.md` wording.

## Tasks

- [x] Create `.claude/skills/outsource-codex/SKILL.md`.
- [x] Teach the Claude skill to create/use one task, call runner, inspect result/diff, call apply script, and offer cleanup.
- [x] Create or update root `AGENTS.md` with normal Codex project rules plus strict non-interactive task-mode behavior.
- [x] Create `.agents/skills/codex-implementer/SKILL.md` if useful for Codex-side task execution.
- [x] Ensure Codex instructions say: JSON result only, obey task scope, run validation, propose follow-ups only in result JSON, do not add tasks directly.
- [x] Keep instructions concise; scripts own mechanics.

## Required touchpoints

- `[scripts/agents/run_codex_task.py]  grep: argparse|usage|main  runner invocation`
  Claude skill must call real script flags.
- `[scripts/agents/apply_codex_patch.py]  grep: argparse|usage|main  apply invocation`
  Claude skill must apply correctly.
- `[scripts/agents/cleanup_codex_task.py]  grep: argparse|usage|main  cleanup invocation`
  Claude skill should know cleanup path.
- `[.agents/config.toml]  full file  user-changeable knobs`
  Document how skill obeys config.
- `[AGENTS.md]  full file if present  existing Codex guidance`
  Preserve existing repo instructions.

## Conditional touchpoints

- `[CLAUDE.md]  grep: codex|agent|task|workstream  existing Claude guidance`
  Read only if adding a brief cross-reference is appropriate.
- `[.claude/skills/]  find .claude/skills -maxdepth 2 -type f  existing skills`
  Read only if skills directory already exists.

## Do-not-read / avoid

- `mtg_sim/sim/*`
  Agent instructions should not inspect simulator implementation.
- `.agents/runs/*`
  Runtime artifacts are not needed unless testing the skill manually.

## Design direction

- Claude skill is the user-facing entry point.
- Do not require the user to remember runner/apply/cleanup order.
- However, keep runner/apply/cleanup as standalone scripts for recovery and debugging.
- `AGENTS.md` should only make strict behavior conditional: if launched by task artifact or runner, act as bounded implementer; otherwise use normal Codex behavior.
- Codex may propose but not write downstream LLM tasks.

## Validation

- Read generated skill files for path/flag accuracy against scripts.
- Optional manual prompt dry-run: ask Claude to summarize how it would outsource a fake task without executing.
- Expected: instructions match actual script names, paths, config keys, and Codex role boundaries.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- [2026-05-13 09:00] Created. Handoff: none yet. Gotchas: none yet.
- [2026-05-13] Done. Updated SKILL.md with full flow, CLI flags, Python import paths, config table, and review checklist. Created .agents/skills/codex-implementer/SKILL.md with task-mode detection and ImplementationResult guidance. Added "Codex Task Mode" section to AGENTS.md. Gotcha: apply/cleanup scripts have no CLI — they are Python library functions only; skill uses import paths not shell commands.
