# Bucket B04: Transmute Costs

Parent: ../workstream.md
State: later
Goal for session: Enforce transmute costs.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- Dizzy Spell and Drift of Phantasms each generate transmute actions directly; resolver currently discards without paying mana.

## Tasks

- [ ] Add focused tests first: Dizzy Spell and Drift of Phantasms transmute are absent without `{1}{U}{U}` and present with `{1}{U}{U}`.
- [ ] Add a resolution test that transmute pays `{1}{U}{U}` before tutoring.
- [ ] Implement the smallest action-generation and resolution fix.
- [ ] Run the focused unit tests.
- [ ] Reproduce `manual_observations.jsonl:100` and `manual_observations_old.jsonl:60` from JSONL-derived states and confirm illegal transmute actions disappear.

## Required touchpoints

- `mtg_sim/scripts/logs/manual_observations.jsonl  line 100  manual note`
  Source bug: Dizzy Spell should not transmute without `{1}{U}{U}`.
- `mtg_sim/scripts/logs/manual_observations_old.jsonl  line 60  manual note`
  Duplicate source bug: Drift of Phantasms should not transmute without `{1}{U}{U}`.
- `mtg_sim/sim/card_behaviors.py  530-563  DizzySpellBehavior.generate_actions`
  Dizzy Spell transmute action generation.
- `mtg_sim/sim/card_behaviors.py  588-604  DriftOfPhantasmsBehavior.generate_actions`
  Drift transmute action generation.
- `mtg_sim/sim/resolver.py  533-546  _resolve_activate_transmute`
  Transmute resolution currently discards and queues tutor.

## Conditional touchpoints

- `mtg_sim/tests/test_tutors.py  150-207  existing transmute tests`
  Read only if adding or updating focused transmute tests there.

## Design direction

- Transmute is an activated ability, not a spell and not a Curiosity trigger.
- The cost is `{1}{U}{U}` for both logged cards; action generation should require it and resolution should pay it.

## Validation

- `python3 -m pytest mtg_sim/tests/<new_or_existing_test_file>.py -k transmute -q`
- JSONL reproduction command or helper output confirming line-100 and old line-60 illegal transmute actions are gone.
- Expected: no transmute with insufficient mana; transmute with sufficient mana pays mana, moves source to graveyard, and queues the tutor choice.

## Done criteria

- [ ] Tasks complete.
- [ ] Validation passes.
- [ ] Bucket `Updates` section records discoveries/gotchas/handoff.
- [ ] Parent workstream progress updated.

## Updates

- 2026-05-13 21:35 Created. Handoff: none yet. Gotchas: none yet.
