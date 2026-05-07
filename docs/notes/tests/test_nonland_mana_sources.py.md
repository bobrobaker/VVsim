## Helpers defined here
- `_make_state(**kwargs)`: 14 — creates `GameState` directly with empty defaults (no Volcanic Island)
- `_mana_actions(state)`: 20 — filters for `ACTIVATE_MANA_ABILITY`, `SACRIFICE_FOR_MANA`, `EXILE_FOR_MANA`
- `_actions_for(state, source)`: 24 — filters `_mana_actions` by `action.source_card == source`

## Setup pattern
- Uses `GameState(**defaults)` directly — initial BF is empty by default (no Volcanic Island, no Vivi).
- Add permanents explicitly: `_make_state(battlefield=[Permanent("Sol Ring")])`.
- ManaPool usage: `ManaPool()` (empty), `ManaPool(U=1)`, `ManaPool(generic=2)` — grep file for pattern before writing.
