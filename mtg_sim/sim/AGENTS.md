# AGENTS.md

Scope: simulation source files under `mtg_sim/sim/`.

## Before Editing

- Check for a matching ContextNote under `docs/notes/sim/` before editing a simulation file.
- Read the relevant Touchpoints and Gotchas first; use them to skip unnecessary full-file reads.
- Use `rg` for symbols, registries, call sites, fields, and constants before opening code ranges.
- Prefer targeted function/class reads over broad file reads. If reading more than 150 lines, explain why.

## Simulation Boundaries

- `action_generator.py` owns generic scaffolding: iterate zones, enforce timing/stack rules, and call behavior hooks.
- `card_behaviors.py` owns card-specific action generation, resolution, battlefield behavior, mana behavior, and enter-the-battlefield behavior.
- `resolver.py` applies chosen actions to `GameState`.
- `policies.py` scores legal actions; keep policy evaluation separate from legality.
- Manual-mode and display output should use readable card/action names, not object IDs.

## Change Rules

- Preserve boundaries between rules resolution, action generation, policy evaluation, manual/display output, and card-specific behavior.
- Avoid turning strategic policy preferences into legality rules unless the task explicitly concerns candidate-action pruning.
- Prefer small targeted changes over broad engine rewrites.
- Preserve default simulator behavior unless the requested card or rule explicitly overrides it.
- Do not model omitted real-card behavior unless `docs/specs/card_specifics.md` says to model it.
- For card-specific work, keep each behavior self-contained so later per-card file splits remain possible.

## Tests And Notes

- Add or update focused tests for behavior changes when practical.
- Test the smallest useful boundary: action generation, action legality, resolution, mana payment, stack behavior, policy choice, or one card behavior.
- Update ContextNotes only for reusable gotchas, architectural role changes, or important moved touchpoints.
- Do not update notes merely because a file changed.
