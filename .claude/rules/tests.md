---
globs:
  - "mtg_sim/tests/**"
---

## Testing rules

- Every behavior change must include focused unit tests unless documentation-only.
- Test the smallest useful boundary: action generation, action legality, resolution, mana payment, stack behavior, policy choice, or one card behavior.
- Prefer separate tests for action generation and resolution when practical.
- Do not use Monte Carlo or broad simulation runs to prove a specific rule.
- Tests must be deterministic: fixed seed, fixed library order, explicit hand/library/battlefield/graveyard/exile setup.
- Assert exact state transitions: hand, library, graveyard, exile, battlefield, stack, floating mana, pending choices, permissions, counters, tapped state, and sacrificed state.
- For legality, assert both legal actions present and illegal actions absent.
- Include negative tests for illegal targets, missing resources, wrong timing, absent board state, and exhausted one-shot resources.
- For cast/resolve tests, use or create a stack-drain helper before writing inline resolve loops.
- Before writing tests, check existing helper patterns, `ManaPool(...)` usage, default initial battlefield, and mana-cost arithmetic.
- Before writing any `Action(...)` construction in a test, grep an existing test for `Action(` to get exact kwarg names (`source_card=`, `costs=`, `effects=`). Do not guess constructor kwargs.
- Test the modeled behavior in `docs/card_specifics.md`, not full real Magic card text.
- Do not weaken, delete, or generalize existing assertions to make new code pass.
- Run the smallest relevant test first; run broader tests only after focused tests pass.
