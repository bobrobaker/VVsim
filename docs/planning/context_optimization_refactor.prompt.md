# Claude Prompt: Context Optimization Refactor

Goal: refactor this project’s Claude context-management setup so future Claude Code sessions load less irrelevant context, preserve useful file-specific knowledge, and make token introspection actionable.

This should be a phased implementation, not a single large all-at-once refactor.

Before editing anything:
1. Inspect the existing `CLAUDE.md`, `.claude/` directory, `docs/` directory, and relevant Claude config files.
2. Inspect available Claude config/task/memory mechanisms first. Confirm whether `.claude/rules/`, `.claude/tasks/`, `TaskCreate`, hooks, skills, and `.claude/memory` exist or need to be created/adapted for this repo.
3. Do not assume requested Claude Code features exist exactly as named. If a feature is unavailable or named differently, report that and recommend the closest safe alternative.
4. Prefer small, reversible changes.
5. Present a phased implementation plan before making changes.
6. After each phase, summarize what changed and what remains.

---

## Phase 0 — Discovery and plan

Inspect the current repo and report:

- current `CLAUDE.md` structure
- existing `.claude/` files/directories
- existing `docs/` files relevant to context management
- whether Claude rules, skills, hooks, task backlog, and memory mechanisms already exist
- whether requested paths need to be created
- any risky or environment-specific actions that should be deferred or confirmed first

Then propose a phased plan. Suggested phases:

1. Safe documentation/context cleanup
2. ContextNotes setup
3. Token introspection skill/docs refactor
4. Backlog/task mechanism inspection and script debugging
5. Hooks/notifications
6. Memory recommendations

Do not implement risky filesystem changes, symlinks, hooks, or task integration until after inspecting the available mechanisms and explaining the plan.

---

## 1. Prebaker docs

Do not implement the Prebaker system in this session.

Context only: Prebaker is intended to be an instruction file for generating compact task prompts. After a brief technical discussion and codebase access, ChatGPT or a specialized Claude agent would use `docs/prompts/prebaker.md` to produce a prompt that can be copy-pasted into a fresh Claude Code session.

---

## 2. Move testing rules into scoped rules

Move testing-specific rules out of `CLAUDE.md` and into a glob-scoped rule file that applies to tests, such as:

- `.claude/rules/tests.md`

This rule should apply to relevant test paths, especially:

- `mtg_sim/tests/**`

Keep only truly global, stable testing guidance in `CLAUDE.md`.

If `.claude/rules/` does not exist or the local Claude setup uses a different rule mechanism, report that first and use the closest safe equivalent.

---

## 3. ContextNotes system

Set up a `ContextNotes` system for file-specific session notes.

### Purpose

`ContextNotes` store compact, file-specific context so Claude does not need to re-derive recurring invariants, gotchas, and important function/class locations every session.

### Files and layout

Create a docs tree that mirrors the relevant source/test tree:

- `docs/notes/sim/`
- `docs/notes/tests/`

Create initial ContextNotes for:

- `mtg_sim/sim/mana.py`
- `mtg_sim/sim/card_behaviors.py`
- `mtg_sim/sim/action_generator.py`
- `mtg_sim/sim/resolver.py`
- `mtg_sim/sim/state.py`

Also create initial ContextNotes for the highest-traffic test files.

For “highest-traffic,” use largest test files by line count as a cheap proxy. Use a command such as `wc -l mtg_sim/tests/*.py | sort -nr | head` or the local equivalent. Report which files you chose.

### Rule file

Create:

- `.claude/rules/sim-notes.md`

This rule should apply to relevant `mtg_sim/**` files.

The rule should instruct Claude:

```markdown
Before editing any file in `mtg_sim/`, check whether a matching ContextNotes file exists under `docs/notes/<relative-path>.md`. If found, read it before editing. Use the Touchpoints section to avoid unnecessary full-file reads.

At the end of a session, update ContextNotes for files you edited.

For source-file ContextNotes:
- Refresh Touchpoints if function/class ranges moved.
- Prepend one bullet to Recent changes.
- Keep only the last 2 Recent changes bullets.
- Update Gotchas only when you discovered a non-obvious invariant.
- Keep the whole file under 20 lines.

For test-file ContextNotes:
- Update Helpers and Setup pattern only.
- Do not add a Recent changes section.
- Keep the whole file under 15 lines.
```

### Source ContextNotes format

```markdown
## Gotchas
- Up to 5 non-obvious invariants.

## Touchpoints
- Key function/class names and line ranges that help avoid full-file reads.

## Recent changes
- Last 2 session-relevant changes only.
```

### Test ContextNotes format

```markdown
## Helpers defined here
- Helper name + line range.

## Setup pattern
- ManaPool conventions, initial-state assumptions, and test setup gotchas.
```

Example setup gotcha:

```markdown
- Initial battlefield usually includes Volcanic Island; check this before asserting Mountain removal.
```

### Populate initial ContextNotes

Populate initial notes from the current file state:

- Use grep/search for function/class locations to fill Touchpoints.
- Seed Gotchas from known recurring issues in `docs/prompts/active/token_introspection.prompt.md`, `docs/logs/introspect_notes.md`, and `CLAUDE.md`.
- Seed test ContextNotes by scanning each selected test file for helper function definitions.

To disable this system later: delete or rename `.claude/rules/sim-notes.md`. The `docs/notes/` tree should remain inert without that rule.

---

## 4. Token introspection skill

Create a token-introspection skill that I can invoke at the end of sessions with:

```text
/introspect
```

First inspect whether this Claude setup supports skills or slash commands in the way needed. If not, recommend the closest safe alternative.

Refactor the existing introspection docs as follows:

- Keep the token-introspection prompt in `docs/prompts/active/token_introspection.prompt.md`.
- Move accumulated introspection output to `docs/logs/introspect_notes.md`.
- Use `docs/logs/introspect_log.md` for token counts and input/output ratios.
- Use `docs/logs/introspect_notes.md` for qualitative findings and recurring mistakes.

The introspection workflow should do this:

1. Report token usage and input/output ratio.
2. Identify recurring mistakes or context waste.
3. For each actionable takeaway, recommend the best context-management destination:
   - workstream instructions, if the session came from a workstream and the takeaway improves future buckets in that workstream
   - `basic_task_generator.md`, if the session came from a generated basic task prompt
   - `.claude/rules/`, if the issue can be triggered syntactically by path/glob
   - `CLAUDE.md`, if it is stable, global, and should apply to every session
   - Claude memory, if it is a durable user preference or general workflow preference
4. Ask for confirmation before implementing the recommendations.
5. After confirmation, implement the accepted recommendations.
6. Report:
   - how many `[SUGGESTION]` backlog tasks were added this session
   - if zero, what one thing would have been logged if we had chosen to log something
   - a one-line summary of the highest-value item added, if any

---

## 5. CLAUDE.md cleanup

Refactor `CLAUDE.md` so it contains only information that is:

- relevant to every session
- stable across sessions
- necessary to hook Claude into the rest of the project’s context-optimization system

Specific changes:

1. Move the “Current Status / Next todo” block out of `CLAUDE.md`.
   - Put human-managed todos in `docs/todo.md`.
   - Use project memory only if that is the better fit and available.

2. Move testing rules into a glob-scoped rule file, such as one applying to `mtg_sim/tests/**`.

3. Keep architectural next steps only if they constrain current decisions.
   - Put these under a small `Planned extensions` section.

4. Add this rule to `CLAUDE.md` or the most appropriate always-loaded context file:

```markdown
When you notice an opportunity to refactor, improve architecture, reduce technical debt, or use a better long-term approach, but it is not needed for the current task, create a pending backlog item with subject prefixed `[SUGGESTION]` and a structured description following `docs/backlog/instructions.md`.

Do not create backlog items for low-value style nits. Only log medium- or high-value improvements.
```

5. Clarify task ownership:
   - Claude/task backlog lives in `.claude/tasks/` if that mechanism exists or is created.
   - Human-managed todos live in `docs/todo.md`.

Move existing todo lines from `CLAUDE.md` to `docs/todo.md`.

---

## 6. Backlog script and task portability

Upload, inspect, and debug the `claude-backlog.py` script that was previously provided for introspecting Claude tasks.

Before implementing task integration, inspect whether this repo/local Claude setup actually supports:

- `.claude/tasks/`
- `~/.claude/tasks/`
- `TaskCreate`
- task hooks
- structured task metadata

Also evaluate task portability:

- `~/.claude/tasks/` is outside the repo, so suggestions may not travel with the project.
- If portability matters, recommend whether to symlink a project-specific task folder into the repo under `.claude/`.
- If using a symlink or repo-local task folder, ensure sensitive fields are gitignored.

Do not make symlinks, global task changes, or risky filesystem changes without explaining them first.

---

## 7. Workstream docs rename/refactor

Refactor `docs/claude_bucket_instructions` into a workstream-oriented document named something like:

- `docs/workstreams/card_specific.md`

Use these definitions:

```markdown
Bucket: A scoped cluster of similar tasks sharing logic patterns and likely touchpoints, intended for one focused Claude session.

Workstream: A broader multi-session effort composed of buckets, organized to preserve architectural continuity while limiting per-session context.
```

Preserve the existing purpose of the bucket instructions, but make the naming and structure clearer.

---

## 8. Hooks and notifications

Evaluate and, if safe, implement hooks for:

1. Task creation notification:
   - When a task is created, print a formatted terminal notification:
     ```text
     → [BACKLOG] logged: <subject>
     ```
   - If feasible, play a subtle sound.

2. Input-needed notification:
   - When Claude needs user input, send a desktop notification so I can switch to other tasks without watching the terminal.

If hooks are environment-specific, report the needed setup instead of guessing.

Do not implement notifications until you have inspected the available hook mechanism and explained the chosen approach.

---

## 9. Claude memory recommendations

Recommend how to use `.claude/memory` or the appropriate Claude memory mechanism to improve the educational value of using Claude.

Goals:
- learn Claude / Claude Code
- learn AI-assisted development workflows
- learn software development generally
- learn Python specifically

Constraint:
- Do this only if it does not add significant recurring token cost.

Prefer concise, durable memory entries over long educational notes.

Before changing memory, inspect the available mechanism and recommend specific entries. Ask for confirmation before adding durable memory entries.

---

## Final report

At the end, report:

1. Files changed.
2. Files created.
3. Any assumptions made.
4. Any requested items skipped or deferred, with reasons.
5. How to verify the new setup.
6. The smallest next follow-up task you recommend.
