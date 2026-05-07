# Workstream: Card-Specific Bucket Implementation

**Bucket**: A scoped cluster of similar cards sharing logic patterns and likely touchpoints, intended for one focused Claude session.

**Workstream**: A broader multi-session effort composed of buckets, organized to preserve architectural continuity while limiting per-session context.

Goal: implement card-specific simulator behavior from `docs/card_specifics.md` one bucket at a time, with focused tests.

## Context rules

Before editing, read first:
- the relevant docs/[bucketname]_claude_prompt_concise.txt for helpful info, which should point out particular lines into:
- `docs/card_specifics.md`
- `mtg_sim/sim/action_generator.py`
- `mtg_sim/sim/card_behaviors.py`
- `mtg_sim/sim/resolver.py`
- relevant existing tests

Do not read unrelated files unless needed. If another file is needed, briefly explain why before reading it.

## Workflow per bucket

1. Locate the requested bucket in `docs/card_specifics.md`.
2. Read only that bucket’s cards and bucket-level notes/tests.
3. Inspect current implementation for those cards.
4. Add or update focused tests for that bucket.
5. For any particular card, there may be no implementation changes needed.

## Implementation rules

- Prefer card-specific logic in `card_behaviors.py`.
- Keep `action_generator.py` as generic scaffolding where possible.
- If a card needs special action generation, implement it through a `CardBehavior.generate_actions(...)` override when practical.
- If a card needs special resolution, implement it through `CardBehavior.resolve_cast(...)`.
- If a card needs battlefield/mana behavior, implement `generate_mana_actions(...)` or `on_enter(...)`.
- Preserve default simulator behavior unless the bucket explicitly overrides it.
- Noncreature spell casts should still trigger Vivi/Curiosity through existing cast logic.
- Permanent spells should enter the battlefield through existing resolver logic unless a card says otherwise.
- Nonpermanent spells should go to graveyard unless a card says otherwise.
- Do not model omitted real-card behavior unless `docs/card_specifics.md` says to model it.

## Comments field

Each card entry has a `Comments:` field. Add that text as an implementation comment near the relevant card behavior if it explains a gap between real Magic behavior and this simulator’s simplified behavior.

## Tests

For each bucket:
- Add bucket-level tests when the behavior applies across several cards.
- Add card-specific tests when the card has unique action generation, resolution, target, or win logic.
- Include negative tests for illegal targets, missing resources, wrong timing, or absent required board state.

## Bucket targeting

When asked to implement a bucket, use the line range or heading supplied by the user.

Example request:

> Implement only `docs/card_specifics.md` lines 10–65, bucket: Terminators.

Terminators: 7–48
Fetchlands: 49–102
MDFC Lands: 103–146
Other Lands: 147–224
Tutors: 225–288
Counterspells and Stack Interaction: 289–371
Nonland Mana Sources: 372–467
Draw and Cast-Permission Engines: 468–509
Misc Spells: 510–622
Generic No-Op Permanents: 623–640
Intake New Cards: 641–650

## Intake new cards

At the end of `docs/card_specifics.md`, there is an `## Intake New Cards` bucket.

Use this only when adding cards not yet organized into final buckets.

Each intake entry should include:

```markdown
### Card Name
Bucket: TBD
Action gen:
Resolution:
Tests:
Comments:
```

When implementing from intake:
- Read only the intake entries requested.
- Preserve the `Bucket: TBD` field unless explicitly asked to classify/reorganize.
- After implementation, add tests as usual.
