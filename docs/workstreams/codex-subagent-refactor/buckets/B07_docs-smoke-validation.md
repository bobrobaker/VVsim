# Bucket B07: Docs Smoke Validation

Parent: ../workstream.md
State: later
Goal for session: Document and smoke-test.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- This bucket validates the whole Route B flow and writes the permanent user-facing docs.
- It should not add new core mechanics unless smoke testing reveals a blocking gap.

## Tasks

- [x] Create `.agents/README.md` as permanent operational documentation.
- [x] Ensure `docs/workstreams/codex-subagent-refactor/how_to_use.md` or equivalent points to permanent docs and explains current workflow.
- [x] Document enable/disable knobs, review policy, base-commit policy, dry-run mode, artifact locations, patch apply, cleanup, and troubleshooting.
- [x] Run full dry-run Route B flow with fake Codex.
- [ ] If safe and desired, run a minimal real `codex exec` smoke that does not edit simulator code.
- [x] Update this bucket and parent workstream with final gotchas/handoff.

## Required touchpoints

- `[.agents/README.md]  full file if present  permanent docs`
  Preserve or create operational docs.
- `[docs/workstreams/codex-subagent-refactor/how_to_use.md]  full file if present  workstream docs`
  Align generated planning docs with implemented commands.
- `[.agents/config.toml]  full file  documented knobs`
  Docs must reflect real config.
- `[scripts/agents/]  grep: argparse|usage|--help  script interfaces`
  Verify commands and flags.

## Conditional touchpoints

- `[AGENTS.md]  grep: Non-interactive task mode|Codex  Codex instructions`
  Read if docs mention Codex behavior.
- `[.claude/skills/outsource-codex/SKILL.md]  full file  Claude entry point`
  Read if docs mention skill usage.
- `[.agents/runs/*.run.json]  sample latest if present  artifact example`
  Read only after smoke run.

## Do-not-read / avoid

- `mtg_sim/sim/*`
  Smoke should use fake/no-op tasks unless explicitly validating a real simulator task.
- `logs/*.jsonl`
  Policy/manual logs are unrelated to Route B mechanics.

## Design direction

- Docs should explain worktrees for a Git-novice user.
- Normal use should be skill-driven; manual commands are for recovery and debugging.
- Make clear that Codex output is isolated until patch application.
- Preserve upgrade path to future worker queue/pool but do not document it as implemented.

## Validation

- `python3 -m pytest tests/agents/ -q`
- Run dry-run Route B end-to-end and verify: task -> worktree -> JSON result -> diff/patch -> apply -> cleanup.
- Expected: docs match actual commands; dry-run flow completes without real Codex.

## Done criteria

- [x] Tasks complete (real Codex smoke deferred — not needed to validate Route B mechanics).
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- [2026-05-13] Done. Created `.agents/README.md` (permanent ops docs). Updated `how_to_use.md` to reflect implemented commands. Dry-run end-to-end flow completed: task → worktree → result JSON → diff/patch → apply (empty patch) → cleanup. Fixed two bugs in `apply_codex_patch.py`: (1) `patch_path` was read from `run_meta["artifacts"]["patch_path"]` but run metadata stores it at top level; (2) empty patch (dry-run) raised PatchCheckError — now short-circuits to `status: applied`. 72 agents tests pass. Real Codex smoke deferred (not needed to validate mechanics).
- [2026-05-13 09:00] Created. Handoff: none yet. Gotchas: none yet.
