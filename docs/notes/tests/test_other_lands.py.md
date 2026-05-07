## Helpers defined here
- `_make_state(**kwargs)`: 14 — creates `GameState` directly with empty defaults (no Volcanic Island)
- `_mana_actions(state)`: 20 — filters for `ACTIVATE_MANA_ABILITY` actions
- `_land_play_actions(state)`: 24 — filters for `PLAY_LAND` actions
- `_land_type_actions(state)`: 28 — filters for `CHOOSE_LAND_TYPE` actions

## Setup pattern
- Uses `GameState(**defaults)` directly — initial BF is empty by default (no Volcanic Island, no Vivi).
- Add permanents explicitly: `_make_state(battlefield=[Permanent("Ancient Tomb")])`.
- `ManaPool` not used in setup (no starting mana); floating mana checked via `state.floating_mana`.
