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

Architecture direction (agreed):
- `action_generator.py` owns generic scaffolding: iterate zones, enforce timing/stack rules, call behavior hooks.
- Each card behavior owns both action generation (when/what) and resolution (what happens).
- Long-term: split into per-card files so each card's full behavior (generation + resolution + tests) can be handed off cleanly. Deferred until individual behaviors grow large enough to warrant it (~half of card behaviors are not well-implemented and will need test coverage first).
- `None`-sentinel pattern is the hook: any behavior can take ownership of its card's action generation by returning a list from `generate_actions()`.

Long term todo:
- card refining: Use docs to describe the intended behavior of each card specific card behavior refining: check unimplemented card tokens
- policy refining: refactor policy to have weights that are in text editable policy config file, in manual mode when reporting actions for the user to choose also display what the policies system thinks of each choice, if then you choose not the top policy manual mode will prompt you as to why and it will log that in a policy-adjustment log + any relevant info about the state. Then review the policy log with claude to refine policy behavior

Card library / active deck:
- `card_library.csv` — all cards the sim knows about (ID 1 = Vivi, always present)
- Active deck = list of card IDs; default is IDs 2–100; configured via `--deck-ids` CLI flag or by passing a list to `build_active_deck()`
- `cards.py`: `load_card_library()` loads CSV, `build_active_deck(card_ids)` validates IDs and warns on missing behaviors
- Cards missing from CSV → error; cards missing from `card_behaviors.py` → warning only (generic rules apply)

Next task:
- refactor wincon/extra turn cards to use language "terminator" since we'll be adding more items to that conceptual cluster that aren't strictly extra turn spells but we can reasonably assume end the simulation with a win
- Prep for specific card behavior refining