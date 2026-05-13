# ContextNotes

`docs/notes/` contains compact, agent-facing notes for selected source and test files. These notes are not design docs or changelogs. They exist to keep repeated implementation sessions from rediscovering the same touchpoints, helper patterns, and non-obvious gotchas.

The note path mirrors the relevant project path under `mtg_sim/`:

- `mtg_sim/sim/card_behaviors.py` -> `docs/notes/sim/card_behaviors.py.md`
- `mtg_sim/tests/test_counterspells.py` -> `docs/notes/tests/test_counterspells.py.md`

## How Notes Are Triggered

Claude loads notes through `.claude/rules/sim-notes.md`, which applies to `mtg_sim/**`:

> Before editing any file in `mtg_sim/`, check whether a matching CompanionDoc exists under `docs/notes/<relative-path>.md`. If found, read it before editing. Use the Touchpoints section to avoid unnecessary full-file reads.

Codex uses the same convention through `AGENTS.md` and the path-local agent files:

- Root `AGENTS.md` requires checking relevant ContextNotes before editing files under `mtg_sim/`.
- `mtg_sim/sim/AGENTS.md` points simulation-source edits at `docs/notes/sim/`.
- `mtg_sim/tests/AGENTS.md` points test edits at `docs/notes/tests/`.

In practice, keep the trigger rules in agent/rule files, not inside individual notes.

## Source Notes

Source-file notes should stay short and use this structure:

```markdown
## Gotchas
- Non-obvious invariants only.

## Touchpoints
- Important function/class ranges or grep anchors.

## Recent changes
- Last 1-2 session-relevant changes.
```

Update source notes only when the takeaway is reusable, architectural, or likely to prevent recurring mistakes. Refresh Touchpoints when functions/classes move. Add Recent changes only for source files edited in the session, and keep the whole note under about 20 lines.

## Test Notes

Test-file notes should stay short and use this structure:

```markdown
## Helpers defined here
- Helper name plus line range.

## Setup pattern
- Fixture, state, and assertion patterns worth reusing.
```

Test notes do not use a Recent changes section. Update Helpers and Setup pattern only when those reusable patterns change, and keep the whole note under about 15 lines.

## Creating Notes

Do not create a new ContextNote silently during ordinary implementation work. If no matching note exists and there is a meaningful reusable item to record, ask before creating it unless the task explicitly requested note maintenance.
