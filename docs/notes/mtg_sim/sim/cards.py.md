---
name: cards.py notes
description: Gotchas and touchpoints for mtg_sim/sim/cards.py (CardData, get_card, card_library.csv)
type: project
---

## Touchpoints

- `get_card(name)` → `CardData | None`; returns `None` for unknown names (does not raise)
- `CardData.is_instant`, `.is_sorcery`, `.is_creature`, `.is_land` — derived from `card_types` field (e.g. `"Instant"`, `"Sorcery"`)
- `CardData.has_flash` — explicit boolean column; separate from `is_instant`

## Gotchas

- Card data lives in `card_library.csv` at the **repo root** (not in `mtg_sim/`, `sim/`, or `data/`). Key columns: `card_id, name, mana_cost, mv, colors, pip_u, pip_r, generic_mana, pip_ur_hybrid, x_in_cost, card_types, …`. Use `grep "CardName" card_library.csv` to inspect a card's raw data without reading code.
- To check pip counts before writing a test, run: `python3 -c "from mtg_sim.sim.cards import get_card; c=get_card('Name'); print(c.pip_u, c.pip_r, c.generic_mana)"`. Wrong pip counts have caused multi-step debug cycles.
