# Bucket B01: Sorcery Stack Timing

Parent: ../workstream.md
State: done
Goal for session: Block sorceries on stack.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- Wild Ride is registered as generic `NullBehavior`, so this bucket is about generic spell timing and any card-specific bypass.

## Tasks

- [x] Add a focused test first: Wild Ride is not generated while any stack object exists.
- [x] Implement the smallest legality fix if the test fails.
- [x] Run the focused unit test.
- [x] Reproduce `manual_observations.jsonl:51` from a JSONL-derived state and confirm Wild Ride action index 0 no longer appears.

## Required touchpoints

- `mtg_sim/scripts/logs/manual_observations.jsonl  line 51  manual note`
  Source bug: Wild Ride is a sorcery and should not be castable while cards are on stack.
- `mtg_sim/sim/action_generator.py  230-238  _gen_normal_and_alt_cast_actions`
  Generic sorcery-speed gate.
- `mtg_sim/sim/card_behaviors.py  grep "Wild Ride"  CARD_BEHAVIORS`
  Confirms Wild Ride uses generic/null behavior rather than a special override.

## Conditional touchpoints

- `mtg_sim/tests/test_misc_spells.py  1-45  _state helper`
  Read only if reusing existing helper patterns for the unit test.

## Design direction

- A sorcery-speed card should not generate a cast action when `state.stack` is nonempty unless an existing modeled effect explicitly grants instant timing.
- Prefer a regression test that builds a small stack directly; the JSONL-derived reproduction is a second check, not the only proof.

## Validation

- `python3 -m pytest mtg_sim/tests/<new_or_existing_test_file>.py -k wild_ride -q`
- JSONL reproduction command or helper output confirming no `source_card == "Wild Ride"` action in the line-51 state.
- Expected: Wild Ride has no legal cast actions with stack nonempty.

## Done criteria

- [x] Tasks complete.
- [x] Validation passes.
- [x] Bucket `Updates` section records discoveries/gotchas/handoff.
- [x] Parent workstream progress updated.

## Updates

- 2026-05-13 21:35 Created. Handoff: none yet. Gotchas: none yet.
- 2026-05-13 Completed. Fix: `card_library.csv` Wild Ride `card_types` changed from `Instant` to `Sorcery`; sorcery-speed gate in `action_generator.py:_gen_normal_and_alt_cast_actions` already correct. Tests added: `test_wild_ride_not_castable_with_stack_nonempty` (stack = Mishra's Bauble, reproduces line-51 state), `test_wild_ride_castable_with_empty_stack`. 418/418 pass. Gotcha: bucket description said "Wild Ride is a sorcery" but card_library.csv had it as `Instant` — the fix was in data, not code. Codex outsource pipeline also had a bug (empty patch from `format-patch`/`<base>..HEAD`); fixed harness in same session. Handoff: B02 depends on B01 (done); proceed to B02.
