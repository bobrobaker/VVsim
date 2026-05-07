# CLAUDE.md

Project: single-turn cEDH spell-chain simulator for Vivi Ornitier + Curiosity.

Goal: simulate whether a starting state can chain enough spells to "Win" 

## Commands

All tests: `python3 -m pytest mtg_sim/tests/ -q`
All tests, suppress known warnings: `python3 -m pytest mtg_sim/tests/ -q -W ignore::UserWarning`
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
- `sim/action_generator.py`: generic legal-action scaffolding
- `sim/card_behaviors.py`: card-specific action generation and resolution
- `sim/resolver.py`: applies chosen action to GameState
- `sim/policies.py`: greedy action scoring
- `sim/mana.py`: mana pool and cost payment

## Design rules

- Manual mode and policy mode should use the same legal action list when practical.
- `action_generator.py` owns generic scaffolding: iterate zones, enforce timing/stack rules, call behavior hooks.
- Card behavior owns card-specific action generation and resolution.
- Use readable names in traces/manual mode, not object IDs.

## Context hygiene

- Use grep for symbol, field, registry, constant, and call-site checks before reading code.
- Read only relevant ranges, but prefer one complete function/class range over multiple partial reads.
- Do not read a whole file to find a section.
- Before reading >150 lines, explain why the full range is needed.
- Separate required reads from conditional reads. Read conditional files only when the change touches that concern.
- Do not inspect unrelated files.
- Do not re-read information already answered by grep or prior output in the same session.
- When starting a chunk, provide line anchors for touchpoints when possible to skip exploration.
- After each focused task, run the smallest relevant test first, then broader tests only if needed.
- For broad pytest runs, suppress known noisy warnings unless investigating warnings.
- CompanionDocs: before editing any `mtg_sim/` file, `.claude/rules/sim-notes.md` auto-loads a matching `docs/notes/` file with Touchpoints and Gotchas.
- Testing rules are in `.claude/rules/tests.md` (auto-loaded for `mtg_sim/tests/**`).

## Card-specific implementation direction

See `docs/workstream_card_specific.md` for the full bucket workflow.

- Prefer card-specific logic in `card_behaviors.py`.
- Keep `action_generator.py` as generic scaffolding where practical.
- If a card needs special action generation, prefer `CardBehavior.generate_actions(...)`.
- If a card needs special resolution, prefer `CardBehavior.resolve_cast(...)`.
- If a card needs battlefield or mana behavior, use `generate_mana_actions(...)`, `generate_activate_actions(...)`, or `on_enter(...)`.
- Noncreature spell casts should still trigger Vivi/Curiosity through existing cast logic.
- Permanent spells should enter battlefield through existing resolver logic unless the card says otherwise.
- Nonpermanent spells should go to graveyard unless the card says otherwise.
- Do not model omitted real-card behavior unless `docs/card_specifics.md` says to model it.
- Add `Comments:` text from `docs/card_specifics.md` as implementation comments when it explains a simulator simplification.

## For policy work

- Inspect `sim/policies.py` and the relevant action/state fields first.
- Keep policy scoring separate from legality.
- Do not fix legality bugs in policy code.
- Prefer small scoring changes with focused tests.

## Backlog

When you notice an opportunity to refactor, improve architecture, reduce technical debt, or use a better long-term approach — but it is not needed for the current task — create a task via TaskCreate with status `pending`, subject prefixed `[SUGGESTION]`, and a structured description following `docs/backlog_instructions.md`.

Do not create backlog items for low-value style nits. Only medium- or high-value improvements.

Human todos: `docs/todo.md`. Task backlog: via TaskCreate (stored in `~/.claude/tasks/`).

## Planned extensions

These constrain current architectural decisions:
- Policy weights will move to a text-editable config file; keep scoring logic separate from action generation.
- Card behaviors may eventually split into per-card files; keep each behavior self-contained.
