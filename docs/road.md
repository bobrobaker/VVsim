# MTG Simulator Roadmap

## 1. How to use this doc

Purpose: orient Claude/Codex/human sessions around project phase, history, next work, and bounded implementation surfaces.

Current phase marker:

`<----- Ongoing phase ----->`

A **phase** is a high-level deliverable with stable interfaces. A **workstream** is a refinable effort inside a phase. A **bucket** is a bounded implementation slice, usually sharing files, invariants, or tests.

Each phase should state: deliverable, surfaces, durable design decisions, file/doc changes, validation, token estimate, and exit criteria. Keep details high-level enough to start a refinement conversation, not enough to implement directly.

---

## 2. Phase roadmap

### Phase 1 — Core simulator loop

**Status:** historical / complete.

**Deliverable:** Single-turn Vivi + Curiosity cEDH spell-chain simulator: state setup, initial draw, action loop, win/brick outcomes, trace output.

**Surfaces:** `simulate_run`, `RunConfig`, `RunResult`, `GameState`, `ManaPool`, `ManaCost`, `run_single`, trace formatter.

**Design:**

- Single-turn goldfish engine, not full multiplayer MTG.
- Model only rules relevant to Vivi spell chains.
- Cards mostly move as names through zones; permanents are lightweight objects.
- Seed/config control reproducibility.
- Outcomes: extra-turn win, spell-count win, no-actions brick, no-useful-actions brick, invalid-state error.

**File/doc changes:** `mtg_sim/sim/` core package; CLI entrypoint; CSV card metadata surface.

**Validation:** single traces; runner/state/mana/trace tests.

**Context notes:** architecture overview and commands are stable; seed/hand/deck experiments are per-session.

**Estimate:** 120k–220k tokens.

**Exit:** runner can simulate a starting state, resolve actions, detect wins/bricks, and print readable traces.

---

### Phase 2 — Core loop boundaries

**Status:** historical / complete.

**Deliverable:** Legal-action generation, stack representation, and state mutation are separate enough to test and extend safely.

**Surfaces:** `action_generator.py`, `resolver.py`, `actions.py`, `stack.py`, `GameState.stack`, `validate_state`.

**Design:**

- `action_generator.py`: what can happen.
- `resolver.py`: what happens after selection.
- `Action` / `CostBundle` / `EffectBundle`: shared contract between generator, policy/manual choice, and resolver.
- Explicit stack objects for spells, draw triggers, targets, and resolution order.
- Curiosity draw triggers sit above the spells that created them.
- Zone consistency checked centrally.

**File/doc changes:** action contract split out; stack object added; generator/resolver responsibilities clarified.

**Validation:** action generation, stack resolution, mana spending, zone movement, state validation.

**Context notes:** generator/resolver split is a durable rule; include only exact anchors in implementation prompts.

**Estimate:** 160k–300k tokens.

**Exit:** legal actions can be generated independently from resolution, stack behavior is visible, and invalid zone duplication is caught.

---

### Phase 3 — Card behavior buckets

**Status:** historical / mostly complete; future bucket passes possible.

**Deliverable:** Enough deck-specific card behavior exists for traces and policy choices to be strategically meaningful.

**Surfaces:** `card_behaviors.py`, `CARD_BEHAVIORS`, `CardBehavior.generate_actions`, `resolve_cast`, `on_enter`, `generate_mana_actions`, `generate_activate_actions`, `card_library.csv`, card specs.

**Design:**

- Generic scaffolding stays in `action_generator.py`.
- Card exceptions live in `card_behaviors.py`.
- Behavior hooks may own generation, resolution, mana, battlefield effects, or pending choices.
- Simulator simplifications should be explicit when they encode project assumptions.
- Do not model real-card behavior unless it matters for current simulation goals.
- Bucket card work to constrain reads/tests.

**Historical buckets:** nonland mana sources; misc spells; fetchlands; MDFCs; counterspells/pitch spells; generic no-op permanents; exile display; mana-payment fixes.

**File/doc changes:** behavior registry expanded; focused tests added; bucket prompts / CompanionDocs introduced.

**Validation:** card-behavior tests, `run_single` traces, regression tests for mana, stack draining, target legality, zone movement.

**Context notes:** Prebaker prompts should be touchpoint-heavy; grep registry/fields before large reads; inspect existing test helper patterns before writing tests.

**Estimate:** 300k–650k tokens.

**Exit:** important mana sources, tutors, free spells, counters, MDFCs, fetchlands, and engines are modeled well enough that policy work is not dominated by missing legality/resolution bugs.

---

### Phase 4 — First-pass policy + manual observation

**Status:** historical / mostly complete.

**Deliverable:** Manual and policy modes share legal actions; policy choices are scored, visible, configurable, and loggable.

**Surfaces:** `policies.py`, `policy.toml`, `rank_actions`, `ScoredAction`, `score_action_with_reasons`, manual display in `runner.py`, `policy_adjustments.jsonl`, `manual_observations.jsonl`, `run_single --manual`.

**Design:**

- Policy scoring is not legality.
- Manual mode shows score/rank/delta so human choices become useful feedback.
- Override reasons go to policy-adjustment logs.
- Full decision snapshots go to manual-observation logs.
- Trainable policy feedback must be separated from bug-tainted observations.
- Weights should be editable outside Python.

**File/doc changes:** TOML policy config; JSONL logs; manual commands for note/missing/illegal/resolution; richer state snapshots.

**Validation:** policy scoring/config tests, manual display tests, JSONL write tests, observation snapshot tests, CLI default tests.

**Context notes:** config is authoritative; clear policy caches in tests; focused policy tests before broad suite.

**Estimate:** 220k–420k tokens.

**Exit:** a human can run manual mode, see ranked policy choices, choose differently, explain why, and save trainable/non-trainable data.

---

### Phase 5 — Context management + multi-agent workflow

`<----- Ongoing phase ----->`

**Status:** ongoing coordination phase.

**Deliverable:** Claude/Codex/human work can be planned and handed off with less context waste, fewer repeated mistakes, and clearer phase/workstream/bucket boundaries.

**Surfaces:** `CLAUDE.md`, possible `AGENTS.md`, `.claude/rules/**`, `docs/notes/**`, Prebaker prompts, introspection notes, handoff artifacts, this `docs/road.md`.

**Design:**

- Durable architecture rules live in stable docs/rules.
- Bucket specifics live in short changing prompts.
- Use line anchors/touchpoints to reduce exploratory reads.
- Route repeated mistakes into durable docs, not ad hoc reminders.
- Use shared handoff files for Claude ↔ Codex; do not rely on Claude-only task tools.
- Keep roadmap, backlog, workstreams, bucket prompts, and session logs distinct.

**File/doc changes:** roadmap added; context notes/rules refined; Codex-facing context and handoff format planned; `AGENTS.md` updated with Codex task mode; Route B (`docs/workstreams/codex-subagent-refactor/`) implemented and complete (B01–B07 done, 72 agents tests pass).

**Validation:** fewer repeated introspection mistakes; bounded implementation prompts; usable handoffs with status/blockers/tests/next prompt.

**Context notes:** `CLAUDE.md` should route, not absorb the roadmap. CompanionDocs hold file gotchas; Prebaker prompts hold execution touchpoints.

**Estimate:** 80k–180k tokens.

**Exit:** future sessions can identify phase, choose workstream, avoid known context drains, and prepare bounded prompts without rediscovering project structure.

---

### Phase 6 — Validate logs against action/resolution accuracy

**Status:** next implementation phase.

**Deliverable:** Manual observations are trustworthy enough for policy/trainer work because legality bugs, resolution bugs, and true policy mistakes are separated.

**Surfaces:** `manual_observations.jsonl`, `policy_adjustments.jsonl`, manual note commands, observation snapshot schema, possible review/replay tooling.

**Design:**

- Human disagreement is not automatically training data.
- Missing actions → generator/card-behavior bug.
- Illegal offered actions → legality bug.
- Resolution bugs taint later snapshots.
- Trainer should consume only trainable examples, or preserve invalid-reason metadata.

**Likely workstreams:**

1. Review selected manual logs.
2. Fix missing/illegal action bugs.
3. Fix resolution/zone/stack/card/mana bugs.
4. Audit observation schema for trainer features.
5. Add replay/review helpers only if manual review is too slow.

**File/doc changes:** maybe `scripts/review_observations.py`, `scripts/replay_observation.py`, observation-validity docs, regression fixtures.

**Validation:** curated manual sessions, bug-regression tests, trainable vs non-trainable counts, examples of pure policy mistakes.

**Context notes:** review small JSONL slices; avoid loading whole logs; route repeated bugs into tests or CompanionDocs.

**Estimate:** 150k–350k tokens.

**Exit:** reviewed trainable observation set exists; known action/resolution bugs are fixed or excluded; remaining data is suitable for policy/trainer work.

---

### Phase 7 — Sparse weighted ranker + trainer

**Status:** next / partly underway depending on latest code.

**Deliverable:** Strongest practical sparse weighted ranker: inspectable features, editable weights, offline trainer, tests, and validation against manual observations.

**Surfaces:** `policies.py`, `policy.toml`, sparse feature extraction, weighted scoring, manual observations, trainer script, trainer outputs, policy/trainer tests.

**Design:**

- Prefer sparse inspectable features over opaque models for now.
- Separate feature extraction from weighting/scoring.
- Keep legality outside policy.
- Train only on policy-trainable observations.
- Trainer output must be reviewable before promotion to config.
- Evaluate against tests, observations, and representative traces.

**Likely workstreams:**

1. Audit SWR contract and feature names.
2. Extract training examples from observations.
3. Build/refine offline trainer.
4. Evaluate baseline vs trained policy.
5. Promote reviewed weights into `policy.toml`.
6. Add regression tests for features, scoring, config cache, trainer output.

**File/doc changes:** trainer module/script; trainer tests; sample observation fixtures; policy-eval reports.

**Validation:** feature/ranker unit tests, tiny trainer fixtures, observation replay accuracy, curated seed comparisons, human review of changed weights.

**Context notes:** keep observation examples small; grep long tests before reading; focused tests first, broad suite later with warning suppression.

**Estimate:** 250k–550k tokens.

**Exit:** SWR has a tested trainer workflow; weights are interpretable; evaluation improves decisions without hiding legality/resolution bugs.

---

### Phase 8 — Monte Carlo analysis + deck-choice data

**Status:** long-term.

**Deliverable:** Simulator can answer deck and starting-state questions: card/package win-rate impact, starting-card impact, seed sensitivity, and common failure modes.

**Surfaces:** `run_monte_carlo`, deck construction/card IDs, simulation result aggregation, policy config selection, CSV/JSONL/Markdown reports, seed-set management.

**Design:**

- Monte Carlo is analysis, not correctness proof.
- Results must be reproducible by seed, decklist, policy config, and starting state.
- Separate experiment definition from aggregation.
- Include sample size / uncertainty so small deltas are not overread.
- Aggregate failures should link back to representative traces.

**Likely workstreams:**

1. Define experiment config format.
2. Refactor batch runner for structured reproducible results.
3. Compare card/package inclusion.
4. Estimate starting-card impact.
5. Summarize brick/failure modes.
6. Generate human and machine-readable reports.

**File/doc changes:** Monte Carlo script refactor, experiment config directory, report/output directory, analysis docs.

**Validation:** deterministic small-run fixtures, reproducibility tests, aggregate-count sanity checks, representative trace inspection.

**Context notes:** do not load large result files into coding sessions; summarize or sample.

**Estimate:** 250k–600k tokens.

**Exit:** project can answer practical questions like “what is this card/package’s win-rate impact?” with reproducible outputs.

---

## 3. Current phase detail

### Phase 5 — Context management + multi-agent workflow

This phase is about making future simulator work cheaper and less repetitive, not changing simulator mechanics. The project now has mature enough surfaces—runner, generator, resolver, card behaviors, policy, manual observations, and SWR direction—that roadmap/context routing is worth doing before deeper trainer/Monte Carlo work.


### Near-term workstreams

#### A. Finish roadmap doc

**Goal:** accepted `docs/road.md`.

Tasks: review phase names, confirm current marker, add missing history, save final doc, optionally link from an index doc. Do not move this into `CLAUDE.md`.

**Estimate:** 10k–30k tokens.

#### B. Define handoff artifacts

**Goal:** shared planner ↔ implementer handoff format, especially Claude ↔ Codex.

Likely fields: phase, workstream, bucket, goal, status, files touched, tests run, blockers, required/conditional/do-not-read touchpoints, decisions, open questions, next prompt.

**Estimate:** 30k–80k tokens.

#### C. Codex context integration ✓ done

**Goal:** Codex-compatible context surfaces.

**Completed:** `AGENTS.md` finalized with Codex working rules, task-mode behavior, and role boundaries. Route B implemented end-to-end (`docs/workstreams/codex-subagent-refactor/`, B01–B07). Claude entry point at `.claude/skills/outsource-codex/SKILL.md`; Codex entry point at `.agents/skills/codex-implementer/SKILL.md`. Operational docs at `.agents/README.md`.

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


