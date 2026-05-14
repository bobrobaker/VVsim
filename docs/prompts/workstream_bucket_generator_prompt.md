# Workstream + Bucket Generator Prompt

The goal of this prompt is to produce actual markdown files for a multi-session implementation effort:

1. Produce one parent workstream file: the always-read router for objective, progress, bucket order, cross-bucket invariants, global implementation notes, non-goals, and cross-bucket updates.
2. Produce as many bucket files as needed: each bucket is a short-session cluster of tasks with shared concept, edit surface, and validation.
3. Before finalizing, internally stress-test:
   - Are bucket boundaries based on context, not arbitrary feature count?
   - Is any parent content actually bucket-local?
   - Are any buckets too large for one session?
   - Are required touchpoints minimal and sufficient?
   - Are conditional/do-not-read notes preventing wasted intake?
   - Are prior mistakes, introspection notes, or bug logs converted into gotchas?
4. Respond in chat with:
   - **Files created** — file paths and one-line purpose.
   - **Assumptions made** — brief bullets.
   - **Compression rationale** — what was omitted, moved to buckets, or preserved globally, and why.
   - **Questions / risks** — only material unresolved issues.

## General information

Brevity rules:
- Every generated word must improve code quality or token efficiency.
- Parent workstream: global objective, progress, bucket index, cross-bucket invariants, global implementation notes, non-goals, updates.
- Bucket files: bucket-local tasks, touchpoints, constraints, validation, gotchas, handoff.
- Do not duplicate bucket detail in the parent.
- Prefer terse but precise instructions over narrative explanation.

File naming rules:
- Create files under `docs/workstreams/[workstream-slug]/` unless I specify another location.
- Parent file: `docs/workstreams/[workstream-slug]/workstream.md`.
- Bucket files: `docs/workstreams/[workstream-slug]/buckets/B##_short_slug.md`.
- Use lowercase kebab-case for `[workstream-slug]` and bucket slugs.
- Use stable bucket IDs: `B01`, `B02`, `B03`, etc.
- Bucket filenames must begin with their bucket ID.
- Keep names short but specific: `B01_policy-config.md`, not `B01_first-bucket.md`.

Bucket split rules:
- First split by conceptual mapping: group tasks that require the same mental model and nearby files.
- Then split further if a bucket is likely to exceed a short Claude session.
- Target roughly 5-minute execution sessions; definitely split if likely above 10 minutes.
- A tiny task may share a bucket if it uses the same loaded context.
- Split tasks with unrelated edit surfaces even if they are thematically adjacent.
- For now, assume only one active bucket at a time. Do not design for parallel bucket execution unless explicitly requested.

Touchpoint: a bounded code region Claude should inspect because it is edited, directly called, or preserves an invariant.

Touchpoint rules:
- Required touchpoints: likely edit surface or necessary invariant reads. No broad conceptual reads.
- Do not add `AGENTS.md` as a required touchpoint in file-creation-only buckets — it is a conditional existence check at most.
- Conditional touchpoints: insurance reads with explicit trigger conditions.
- Do-not-read touchpoints: tempting distractions; encode the conclusion so Claude does not rediscover it. Omit this section entirely if empty.
- Prefer line ranges, symbols, and grep queries over full-file reads.
- Format touchpoints as:
  `[file]  [line range or grep query]  [symbol/anchor]`
  followed by a short reason.

## Input to convert

Goal / technical discussion:

[PASTE GOAL OR DISCUSSION HERE]

Relevant files, docs, introspection notes, bug logs, prior decisions:

[PASTE CONTEXT HERE]

## Workstream template

Use this structure for the generated parent file. Keep section names.

```markdown
# Workstream: [Name]

Progress: B01/[1-5 word focus] next
Blocked: none

## Objective

[2-4 sentence compressed objective. Global only.]

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
| B01 | next | buckets/B01_short_slug.md | [short goal] | — |
| B02 | later | buckets/B02_short_slug.md | [short goal] | B01 |

States: `next`, `active`, `blocked`, `done`, `deferred`, `later`.

## Cross-Bucket Invariants

- [Global invariant Claude must preserve across buckets.]

## Deferred / Non-Goals

- [Out-of-scope item that Claude may be tempted to do.]

## Global Implementation Notes

- [Implementation detail relevant across the whole workstream.]

## Estimate

[X–Y tokens — implementation cost, not planning cost. Count reads, edits, tests, and iteration cycles. Exclude the cost of generating this workstream/bucket plan itself.]

## Updates

- [YYYY-MM-DD HH:MM] Initial plan created. Next: B01/[focus].
```

Workstream file rules:
- Do not include bucket-local touchpoints, detailed task lists, or bucket-local validation.
- Put discoveries here only if they affect later buckets or the whole workstream.
- Keep `Progress` to one line. Use `Updates` for details.
- Keep `Bucket Index` as the source of truth for sequencing.
- `Updates` entries are chronological ascending: **append new entries at the end**, oldest entry first.

## Bucket template

Use this structure for each generated bucket file. Keep section names.

```markdown
# Bucket [B##]: [Name]

Parent: ../workstream.md
State: [next/later/active/blocked/done/deferred]
Goal for session: [10 words max].
Target duration: ~5 minutes; split if likely >10.
Context budget: Read parent + this bucket + required touchpoints only.

## Conceptual mapping

- [Why these tasks share context/edit surface.]

## Tasks

- [ ] [Concrete task.]
- [ ] [Concrete task.]

## Required touchpoints

- `[file]  [line range or grep query]  [symbol/anchor]`
  [Short reason.]

## Conditional touchpoints

- `[file]  [line range or grep query]  [symbol/anchor]`
  Read only if [trigger condition].

## Do-not-read / avoid

- `[file or area]`
  [Why this is distracting or already decided.]

(Omit this section if there are no distracting targets for this bucket.)

## Design direction

- [Concise guidance needed to implement correctly.]
- [Subtle constraint that would be easy to miss.]

## Validation

- [Command or manual check.]
- Expected: [observable pass condition.]

## Done criteria

- [ ] Tasks complete.
- [ ] Validation passes.
- [ ] Bucket `Updates` section records discoveries/gotchas/handoff.
- [ ] Parent workstream progress updated.

## Updates

- [YYYY-MM-DD HH:MM] Created. Handoff: none yet. Gotchas: none yet.
```

Bucket file rules:
- Bucket-specific context lives here, not in the parent.
- Include only touchpoints needed for this bucket.
- Use `Updates` for bucket-local discoveries, gotchas, test notes, and handoff.
- `Updates` entries are chronological ascending: **append new entries at the end**, oldest entry first.
- Do not let Claude mark a bucket `done` without validation or an explicit explanation of why validation was not possible.

## Workstream Bucket Generator Updates

Introspection notes + feedback notes go here with a timestamp and a suggestion:
- 2026-05-12 00:00: Initial draft.
- 2026-05-13 00:00: Removed `## Report First` from bucket template — duplicates Execution Protocol steps 5–6 in workstream, which is already always read. Added note to omit `## Do-not-read` when empty. Added touchpoint rule: do not add `AGENTS.md` as required touchpoint in file-creation-only buckets.
- 2026-05-13 17:00: Changed timestamp format to `YYYY-MM-DD HH:MM` throughout templates for ordering clarity.
- 2026-05-13 18:00: Added `## Estimate` field to workstream template. Must be implementation cost (reads + edits + tests + iteration), not the cost of generating the workstream plan itself.
- 2026-05-13: Resolver touchpoints — when a bucket's goal is action-generation-only (fix lives entirely in `generate_actions` or a helper), resolver touchpoints should be `Conditional` (read only if the fix might affect resolution) not `Required`. Required resolver reads are only warranted when the bucket explicitly changes resolution logic.
