# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-turn cEDH spell-chain simulator for the Vivi Ornitier + Curiosity combo. Vivi deals damage each time a noncreature spell is cast; Curiosity-like effects trigger draws on that damage. The sim models the full chain from starting hand/mana until the player wins or bricks.

Win conditions:
- Cast an extra-turn win card (Final Fortune, Last Chance, etc.) — wins on cast, not resolution
- Cast 40+ noncreature spells in one turn

## Commands

```bash
# Run tests
python3 -m pytest mtg_sim/tests/ -q

# Run a single test file
python3 -m pytest mtg_sim/tests/test_basic_brick.py -v

# Single simulation with trace
python3 -m mtg_sim.scripts.run_single --mana-u 1 --mana-r 1 --seed 42

# Single sim with a specific starting hand
python3 -m mtg_sim.scripts.run_single --hand "Rite of Flame" "Lotus Petal" --mana-u 1

# Monte Carlo (1000 runs)
python3 -m mtg_sim.scripts.run_monte_carlo --runs 1000 --mana-u 1

# Inspect a trace from file (if saved)
python3 -m mtg_sim.scripts.inspect_trace
```

Data files live in the project root: `mtg_sim_card_data_v1.csv` and `testdecklist.txt`.

## Architecture

The simulation loop lives in `sim/runner.py:simulate_run`. Each iteration:
1. Check win condition
2. `action_generator.generate_actions(state)` → list of legal `Action` objects
3. `policies.choose_action(state, actions)` → picks best action by score
4. `resolver.resolve_action(state, action)` → mutates `GameState`

**Key data flow:**

- `sim/cards.py` — loads `CardData` from CSV into a global dict; `get_card(name)` is the lookup used everywhere
- `sim/state.py` — `GameState` (mutable, passed everywhere), `Permanent`, `Permission`, `ActionLog`
- `sim/mana.py` — `ManaPool` (U/R/C/ANY fields), `ManaCost`, `can_pay_cost`, `pay_cost`; `ANY` mana is flexible and resolved to a color at spend time
- `sim/actions.py` — `Action`, `CostBundle`, `EffectBundle` dataclasses; action type constants; risk level constants
- `sim/stack.py` — `StackObject` (cards on the stack awaiting resolution)
- `sim/card_behaviors.py` — `CardBehavior` base class + `CARD_BEHAVIORS` dict mapping card name → behavior instance; each behavior implements `generate_actions`, `generate_mana_actions`, `resolve_cast`, `on_enter`
- `sim/action_generator.py` — assembles all legal actions by querying behaviors, checking mana affordability, and parsing alt-cost tokens from the CSV
- `sim/resolver.py` — applies chosen action to state; calls `CARD_BEHAVIORS[name].resolve_cast` or `on_enter` for card-specific effects
- `sim/policies.py` — greedy `score_action` heuristic; higher score = preferred; returns `None` if best score ≤ 0 (brick)
- `sim/trace.py` / `sim/metrics.py` — formatting helpers for output

**Alt costs** are semicolon-delimited tokens in the CSV `alt_costs` column (e.g., `free:pitch_blue; free:pay_life_ignored`). `action_generator._gen_alt_cost_actions` parses these into additional `Action` objects with the appropriate `alt_cost_type` string.

**Curiosity draw** fires immediately on cast of any noncreature spell (not on resolution). `GameState.cards_drawn_per_noncreature_spell = 3 * curiosity_effect_count`. Adding Curiosity/Ophidian Eye/Tandem Lookout increments `curiosity_effect_count`.

**Mana source routing**: `_gen_mana_actions` only iterates permanents with `mana_source_type in ("land", "artifact")`. Vivi's creature tap ability is not modeled as an activated ability — it feeds into Curiosity triggers instead.

## Adding a new card

1. Add a row to `mtg_sim_card_data_v1.csv` with the card's mana cost, type flags, and alt_costs
2. If the card has non-trivial behavior (ETB, resolution effect, mana production): add a `CardBehavior` subclass in `card_behaviors.py` and register it in `CARD_BEHAVIORS`
3. If no special behavior needed, the default action generator handles it automatically for lands and simple artifact mana sources
