# Bucket B01: Scaffold Agents

Parent: ../workstream.md
State: done
Goal for session: Create agent scaffolding.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- This bucket creates the shared filesystem contract before behavior exists.
- It groups static directories, config defaults, schemas, and ignore rules because later buckets depend on these paths.

## Tasks

- [x] Inspect whether `.agents/`, `.claude/skills/outsource-codex/`, `.codex/config.toml`, `AGENTS.md`, and `.gitignore` already exist.
- [x] Create `.agents/` directory structure for tasks, schemas, handoffs, runs, worktrees, locks/status placeholders, and skills.
- [x] Create `.agents/config.toml` with defaults for Codex enabled, sync mode, worktree use, review policy, patch/base-commit policy, and cleanup preservation.
- [x] Create `.agents/tasks.json` as an empty neutral task ledger.
- [x] Create initial JSON schemas for implementation task and implementation result.
- [x] Update `.gitignore` for worktrees and volatile agent files without hiding review artifacts.
- [x] Add minimal placeholder files where needed so directories are tracked.

## Required touchpoints

- `[repo root]  find . -maxdepth 3 \( -path './.agents*' -o -path './.claude*' -o -path './.codex*' -o -name 'AGENTS.md' -o -name '.gitignore' \) -print  existing agent setup`
  Avoid overwriting prior setup.
- `[.gitignore]  full file if present  ignore rules`
  Preserve existing ignores and add only agent-specific entries.
- `[pyproject.toml or setup.cfg or pytest.ini]  grep: pytest|testpaths|pythonpath  test conventions`
  Needed only to align later test commands and repo paths.

## Conditional touchpoints

- `[docs/ or README*]  grep: codex|claude|agent|workstream  existing docs`
  Read only if existing agent docs are found in the required inspection.
- `[.codex/config.toml]  full file if present  Codex config`
  Read only if it already exists; preserve user settings.

## Do-not-read / avoid

- `mtg_sim/sim/*`
  Simulator internals are irrelevant for scaffolding.
- `logs/*.jsonl`
  Policy/manual logs do not affect agent directory setup.

## Design direction

- `base_commit` belongs in every implementation task.
- Default `.agents/config.toml` values: `codex.enabled=true`, `mode="sync"`, `use_worktree=true`, `review.codex_result_review="always"`, `patch.base_commit_policy="warn"`, `cleanup.auto_cleanup_after_success=false`, `cleanup.preserve_artifacts=true`.
- Result schema must allow `proposed_followup_tasks`; Codex may propose but not write tasks.
- Do not overbuild locking/worker-pool fields; include only fields Route B needs plus harmless future-compatible metadata.

## Validation

- `python3 -m json.tool .agents/tasks.json`
- `python3 - <<'PY'` load all `.agents/schemas/*.json` with `json.load`; load `.agents/config.toml` with `tomllib`.
- Expected: all JSON/TOML parse; existing config/docs are preserved.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- [2026-05-13 09:00] Created. Handoff: none yet. Gotchas: none yet.
- [2026-05-13 09:30] Done. Discoveries: `.agents/skills/introspect/` already existed (preserved). `.codex/hooks.json` exists but no `config.toml` (not needed for B01). No pyproject.toml. Handoff: B02 can assume all `.agents/` paths exist and `config.toml`/`tasks.json`/schemas are valid.
