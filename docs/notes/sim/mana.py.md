## Gotchas
- `ManaPool` kwargs: use `ManaPool()`, `ManaPool(U=1)`, `ManaPool(R=1)`, `ManaPool(generic=2)` — grep existing tests for `ManaPool(` before authoring new tests to confirm current pattern.
- Mana arithmetic: `2R` = 3 mana total (generic=2, R=1). Compute pips + generic before setting test mana amounts.

## Touchpoints
- `ManaPool` class: 6
- `ManaCost` class: 53
- `can_pay_cost(pool, cost)`: 87
- `pay_cost(pool, cost)`: 113
- `choose_mana_color(pool, available_colors)`: 159

## Recent changes
- 2026-05-05: Fixed mana payment to correctly prefer colored pips over generic.
