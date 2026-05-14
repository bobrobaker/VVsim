# Bucket B05: Misdirection Player Targets

Parent: ../workstream.md
State: later
Goal for session: Recognize player-target spells.
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- Misdirection action generation depends on stack-object target metadata; Gitaxian Probe currently resolves as a player-targeting spell conceptually but may not put a target on stack.

## Tasks

- [ ] Add a focused test first: with Gitaxian Probe on stack and a blue pitch card in hand, Misdirection has a pitch-blue action targeting Gitaxian Probe.
- [ ] Implement the smallest target metadata/action-generation fix.
- [ ] Run the focused unit test.
- [ ] Reproduce `manual_observations.jsonl:16` from a JSONL-derived state and confirm Misdirection appears.

## Required touchpoints

- `mtg_sim/scripts/logs/manual_observations.jsonl  line 16  manual note`
  Source bug: Misdirection missing; Gitaxian Probe targets players and should count as a target spell.
- `mtg_sim/sim/action_generator.py  660-666  _get_single_target_stack_objects`
  Current Misdirection target detector requires exactly one stack target.
- `mtg_sim/sim/card_behaviors.py  635-641  GitaxianProbeBehavior`
  Probe card-specific behavior and target simplification.
- `mtg_sim/sim/card_behaviors.py  1446-1484  MisdirectionBehavior.generate_actions`
  Misdirection normal and pitch-blue action generation.
- `mtg_sim/sim/resolver.py  154-164  StackObject construction in _resolve_cast_spell`
  Stack target metadata source when spells are cast.

## Conditional touchpoints

- `mtg_sim/sim/stack.py  6-19  StackObject`
  Read only if adding explicit target metadata or a marker for implicit player targets.
- `mtg_sim/tests/test_counterspells.py  grep "Misdirection"  existing tests`
  Read only if adding the focused test near counterspell coverage.

## Do-not-read / avoid

- `docs/specs/card_specifics.md`
  Do not broaden into full player-target modeling unless a local card-specific comment explicitly requires it.

## Design direction

- Model only enough target metadata for Misdirection legality with known player-targeting spells like Gitaxian Probe.
- Do not make untargeted spells generally targetable by Misdirection.

## Validation

- `python3 -m pytest mtg_sim/tests/<new_or_existing_test_file>.py -k misdirection -q`
- JSONL reproduction command or helper output confirming a Misdirection pitch action exists in the line-16 state.
- Expected: Misdirection can target Gitaxian Probe on stack when a blue pitch card is available.

## Done criteria

- [ ] Tasks complete.
- [ ] Validation passes.
- [ ] Bucket `Updates` section records discoveries/gotchas/handoff.
- [ ] Parent workstream progress updated.

## Updates

- 2026-05-13 21:35 Created. Handoff: none yet. Gotchas: none yet.
