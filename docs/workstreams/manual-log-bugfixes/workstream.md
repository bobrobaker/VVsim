# Workstream: Manual Log Bugfixes

Progress: B04/transmute-costs next (B01, B02, B03 done)
Blocked: none

## Objective

Fix the real bug/issue notes found in `mtg_sim/scripts/logs/manual_observations.jsonl`, preserving game semantics and keeping each change small. For every bucket, write the focused unit test first, implement the fix second, run that unit test third, then reproduce the logged situation with a state derived from the corresponding JSONL entry. Treat old-log test/no-op notes as context only unless the active bucket says otherwise.

## Execution Protocol (do not change)

1. Read this workstream first.
2. Use `Progress` and `Bucket Index` to select the active bucket; if none is active, select the next bucket.
3. Open only the selected bucket file.
4. Read only that bucket's required touchpoints before reporting.
5. Report first: selected bucket, required touchpoints read, current behavior, proposed edits, validation plan, and extra touchpoints if needed.
6. Only edit after the plan is clear.
7. Run the bucket's validation.
8. Update the bucket file's `Updates` section with completed tasks, discoveries, gotchas, test results, and handoff notes.
9. Update this workstream's `Progress`, `Bucket Index`, and `Updates` only for progress, sequencing changes, cross-bucket discoveries, and cross-bucket gotchas.
10. Keep only one bucket active at a time unless the user explicitly authorizes parallel execution.

## Bucket Index

| B | State | File | Goal | Depends |
|---|---|---|---|---|
| B01 | done | buckets/B01_sorcery-stack-timing.md | Block sorceries on stack | - |
| B02 | done | buckets/B02_daze-tapped-island.md | Allow tapped Island return | B01 |
| B03 | done | buckets/B03_strike-it-rich-flashback.md | Fix flashback cost/zone | B02 |
| B04 | next | buckets/B04_transmute-costs.md | Enforce transmute costs | B03 |
| B05 | later | buckets/B05_misdirection-player-targets.md | Recognize player-target spells | B04 |

States: `next`, `active`, `blocked`, `done`, `deferred`, `later`.

## Cross-Bucket Invariants

- Tests first, implementation second, unit test third, JSONL-derived state reproduction last.
- Do not encode policy preference as legality; these buckets fix legal action generation/resolution only.
- Manual mode and policy mode should continue consuming the same legal action list.
- Keep logged manual notes visible in test names or comments where useful, including source file and line.

## Deferred / Non-Goals

- Do not implement full MTG targeting or priority beyond the logged bug surface.
- Do not convert diagnostic opener scripts into formal tests in this workstream.
- Do not inspect or edit `.claude/` files.

## Global Implementation Notes

- Relevant bug notes are in `mtg_sim/scripts/logs/manual_observations.jsonl` lines 16, 51, and 100.
- `manual_observations_old.jsonl` line 60 duplicates the transmute-cost issue; lines 48, 59, and 154 are test/no-op notes and should not drive fixes.
- JSONL-derived state reproduction may be a focused helper that reconstructs only the fields needed to prove the reported action appears or disappears.

## Estimate

18k-28k tokens.

## Updates

- 2026-05-13 21:35 Initial plan created. Next: B01/sorcery timing.
- 2026-05-13 B01 done. Wild Ride card_types fixed in card_library.csv (Instant→Sorcery). Outsource-codex pipeline harness bug discovered and fixed same session (patch capture used `format-patch`/`<base>..HEAD`, missed uncommitted worktree edits; fixed to `git diff --binary <base> --`). Next: B02.
- 2026-05-13 B02 done. Removed tapped-land filter from `_islands_on_battlefield`. One-line fix + one new test. 419 tests pass. Next: B03.
- 2026-05-13 B03 done. Fixed graveyard flashback loop to generate only flashback alt-cost actions (not normal hand-cast). Zone movement to exile was already correct. 3 new tests, 419 pass. Next: B04.
