# /introspect — Token Introspection Workflow

Run this at the end of any session to audit token use and route actionable findings to the right context files.

## Step 1: Measure

Report:
- Estimated input/output token ratio for this session
- Which files/docs were loaded and whether each earned its tokens (useful vs wasteful)
- Top 3 token drains with a one-line explanation of why each was wasteful

## Step 2: Identify recurring mistakes

Check `docs/introspect_notes.md` for patterns that appeared in prior sessions and recurred in this one. Flag any repeated mistakes explicitly.

## Step 3: Route actionable takeaways

For each concrete takeaway, recommend the best destination:

| Destination | When to use |
|---|---|
| `docs/workstream_card_specific.md` | Takeaway improves future card-bucket sessions |
| `CLAUDE.md` | Stable, global, applies every session |
| `.claude/rules/` | Can be triggered syntactically by file path/glob |
| Claude memory | Durable user preference or general workflow preference |
| `docs/introspect_notes.md` | Qualitative finding worth preserving but not actionable yet |

## Step 4: Confirm

List only proposed changes to routing destinations (CLAUDE.md, rules, memory, workstream docs). Do NOT ask for confirmation before writing to `docs/introspect_notes.md` or `docs/introspect_log.md` — those are unconditional housekeeping.

## Step 5: Implement

After confirmation, make the accepted changes.

## Step 6: Log and report

- Append one bullet of qualitative findings to `docs/introspect_notes.md` under a new `## <Session Name>` header (2–4 word title identifying this session). Include: token ratio, what was useful, main drains, concrete recommendations.
- Append one row to `docs/introspect_log.md`: date, session name, ratio, notes.

## Step 7: Backlog report

Report: how many `[SUGGESTION]` backlog tasks were added this session? If zero, name the one thing that would have been logged. Give a one-line summary of the highest-value item added, if any.
