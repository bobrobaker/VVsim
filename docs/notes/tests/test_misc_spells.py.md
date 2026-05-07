## Helpers defined here
- `_load()`: 18 — loads card library, builds active deck
- `_drain_stack(state)`: 23 — resolves all RESOLVE_STACK_OBJECT actions until stack empty
- `_state(hand, mana, battlefield, library)`: 33 — calls `_build_initial_state`; accepts optional `battlefield` list and `library` list overrides

## Setup pattern
- Uses `_build_initial_state`: initial BF includes Volcanic Island and Vivi Ornitier.
- Extra permanents can be appended via `battlefield` kwarg (appended to initial state, not replacing it).
- `_drain_stack` is the canonical stack-drain helper for this file — reuse it.
