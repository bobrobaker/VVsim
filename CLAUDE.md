# CLAUDE.md

Project: single-turn cEDH spell-chain simulator for Vivi Ornitier + Curiosity.

Goal: simulate whether a starting state can chain enough spells to win.
Win conditions:
- cast an extra-turn win card, e.g. Final Fortune / Last Chance
- cast 40+ noncreature spells in one turn

## Commands

All tests: `python3 -m pytest mtg_sim/tests/ -q`
One test: `python3 -m pytest mtg_sim/tests/<test_file>.py -v`
Single trace: `python3 -m mtg_sim.scripts.run_single --mana-u 1 --mana-r 1 --seed 42`
Monte Carlo: `python3 -m mtg_sim.scripts.run_monte_carlo --runs 1000 --mana-u 1`

## Core architecture

Main loop: `sim/runner.py:simulate_run`

Flow:
1. check win/brick
2. generate legal actions
3. choose action manually or by policy
4. resolve action
5. repeat

Key files:
- `sim/state.py`: GameState, zones, permanents, permissions, logs
- `sim/actions.py`: Action / CostBundle / EffectBundle
- `sim/stack.py`: StackObject and stack representation
- `sim/action_generator.py`: assembles legal actions
- `sim/card_behaviors.py`: card-specific action generation and resolution
- `sim/resolver.py`: applies chosen action to GameState
- `sim/policies.py`: greedy action scoring
- `sim/mana.py`: mana pool and cost payment

## Design rules

- Manual mode and policy mode should use the same legal action list when practical.
- Resolution should execute choices encoded in Actions or explicit pending choices.
- Use readable names in traces/manual mode, not object IDs.
- Use focused tests for each simulator rule/card bug.
- For architectural questions, inspect first and recommend the smallest safe change before refactoring.

## Context hygiene

- Grep for exact line numbers first, then read only those ranges, then write. Never read a whole file to find a section.
- Before reading a file over ~150 lines, explain why the full file is needed.
- Do not inspect unrelated files.
- After each focused task, run the smallest relevant test first, then broader tests if needed.
- When starting a chunk, provide line anchors for the touch points (e.g. "imprint block is lines 61–84") to skip the exploration phase entirely.

## Current Status

Chunks 5–6 complete: all card-specific action generation moved out of `action_generator.py` into `CardBehavior` subclasses.

Sentinel refactor complete:
- `CardBehavior.generate_actions()` returns `None` by default (delegate to generic scaffolding) or a `list[Action]` to own generation.
- `owns_action_generation` flag removed entirely from all subclasses.
- Dispatcher in `action_generator._gen_cast_actions` (line ~142): calls `beh.generate_actions()`, uses result if not None, else falls through to `_gen_normal_and_alt_cast_actions`.
- Behaviors that override `generate_actions`: TwistedImageBehavior, RepealBehavior, MoggSalvageBehavior, MentalMisstepBehavior, MisdirectionBehavior, SimianSpiritGuideBehavior.
- `_gen_alt_cost_actions` has no card-name branches; remaining alt-cost tokens are generic.
- `CardBehavior.generate_pending_actions(state, choice)` handles card-specific pending choices. ChromeMoxBehavior (imprint) and MoxDiamondBehavior (discard) implement it; `_gen_pending_choice_actions` dispatches by `choice.source_card`.

Architecture direction (agreed):
- `action_generator.py` owns generic scaffolding: iterate zones, enforce timing/stack rules, call behavior hooks.
- Each card behavior owns both action generation (when/what) and resolution (what happens).
- Long-term: split into per-card files so each card's full behavior (generation + resolution + tests) can be handed off cleanly. Deferred until individual behaviors grow large enough to warrant it (~half of card behaviors are not well-implemented and will need test coverage first).
- `None`-sentinel pattern is the hook: any behavior can take ownership of its card's action generation by returning a list from `generate_actions()`.

Known design direction:
- Manual mode and policy mode should use the same legal action list when possible.
- Manual/debug output should be readable and show relevant zones/targets.

Next task:
- Incrementally move remaining card-specific logic from `_gen_normal_and_alt_cast_actions` and `_gen_alt_cost_actions` into behavior `generate_actions()` overrides, one card at a time, with test coverage.
- Prioritize cards with known behavior gaps (to be enumerated with user).