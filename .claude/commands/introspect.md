# /introspect — Token Introspection Workflow

Run this at the end of any session to audit token use and route actionable findings to the right context files.

**Scope note:** If `/introspect` was already run earlier in this same session, evaluate only the work that occurred *after* that prior introspect — not the full session history.

## Step 1: Measure

Report:
- Estimated input/output token ratio for this session
- Which files/docs were loaded and whether each earned its tokens (useful vs wasteful)
- Top 3 token drains with a one-line explanation of why each was wasteful

## Step 2: Identify recurring mistakes

Check last 50 lines of `docs/logs/introspect_notes.md` for patterns that appeared in prior sessions and recurred in this one. Flag any repeated mistakes explicitly.

## Step 3: Route actionable takeaways

For each concrete takeaway, recommend the best destination:

| Destination | When to use |
|---|---|
| `CLAUDE.md` | Stable, global, applies every session |
| `.claude/rules/` | Can be triggered syntactically by file path/glob |
| Claude memory | Durable user preference or general workflow preference |
| ContextNotes (`docs/notes/<file>.md`) | File-specific gotcha, touchpoint, or invariant discovered while editing that file. Create one if this is chosen if it didn't already exist |
| `docs/Prebaker.md` | Session was prebaked and takeaway improves future prompt generation |
| Workstream prompt (`docs/workstream_<name>_.md`) | Session began from a workstream prompt and takeaway improves future sessions in that workstream |
| `docs/prompts/workstream_bucket_generator_prompt.md` | Something is generically wrong with the structure/boilerplate of workstream or bucket files (e.g. required touchpoints that are always wasteful, structural sections that drain tokens every session) |

## Step 4: Confirm

List only proposed changes to routing destinations (CLAUDE.md, rules, memory, workstream docs). Do NOT ask for confirmation before writing to `docs/introspect_notes.md` or `docs/introspect_log.md` — those are unconditional housekeeping.

## Step 5: Implement

After confirmation, make the accepted changes.

## Step 6: Log and report

- Append one bullet of qualitative findings to `docs/introspect_notes.md` under a new `## <Session Name>` header (2–4 word title identifying this session). Include: token ratio, what was useful, main drains, concrete recommendations.
- Append one row to `docs/introspect_log.md`: date, session name, ratio, notes.

## Step 7: Clear or continue?

Make a genuine judgment: should the user clear, compact, or continue? Weigh the actual tradeoffs — what's in context now, what the next task needs, and what the cheapest path to that task is. Options:

- **Clear**: start a fresh session with no prior context. Best when the next task is a new bucket or unrelated work and nothing in the current session needs to carry forward. Eliminates re-ingestion cost entirely.
- **Compact**: compress context and continue. Only worth it if the next task genuinely needs live context from this session (e.g. mid-task, open decisions, active debugging state).
- **Continue**: no action. Only if context is genuinely small and the next task is a direct extension.

Note that compact does not eliminate re-ingestion cost — it just defers it. A compacted summary paid on the next turn is the same category of drain as one paid at session start.

Give 2–3 sentences: what the current context state is, what the next task likely needs, and your recommendation with the reasoning behind it.

## Step 8: Backlog report

First, identify anything that should have been logged during the session but wasn't — every item meeting the CLAUDE.md criteria (medium/high value OR medium/high urgency). Call `TaskCreate` for each automatically (no confirmation needed).

Then report: how many `[SUGGESTION]` backlog tasks were added this session in total (including any just created above)? List the top 3 **session near-misses** — things noticed this session that *would have* been logged if they were higher value or urgency — with a one-line note on why each didn't meet the bar. Do NOT re-list pre-existing backlog tasks the user already knows about. If there are no near-misses, say so explicitly.
