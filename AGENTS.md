# AGENTS.md

Project: single-turn cEDH spell-chain simulator for Vivi Ornitier + Curiosity.

Goal: simulate whether a starting state can chain enough spells to "Win".

## Project Identity

- This is a Python Magic: The Gathering simulation project.
- Correctness, reproducibility, and small reviewable diffs matter more than broad refactors.
- Preserve game semantics carefully; passing tests is necessary but not always sufficient.
- Do not silently encode strategic policy preference as game rules.
- Do not silently change public behavior unless the task explicitly asks for it.

## Commands

- All tests: `python3 -m pytest mtg_sim/tests/ -q`
- All tests, suppress known warnings: `python3 -m pytest mtg_sim/tests/ -q -W ignore::UserWarning`
- One test: `python3 -m pytest mtg_sim/tests/<test_file>.py -v`
- Single trace: `python3 -m mtg_sim.scripts.run_single --mana-u 1 --mana-r 1 --seed 42`
- Monte Carlo: `python3 -m mtg_sim.scripts.run_monte_carlo --runs 1000 --mana-u 1`

## Core Architecture

Main loop: `mtg_sim/sim/runner.py:simulate_run`

Flow:

1. Check win/brick.
2. Generate legal actions.
3. Choose action manually or by policy.
4. Resolve action.
5. Repeat.

Key files:

- `mtg_sim/sim/state.py`: `GameState`, zones, permanents, permissions, logs.
- `mtg_sim/sim/actions.py`: `Action`, `CostBundle`, `EffectBundle`.
- `mtg_sim/sim/stack.py`: `StackObject` and stack representation.
- `mtg_sim/sim/action_generator.py`: generic legal-action scaffolding.
- `mtg_sim/sim/card_behaviors.py`: card-specific action generation and resolution.
- `mtg_sim/sim/resolver.py`: applies chosen actions to `GameState`.
- `mtg_sim/sim/policies.py`: greedy action scoring.
- `mtg_sim/sim/mana.py`: mana pool and cost payment.

## Codex Working Rules

- Prefer read-only discovery before editing.
- Use `rg` for symbol, field, registry, constant, and call-site checks before reading code.
- Read targeted ranges; prefer one complete function/class range over multiple partial reads.
- Do not read a whole file only to find a section.
- Before reading more than 150 lines, explain why the full range is needed.
- Separate required reads from conditional reads; inspect conditional files only when the change touches that concern.
- Keep diffs small and reviewable.
- Do not make unrelated architectural changes.
- If architecture seems wrong but changing it is outside scope, report it as follow-up work instead of expanding the task.
- Manual mode and policy mode should use the same legal action list when practical.
- Use readable names in traces/manual mode, not object IDs.

## ContextNotes

- Before editing files under `mtg_sim/`, check whether relevant ContextNotes exist under `docs/notes/`.
- Matching notes generally follow the path under `mtg_sim/`, for example `docs/notes/sim/card_behaviors.py.md`.
- Read applicable Touchpoints and Gotchas before editing to avoid rediscovering known file-specific information.
- Update ContextNotes only when the takeaway is reusable, architectural, or likely to prevent recurring mistakes.
- Do not update notes merely because a file changed.
- Ask before creating a new ContextNote unless the user explicitly requested note maintenance.

## Card-Specific Work

- See `docs/workstreams/card_specific.md` for the bucket workflow when implementing card-specific behavior.
- Prefer card-specific logic in `card_behaviors.py`.
- Keep `action_generator.py` as generic scaffolding where practical.
- If a card needs special action generation, prefer `CardBehavior.generate_actions(...)`.
- If a card needs special resolution, prefer `CardBehavior.resolve_cast(...)`.
- If a card needs battlefield or mana behavior, use `generate_mana_actions(...)`, `generate_activate_actions(...)`, or `on_enter(...)`.
- Noncreature spell casts should still trigger Vivi/Curiosity through existing cast logic.
- Permanent spells should enter battlefield through existing resolver logic unless the card says otherwise.
- Nonpermanent spells should go to graveyard unless the card says otherwise.
- Do not model omitted real-card behavior unless `docs/specs/card_specifics.md` says to model it.
- Add `Comments:` text from `docs/specs/card_specifics.md` as an implementation comment when it explains a simulator simplification.

## Policy Work

- Inspect `mtg_sim/sim/policies.py` and the relevant action/state fields first.
- Keep policy scoring separate from legality.
- Do not fix legality bugs in policy code.
- Prefer small scoring changes with focused tests.

## Verification

- For code changes, run the smallest relevant pytest target first.
- Run broader tests only after focused tests pass and only when the task scope justifies it.
- Do not use Monte Carlo or broad simulation runs to prove a specific rule.
- If no focused test exists, explain what was and was not verified.
- Documentation-only changes do not require the Python test suite.
- Final reports should include files changed, behavior before/after, tests run, and remaining uncertainty.

## Codex Task Mode (Route B)

When launched non-interactively by `run_codex_task.py` or with a task artifact, follow bounded-implementer rules in `.agents/skills/codex-implementer/SKILL.md`:

- Implement only what the task describes; report follow-ups in result JSON, do not expand scope.
- Write an `ImplementationResult` JSON to `.agents/runs/<task_id>/<task_id>.result.json`.
- Run all `validation_commands` before reporting success.
- Do not add entries to `.agents/tasks.json` directly.
- Do not read or edit `.claude/` files.

In interactive mode, use normal Codex behavior and the working rules above.

## Task And Backlog Notes

- Do not migrate `.claude/tasks`.
- Do not create a separate Codex backlog.
- If follow-up work is discovered, report it in the final response unless an existing repo-visible backlog file has clear instructions.
- Treat `.claude/` task mechanisms as Claude-specific unless explicitly asked to inspect or port them.

## Tool-Specific Warning

- `.claude/` files are Claude-specific.
- Read `.claude/` files only when explicitly asked to inspect, translate, or maintain Claude context.
- Do not edit `.claude/` files during ordinary Codex implementation tasks.

## Planned Extensions

- Policy weights will move to a text-editable config file; keep scoring logic separate from action generation.
- Card behaviors may eventually split into per-card files; keep each behavior self-contained.
