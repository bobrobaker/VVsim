## Gotchas
- `_build_initial_state` always enters Volcanic Island tapped; tests asserting mana or tapped state must account for this.
- `manual_mode` flag lives on `RunConfig`, not `GameState`; display logic is in `_manual_choose_action`, not the main loop.
- `cfg` is loaded once per `simulate_run` call via `load_policy_config`; changing the TOML mid-run has no effect.

## Touchpoints
- `RunConfig` dataclass: 28; `RunResult` dataclass: 52
- `simulate_run` (main loop): 69; cfg loaded at ~97; win/brick check: ~152
- `_manual_choose_action` (display + input + JSONL): 198
- `_write_adjustment_log`: 286; `_state_snapshot`: 293
- `_build_initial_state`: 331

## Recent changes
- 2026-05-07: `_manual_choose_action` now calls `rank_actions`, shows scores/delta/reasons, prompts for reason on non-top choice, writes JSONL via `_write_adjustment_log`. `RunConfig` gained `policy_config_path` and `adjustment_log_path`.
- 2026-05-07: Added `Exile:` display block to `_manual_choose_action`; printed only when nonempty.
