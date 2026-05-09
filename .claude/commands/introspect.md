# /introspect — Token Introspection Workflow

Run this at the end of any session to audit token use and route actionable findings to the right context files.

## Step 1: Measure

Report:
- Estimated input/output token ratio for this session
- Which files/docs were loaded and whether each earned its tokens (useful vs wasteful)
- Top 3 token drains with a one-line explanation of why each was wasteful

## Step 2: Identify recurring mistakes

Check last 50 lines of `docs/introspect_notes.md` for patterns that appeared in prior sessions and recurred in this one. Flag any repeated mistakes explicitly.

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

## Step 4: Confirm

List only proposed changes to routing destinations (CLAUDE.md, rules, memory, workstream docs). Do NOT ask for confirmation before writing to `docs/introspect_notes.md` or `docs/introspect_log.md` — those are unconditional housekeeping.

## Step 5: Implement

After confirmation, make the accepted changes.

## Step 6: Log and report

- Append one bullet of qualitative findings to `docs/introspect_notes.md` under a new `## <Session Name>` header (2–4 word title identifying this session). Include: token ratio, what was useful, main drains, concrete recommendations.
- Append one row to `docs/introspect_log.md`: date, session name, ratio, notes.

## Step 7: Backlog report

First, identify anything that should have been logged during the session but wasn't — every item meeting the CLAUDE.md criteria (medium/high value OR medium/high urgency). Call `TaskCreate` for each automatically (no confirmation needed).

Then report: how many `[SUGGESTION]` backlog tasks were added this session in total (including any just created above)? List at least the top 3 in order of criticality, with a one-line value/urgency note for each. If fewer than 3 real candidates exist, name the next closest things that would have been logged and why they didn't meet the bar.
