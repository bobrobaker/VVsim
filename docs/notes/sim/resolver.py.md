## Gotchas
- Functions often run longer than a narrow read range. Always extend the range to include the full function before issuing the read.
- Don't re-read action type constants after grep already showed them inline.
- `alt_cost_type` handlers: grep `alt_cost_type` in this file to see all 8 handlers at once before adding a new one.

## Touchpoints
- `draw_cards(state, n)`: 23
- `resolve_action(state, action)` dispatch: 37
- `_resolve_cast_spell`: 87; `_resolve_stack_object`: 202
- `_enter_battlefield(state, card_name, obj)`: 251
- `_resolve_play_land`: 272; `_resolve_activate_mana`: 304
- Pending-choice resolvers (fetch, imprint, tutor, etc.): 407–572

## Recent changes
- 2026-05-05: Added `equip_mantle` and `tap_mantle_vivi` alt-cost handlers.
