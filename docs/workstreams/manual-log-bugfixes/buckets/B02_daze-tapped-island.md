# Bucket B02: Daze Tapped Island

Parent: ../workstream.md
State: done
Goal for session: Allow tapped Island return.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- Daze alternate cost already exists; the logged issue is that candidate Island selection excludes tapped Islands.

## Tasks

- [ ] Add a focused test first: Daze can be cast by returning tapped Volcanic Island while a spell is on stack.
- [ ] Implement the smallest action-generation fix.
- [ ] Run the focused unit test.
- [ ] Reproduce `manual_observations.jsonl:51` from a JSONL-derived state and confirm a Daze return-island action appears.

## Required touchpoints

- `mtg_sim/scripts/logs/manual_observations.jsonl  line 51  manual note`
  Source bug: Daze missing; tapped Volcanic Island should count as an Island to return.
- `mtg_sim/sim/card_behaviors.py  1489-1523  DazeBehavior.generate_actions`
  Daze action construction and alternate cost metadata.
- `mtg_sim/sim/action_generator.py  790-801  _is_island/_islands_on_battlefield`
  Current Island helper excludes tapped permanents.
- `mtg_sim/sim/resolver.py  115-120  Daze return-island payment`
  Resolution already removes the selected permanent and returns it to hand.

## Conditional touchpoints

- `mtg_sim/tests/test_counterspells.py  grep "Daze"  existing Daze tests`
  Read only if adding the focused test near existing counterspell tests.

## Design direction

- For Daze, returning an Island does not require tapping it; tapped Volcanic Island should be eligible.
- Avoid changing other mana-action helpers that rely on untapped land filtering.

## Validation

- `python3 -m pytest mtg_sim/tests/<new_or_existing_test_file>.py -k daze -q`
- JSONL reproduction command or helper output confirming a legal Daze action in the line-51 state.
- Expected: Daze appears with `alt_cost_type == "return_island"` and returns Volcanic Island on resolution.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- 2026-05-13 21:35 Created. Handoff: none yet. Gotchas: none yet.
- 2026-05-13 Done. Removed `and not p.tapped` filter from `_islands_on_battlefield` in `action_generator.py:801`. This function is only called from `DazeBehavior`; no other callers use it. Added `test_daze_alt_cost_tapped_island_eligible` in `test_counterspells.py`. Gotcha: default `_build_initial_state` already places a tapped Volcanic Island on battlefield — no need to add another in the test. JSONL-51 reproduction confirmed: 1 return-island action appears. 419 tests pass. Next: B03.
