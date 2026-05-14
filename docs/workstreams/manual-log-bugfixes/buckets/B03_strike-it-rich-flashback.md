# Bucket B03: Strike It Rich Flashback

Parent: ../workstream.md
State: done
Goal for session: Fix flashback cost/zone.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- Strike It Rich uses generic flashback generation plus generic flashback zone movement, with a small card-specific resolve effect.

## Tasks

- [x] Add focused tests first: Strike It Rich flashback costs `{2}{R}` from graveyard and moves to exile after resolution.
- [x] Implement the smallest generation/resolution fix.
- [x] Run the focused unit test.
- [x] Reproduce `manual_observations.jsonl:100` from a JSONL-derived state and confirm Strike It Rich is not castable with only `R`.

## Required touchpoints

- `mtg_sim/scripts/logs/manual_observations.jsonl  line 100  manual note`
  Source bug: Strike It Rich from graveyard should cost `{2}{R}`, then go to exile.
- `mtg_sim/sim/action_generator.py  216-225  graveyard flashback generation`
  Graveyard cast path dispatch.
- `mtg_sim/sim/action_generator.py  411-430  alt:flashback_ parser`
  Flashback mana-cost parser and action metadata.
- `mtg_sim/sim/resolver.py  137-146  _resolve_cast_spell source-zone removal`
  Cast from graveyard source removal.
- `mtg_sim/sim/resolver.py  232-244  _resolve_stack_object final zone`
  Flashback final-zone movement to exile.
- `mtg_sim/sim/card_behaviors.py  746-754  StrikeItRichBehavior`
  Card-specific treasure creation.

## Conditional touchpoints

- `card_library.csv  grep "Strike It Rich"  CSV alt_costs`
  Read only to verify encoded flashback cost before changing parser or tests.

## Design direction

- Do not make graveyard Strike It Rich use its hand mana cost.
- Ensure the same stack object that resolves remembers `alt_cost_used == "flashback"`.

## Validation

- `python3 -m pytest mtg_sim/tests/<new_or_existing_test_file>.py -k strike_it_rich -q`
- JSONL reproduction command or helper output confirming no flashback action with only `R`, and flashback resolves to exile when `{2}{R}` is available.
- Expected: flashback action requires three total mana including red and final zone is exile.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- 2026-05-13 21:35 Created. Handoff: none yet. Gotchas: none yet.
- 2026-05-13 B03 done. Fixed graveyard flashback loop in action_generator.py:225 — replaced `_gen_normal_and_alt_cast_actions` call with targeted flashback-only token loop plus sorcery-speed gate. Zone movement (graveyard → exile) was already correct in resolver.py. 3 new tests added (no action with R=1, flashback requires {2}{R}, resolves to exile). 419 tests pass. Outsourced via Codex (b03-strike-it-rich-flashback-20260513).
