## Gotchas
- `_build_initial_state` always enters Volcanic Island tapped; tests asserting mana or tapped state must account for this.
- `manual_mode` flag lives on `RunConfig`, not `GameState`; display logic is in `_manual_choose_action`, not the main loop.

## Touchpoints
- `RunConfig` dataclass: 26; `RunResult` dataclass: 46
- `simulate_run` (main loop): 63; win/brick check: 145
- `_manual_choose_action` (display + input): 186
- `_build_initial_state`: 242

## Recent changes
- 2026-05-07: Added `Exile:` display block to `_manual_choose_action` (lines 199–200); printed only when nonempty.
