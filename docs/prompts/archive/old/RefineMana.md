Goal for session: Refine policy-driven mana payment.

Distinction: auto-pay floating mana; keep mana-source/color activation explicit.

Inspect targeted touchpoints, then propose a narrow tested patch.

## Required touchpoints
Must read before coding.

mtg_sim/sim/mana.py        1-168     ManaPool/pay_cost
  Existing spend order and likely main edit surface.

mtg_sim/sim/resolver.py    87-96     _resolve_cast_spell
  Spell casts pay mana here; add payment-plan note here if needed.

mtg_sim/sim/resolver.py    372-402   _resolve_sacrifice_for_mana
  Non-spell abilities can pay mana too; keep behavior consistent.

mtg_sim/sim/actions.py     51-92     CostBundle/Action
  Confirm actions encode costs, not every payment permutation.

mtg_sim/tests/test_mana_payment.py  1-150  payment tests
  Best place for focused regression tests if file already exists.

## Conditional touchpoints
Use only if required touchpoints reveal a need.

mtg_sim/sim/action_generator.py  230-305  cast action shape
  Needed if Action fields or cost construction must change.

mtg_sim/sim/action_generator.py  466-491  exile cast costs
  Needed if exile-cast path bypasses normal spell payment assumptions.

mtg_sim/sim/runner.py  manual chooser
  Needed if adding manual auto-payment preview in this session.

mtg_sim/sim/trace.py  format_trace
  Needed if resolver notes do not already display payment clearly.

mtg_sim/sim/policies.py  mana scoring
  Needed if scope expands from payment consumption into production timing.

mtg_sim/sim/cards.py  CardData/get_card
  Needed if payment planner uses hand-aware future color demand.

## Do-not-read touchpoints
Likely distractions; use the note instead.

mtg_sim/sim/card_behaviors.py  mana source behaviors
  Production color choices already stay explicit; do not refactor them.

mtg_sim/sim/action_generator.py  _gen_mana_actions
  Mana production action generation is not the target of this patch.

mtg_sim/sim/card_specifics.md  mana source buckets
  Card behavior specs are unchanged; avoid revalidating production design.

mtg_sim/sim/policies.py  choose_action broadly
  Broad policy tuning is separate unless payment change exposes a bug.

## Design direction
- Keep legal actions at the spell/target/alt-cost level; do not add cast-action permutations for every possible mana payment.
- Treat `can_pay_cost` as legality checking and `pay_cost`/new helper as payment selection; preserve that separation unless a better minimal design is obvious.
- Improve generic-cost spending: spend `C` first, then choose between `ANY`/colored mana to preserve future castability rather than blindly using fixed `ANY → U → R` order.
- Apply the same payment planner anywhere mana costs are paid, including spell casts and non-spell ability costs.
- Do not change mana production action generation: Treasure/LED/Petal/Mox/land color choices should remain explicit actions.
- Trace/manual payment visibility is useful but secondary; add simple resolver notes only if it stays low-risk.
- Avoid broad policy tuning unless tests show payment planning alone cannot fix the issue.

## Tips on tests:
- Before writing mana tests, grep existing `ManaPool(` usage and verify numeric costs (`2R` = 3 total mana), since past failures came from invalid test mana assumptions.
- For field/handler existence checks, prefer grep over broad file reads (`alt_cost_type`, `attached_to`, `_opponent`, registry entries); avoid re-reading constants already shown by grep.
- If a cast/resolve test touches stack resolution, define/use a `_drain_stack` helper up front so Curiosity draw triggers do not cause avoidable debug loops.
