## Helpers defined here
- `_load()`: 19 — loads card library, builds active deck
- `_state_with_hand(hand, mana, cards=None)`: 24 — calls `_build_initial_state` then `draw_cards(state, 3)`
- `_push_spell(state, card_name)`: 34 — appends a StackObject directly (bypasses cast path)
- `_resolve_top(state)`: 243 — resolves the top RESOLVE_STACK_OBJECT action once

## Setup pattern
- Uses `_build_initial_state`: initial BF includes Volcanic Island and Vivi Ornitier.
- `_state_with_hand` draws 3 extra cards on top of starting hand — account for this in library assertions.
- No `_drain_stack` helper; tests use `_resolve_top` or inline RESOLVE_STACK_OBJECT loops.
