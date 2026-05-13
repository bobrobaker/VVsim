## Touchpoints

- `apply()` — public entry point; reads run metadata, enforces review/base-commit policy, applies patch, runs validation
- `_check_review_policy()` — raises `ReviewRequiredError` unless `force=True`
- `_check_base_commit()` — compares task `base_commit` to `HEAD`; behavior controlled by `base_commit_policy`

## Gotchas

- No CLI entrypoint — library only; call `from scripts.agents.apply_codex_patch import apply` (no argparse/main)
- `patch_path` is at the **top level** of run metadata (`run_meta["patch_path"]`), NOT under `run_meta["artifacts"]` — reading the sub-key silently returns `""` and causes a confusing `FileNotFoundError`
- An **empty patch** (dry-run or no-op Codex) causes `git apply --check` to raise `PatchCheckError`; must short-circuit before the git check when `patch_path.stat().st_size == 0`
- `tomllib` is stdlib in Python 3.11+; `tomli` fallback import is present for 3.10

## Recent changes

- Fixed: `patch_path` key lookup (`artifacts` sub-key → top-level); added empty-patch short-circuit before git apply check
