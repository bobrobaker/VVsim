## Touchpoints

- `cleanup()` — public entry point; removes worktree/branch/lock, optionally deletes artifacts, updates status to `cleaned`
- `_ARTIFACT_SUFFIXES` — controls which run files are preserved by default (`.run.json`, `.diff`, `.patch`, `.result.json`)

## Gotchas

- No CLI entrypoint — library only; call `from scripts.agents.cleanup_codex_task import cleanup` (no argparse/main)
- `git worktree remove --force` only works on git-tracked worktrees; manually created directories are silently skipped (not an error)
- Status update is best-effort: missing task in ledger logs an error but does not raise
- Safe to rerun: all missing paths are skipped, not errors

## Recent changes

- Created: worktree/branch/lock removal, artifact preservation by default, `delete_artifacts=True` opt-in
