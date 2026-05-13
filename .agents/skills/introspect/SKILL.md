---
name: introspect
description: Audit Codex session token/context use, identify recurring mistakes, and route takeaways to AGENTS.md, nested AGENTS.md, skills, config, notes, logs, or task backlog. Use at the end of a Codex session.
---

# /introspect — Codex Token Introspection Workflow

Run this at the end of any Codex session to audit token/context use and route actionable findings to the right Codex-facing context files.

## Step 1: Measure

Report:
- Estimated input/output token ratio for this session
- Which files/docs were loaded and whether each earned its tokens: useful vs wasteful
- Top 3 token drains with a one-line explanation of why each was wasteful
- Whether the task should have used a different Codex mode:
  - interactive Codex session
  - `codex exec`
  - `/review`
  - read-only scout profile
  - implementation profile
  - app/worktree task

## Step 2: Identify recurring mistakes

Check the last 50 lines of `docs/logs/introspect_notes.md` for patterns that appeared in prior sessions and recurred in this one.

Flag repeated mistakes explicitly, especially:
- over-reading broad files instead of targeted symbols
- editing before reporting a plan
- skipping required bucket tests
- treating architecture docs as implementation targets
- failing to run the relevant pytest command
- confusing policy failures with action-generation or resolver bugs
- using interactive Codex when `codex exec` with structured output would have been cleaner

## Step 3: Route actionable takeaways

For each concrete takeaway, recommend the best destination:

| Destination | When to use |
|---|---|
| `AGENTS.md` at repo root | Stable, global project instruction that should apply to every Codex session in this repo |
| Nested/path-local `AGENTS.md` | Path-scoped instruction that should apply only when working under that directory; Codex equivalent of Claude path/glob rules |
| User-level Codex instructions / global `AGENTS.md` | Durable user workflow preference that should apply across repositories |
| Codex skill | Repeatable procedural workflow, checklist, or task type that should load only when invoked |
| Codex slash command | Short reusable prompt/action shortcut, especially for frequent review/scout commands |
| `.codex/config.toml` profile | Permission/sandbox/model/approval behavior that should be enforced by mode rather than remembered in prose |
| ContextNotes (`docs/notes/<file>.md`) | File-specific gotcha, touchpoint, or invariant discovered while editing that file; create one if chosen and it does not exist |
| `docs/prompts/prebaker.md` or Codex prebake skill | Session was prebaked and takeaway improves future prompt generation or touchpoint selection |
| Workstream prompt (`docs/workstreams/<name>.md`) | Session began from a workstream prompt and takeaway improves future sessions in that workstream |
| `.agents/tasks.json` | New task, follow-up, blocked item, acceptance criterion, or cross-agent handoff |
| `docs/logs/introspect_notes.md` | Qualitative recurring lesson from this session |
| `docs/logs/introspect_log.md` | Structured session audit row |

Routing guidance:
- Prefer `AGENTS.md` only for stable rules that are worth loading every session.
- Prefer nested `AGENTS.md` when the lesson is path-local and would otherwise pollute global context.
- Prefer a Codex skill when the lesson is procedural: “when doing X, follow this checklist.”
- Prefer `.codex/config.toml` when the issue is permissions, sandboxing, approvals, or model/mode selection.
- Prefer `.agents/tasks.json` for work that should be executed later by Claude, Codex, or ChatGPT.

## Step 4: Confirm

List only proposed changes to routing destinations that affect future agent behavior, such as:
- root `AGENTS.md`
- nested/path-local `AGENTS.md`
- user-level Codex instructions
- Codex skills
- Codex slash commands
- `.codex/config.toml`
- workstream docs
- `.agents/tasks.json`

Do **not** ask for confirmation before writing unconditional housekeeping:
- `docs/logs/introspect_notes.md`
- `docs/logs/introspect_log.md`

If the session produced a clear follow-up task that meets the project’s task-capture threshold, add or update it in `.agents/tasks.json` automatically unless the task system for this repo says otherwise.

## Step 5: Implement accepted routing changes

After confirmation, make the accepted changes.

Rules:
- Keep root `AGENTS.md` short and stable.
- Use nested `AGENTS.md` for directory-specific rules instead of globalizing them.
- Do not duplicate the same instruction in root `AGENTS.md`, nested `AGENTS.md`, and a skill unless each location serves a distinct purpose.
- If a rule is only relevant to a repeated workflow, prefer a Codex skill over always-loaded context.
- If a rule is safety/permissions-related, prefer `.codex/config.toml` or a profile over prose reminders.
- If a change is speculative, log it as a task or suggestion instead of changing context files.

## Step 6: Log and report

Append one bullet of qualitative findings to `docs/logs/introspect_notes.md` under a new `## <Session Name>` header.

The header should be 2–4 words identifying this session.

Include:
- token ratio
- what context was useful
- main token drains
- repeated mistakes
- concrete recommendations
- which Codex mode would have been best in hindsight

Append one row to `docs/logs/introspect_log.md`:

| date | session name | ratio | mode used | better mode? | notes |
|---|---|---|---|---|---|

Use a compact single-line note. Do not paste the whole report into the log row.

## Step 7: Backlog / task report

First, identify anything that should have been logged during the session but was not.

Add or update `.agents/tasks.json` entries for each item that meets the repo’s task-capture threshold:
- medium/high value, or
- medium/high urgency, or
- required follow-up for correctness, tests, policy win rate, or architecture hygiene.

Use `[SUGGESTION]` for non-blocking improvement tasks.

Then report:
- how many `[SUGGESTION]` backlog tasks were added or updated this session in total
- the top 3 in order of criticality, each with a one-line value/urgency note
- if fewer than 3 real candidates exist, name the next closest things and why they did not meet the bar

## Step 8: Codex-specific hindsight

Report whether this session should change future routing.

Answer briefly:
- Should this have been run as `codex exec` instead of interactive Codex?
- Should this have used `/review`?
- Should this have used a read-only profile?
- Should this have used a worktree?
- Should this have been routed to Claude or ChatGPT instead of Codex?
- Did Codex need a skill/slash command that does not exist yet?

## Output format

Use this exact structure:

```markdown
# Introspection: <Session Name>

## Token use
- Ratio:
- Useful context:
- Wasteful context:
- Top drains:

## Recurring mistakes
- ...

## Routing recommendations
| Takeaway | Destination | Reason |
|---|---|---|
| ... | ... | ... |

## Proposed context/config changes
- Needs confirmation:
  - ...
- Housekeeping written without confirmation:
  - `docs/logs/introspect_notes.md`
  - `docs/logs/introspect_log.md`

## Task/backlog updates
- Added/updated:
- Top candidates:

## Codex mode hindsight
- Best mode:
- Reason:
- Future adjustment:
```

## Codex routing translation reference

| Claude-oriented destination | Codex-oriented destination |
|---|---|
| `CLAUDE.md` | root `AGENTS.md` |
| `.claude/rules/` | nested/path-local `AGENTS.md` files |
| Claude memory | user-level Codex instructions or global `AGENTS.md`, depending on scope |
| Claude subagent instruction | Codex skill or explicit subagent prompt, depending on whether it is reusable |
| Claude task JSON | neutral `.agents/tasks.json` unless the repo has chosen another task source of truth |
| Claude hook / deterministic guard | `.codex/config.toml` profile, external script, or repo test/check command |
| Claude workstream prompt | `docs/workstreams/<name>.md` plus optional Codex skill/slash command |
