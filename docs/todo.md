### Near-term workstreams

#### A. Finish roadmap doc

**Goal:** accepted `docs/road.md`.

Tasks: review phase names, confirm current marker, add missing history, save final doc, optionally link from an index doc. Do not move this into `CLAUDE.md`.

**Estimate:** 10k–30k tokens.

#### B. Define handoff artifacts

**Goal:** shared planner ↔ implementer handoff format, especially Claude ↔ Codex.

Likely fields: phase, workstream, bucket, goal, status, files touched, tests run, blockers, required/conditional/do-not-read touchpoints, decisions, open questions, next prompt.

**Estimate:** 30k–80k tokens.

#### C. Codex context integration

**Goal:** Codex-compatible context surfaces.

Tasks: decide `AGENTS.md` / nested agent files; translate Claude rules without Claude-only tools; define where Codex writes handoffs for Claude.

**Estimate:** 40k–100k tokens.

#### D. Introspection routing cleanup

**Goal:** repeated mistakes become stable rules/docs.

Tasks: identify repeated introspection failures; route to `CLAUDE.md`, `.claude/rules/tests.md`, CompanionDocs, Prebaker instructions, or roadmap; avoid bloating `CLAUDE.md`.

**Estimate:** 30k–70k tokens.

### Current-phase invariants

- `CLAUDE.md` routes; it should not become the whole roadmap.
- Workstream docs hold medium-term plans.
- Prebaker prompts are short, execution-oriented, touchpoint-heavy.
- CompanionDocs hold per-file gotchas.
- Introspection notes justify durable rule changes only when mistakes recur or are costly.
- Codex should coordinate through shared files/handoffs, not Claude-only task tools.

### Risks

- Over-documenting until future sessions load too much.
- Duplicating rules across files and causing drift.
- Treating Claude and Codex as if they share a task system.
- Making the roadmap too detailed to stay stable.
- Marking the wrong phase as current.

### Exit criteria

- `docs/road.md` accepted.
- Current phase marker accurate.
- Work can be described as phase → workstream → bucket.
- Claude/Codex handoff format agreed or explicitly deferred.
- `CLAUDE.md` points to the right docs without absorbing them.
- Recent introspection lessons routed or deferred.

---

### 4. Immediate next work

1. Finalize `docs/road.md`.
2. Define structured handoff artifact format.
3. Run small manual-observation validation pass on curated seeds.
4. Separate action/resolution bugs from policy mistakes.
5. Use reviewed logs for SWR/trainer evaluation.
6. Expand Monte Carlo only after policy/trainer confidence improves.

Reason: bad observations make bad training data; weak policy makes Monte Carlo conclusions noisy.

---

### Backlog (misc unsorted tasks)

- File system refactor each card to their own file. 