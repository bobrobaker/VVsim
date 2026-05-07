## Gotchas
- `MishraBaubleBehavior`, `UrzaBaubleBehavior`, `LodestoneBaubleBehavior`, `VexingBaubleBehavior` are each defined TWICE (~758 and ~1213+). Python uses the second definition; the first is dead code. Only edit/read the 1213+ versions.
- SSG (Simian Spirit Guide) generates actions via both `generate_actions()` AND `_gen_special_hand_actions()` — double-count risk in tests.
- Registry: grep `CARD_BEHAVIORS` instead of reading the end of the file.

## Touchpoints
- `CardBehavior` base: 28; mana-source behaviors: 52–358
- Tutors: 449–519; misc/bounce spells: 824–975
- Counterspell behaviors: 1311–1680; Bauble activate-actions: 1213–1286
- MDFC land behaviors: 1810–1975; CARD_BEHAVIORS registry: grep for it

## Recent changes
- 2026-05-05: Added misc-spells behaviors (Snapback, Boomerang, Cave In, etc.).
- 2026-05-05: Fixed Rite of Flame, Chrome Mox imprint, Paradise Mantle; added flashback graveyard generation.
