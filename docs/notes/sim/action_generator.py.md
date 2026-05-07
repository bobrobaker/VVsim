## Gotchas
- Sequential narrow reads waste tokens. If reading lines N–M, check whether the function extends past M before issuing the read — extend the range first.
- Some cards have dual-path action generation: both `CardBehavior.generate_actions()` and `_gen_special_hand_actions()` (e.g., SSG). Grep for `generate_actions.*card_name` before writing count-sensitive tests.

## Touchpoints
- `generate_actions(state)` entry point: 38
- `_gen_pending_choice_actions`: 56; `_gen_cast_actions`: 193
- `_gen_normal_and_alt_cast_actions`: 230; alt-cost parsing: `_gen_alt_cost_actions`: 332
- `_gen_mana_actions`: 524; `_gen_activate_actions`: 609
- `_gen_special_hand_actions`: 620; target helpers: 633–797

## Recent changes
- 2026-05-05: Added flashback alt-cost generation; SSG dual-path is pre-existing behavior.
