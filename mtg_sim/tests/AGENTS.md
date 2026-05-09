# AGENTS.md

Scope: tests under `mtg_sim/tests/`.

## Test Style

- Follow existing setup patterns before inventing new fixtures.
- Inspect nearby tests and helpers first; use `rg` for helper names, constructor call sites, and parameter names.
- Prefer focused regression tests for bug fixes and behavior changes.
- Do not broadly rewrite tests to match changed behavior unless the behavior change is intentional.
- Keep test changes narrow and behavior-focused.

## Determinism And Assertions

- Tests should be deterministic: fixed seed, fixed library order, explicit hand/library/battlefield/graveyard/exile setup.
- Assert exact state transitions when relevant: hand, library, graveyard, exile, battlefield, stack, floating mana, pending choices, permissions, counters, tapped state, and sacrificed state.
- For legality, assert both legal actions present and illegal actions absent.
- Include negative tests for illegal targets, missing resources, wrong timing, absent board state, and exhausted one-shot resources.
- Test the modeled behavior in `docs/card_specifics.md`, not full real Magic card text.

## Fixtures And Helpers

- Check existing helper patterns, `ManaPool(...)` usage, default initial battlefield, and mana-cost arithmetic before writing new setup.
- For card mana costs that are load-bearing in assertions, verify `get_card("<name>").pip_r`, `.pip_u`, and `.generic_mana` before writing the test.
- Before constructing `Action(...)` directly, grep existing tests for `Action(` and copy the established keyword names such as `source_card=`, `costs=`, and `effects=`.
- For cast/resolve tests, use or create a stack-drain helper instead of writing repeated inline resolve loops.
- If a module introduces a process-level cache, add a clear-cache helper and an autouse fixture that clears it before and after each test.

## ContextNotes And Verification

- Check for matching ContextNotes under `docs/notes/tests/` before editing a test file.
- Reuse stable helper/setup notes, such as initial battlefield assumptions and canonical stack-drain helpers.
- Do not weaken, delete, or generalize existing assertions merely to make new code pass.
- Run the smallest relevant test first; run broader tests only after focused tests pass and only when scope justifies it.
