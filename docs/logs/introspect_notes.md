# Introspection Notes

Qualitative findings from past sessions. Append new entries via `/introspect`.

## Route B Scout / Protocol Hardening

**Session:** 2026-05-13. Ran outsource-codex scout (99 cards, 26 castable). Fixed Route B protocol: `codex exec -o` contract, OpenAI strict schema (3 fix cycles), worktree-from-HEAD propagation, SKILL.md frontmatter, preflight staleness warning. 85 agents tests pass.

### Estimated token ratio

~10:1 input:output. Long session — multiple Codex re-runs, 3 schema fix cycles, compacted prior-context re-ingestion, multi-file protocol sync.

### What was useful

- `implementation_result.json` — essential, fixed 3 times.
- `run_codex_task.py` — core edit surface, read multiple times but all relevant.
- `test_schema_strict.py` (created new) — high value, now prevents schema regressions.
- `test_run_codex_task.py` — necessary for fake_codex fixture updates.

### Main token drains

1. **Schema fixed 3 separate times** — each commit revealed the next OpenAI strict compliance issue. A single upfront checklist (additionalProperties:false, all props in required, nullable for optional) would have collapsed 3 cycles to 1. Now self-enforcing via `test_schema_strict.py`.
2. **5–6 Codex re-runs** — each protocol fix required: commit → run → read error → diagnose → fix. Most cycles caused by schema errors or uncommitted files not propagating to worktree.
3. **Multi-file protocol sync** — AGENTS.md, both SKILL.md files, how_to_use.md all needed updating when write-result contract changed. Each required a separate read + edit.

### Concrete recommendations

- Before using `--output-schema` with any JSON schema, run `test_schema_strict.py` equivalent checks first. Now encoded in tests — self-enforcing.
- Worktree-from-HEAD constraint is now in CompanionDoc for `run_codex_task.py` and covered by `agents-notes.md` glob rule.
- When the write-side protocol changes (how Codex emits output), enumerate all instruction surfaces upfront (AGENTS.md, SKILL.md, outsource SKILL.md, how_to_use) before editing any of them.

---

## B04 Result Diff Patch

**Session:** 2026-05-13. Built diff/patch/result capture in `run_codex_task.py`, 23 tests pass (47 total). Fixed CompanionDoc rule gap.

### Estimated token ratio

~6:1 input:output. Short session dominated by compacted prior-context re-ingestion.

### What was useful

- `B04_result-diff-patch.md` — essential.
- `task_queue.py` full read — confirmed reusable helpers.
- `implementation_result.json` — confirmed `files_changed` field name cheaply.
- `sim-notes.md` — needed as rule template; earned its cost.

### Main token drains

1. **Compacted summary re-ingestion** — dominant; avoidable by compacting before starting the next bucket, not after.
2. **Three test-failure debug cycles** — fake SHA silent-empty diff, stdout pollution, `base_commit=""` fix; recurrence of B03 pattern (bugs caught only in test runs).
3. **MEMORY.md write + immediate revert** — added pointer as workaround, then removed it when rule was created; wasted two round-trips.

### Concrete recommendations

- Both B04 gotchas are now in `docs/notes/scripts/agents/run_codex_task.py.md` and covered by `agents-notes.md` rule.
- CLAUDE.md now requires glob rule whenever a CompanionDoc is created outside `mtg_sim/`.
- Pattern: when a workaround (MEMORY.md pointer) is created because the right mechanism (glob rule) is missing, create the mechanism first.
- Compact re-ingestion drain is avoidable — recommend compact *before* the next bucket at the end of every bucket session, not just when context is large.

---

## Misc Spells Bucket

**Session:** 2026-05-05, misc_spells card behavior bucket. Implemented 10 new behaviors, fixed 5 existing, added 44 tests.

### Estimated token ratio

Input heavy — roughly **5:1 input:output**. The session read many large file ranges to orient before writing. Output was dense but much smaller than total context loaded.

### What was useful

- `docs/misc_spells_claude_prompt_concise.txt` — high signal, gave exact line anchors upfront. Paid for itself by eliminating most exploratory greps.
- `docs/card_specifics.md:510-622` — essential spec. Tight range, no waste.
- `docs/claude_bucket_instructions.md:19-49` — short and necessary.
- Parallel reads of `card_behaviors.py:600-666`, `card_behaviors.py:1027-1062`, `card_behaviors.py:1419-1443`, `card_behaviors.py:711-731` — all immediately actionable.
- `card_library.csv` grep for misc cards — single targeted grep, high yield.

### Main token drains

1. **`action_generator.py` and `resolver.py` repeated reads.** Several ranges were read (192-276, 308-400, 641-753, 772-778 from action_generator; 87-164, 271-359 from resolver) before I had a complete enough picture to code. Some of these could have been a single wider read instead of sequential narrow ones.

2. **`state.py` full orientation read (14-141).** Read ~130 lines to confirm that `_opponent_player_perm` didn't exist. A single grep (`grep -n "_opponent"`) would have answered the same question in one tool call.

3. **`card_behaviors.py` registry read (1680-1730).** Read to check what was registered. Could have been a grep: `grep -n "Snapback\|Bauble\|Cave\|Boomerang"` which I eventually did anyway.

4. **Blazing Shoal test file read (full, 90 lines).** Needed only the helper pattern (~10 lines). Could have read offset=17, limit=15.

5. **Test debugging loop.** Three test runs were needed: initial run (11 failures), then after `ManaPool(generic=)` fix + `_drain_stack` introduction, then final clean run. The `ManaPool` kwargs error should have been caught by grep before writing the test file: `grep -n "ManaPool(" mtg_sim/tests/test_blazing_shoal.py` would have shown the `ManaPool()` / `ManaPool(U=1)` pattern in 5 seconds.

6. **Debug Python one-liner for Thunderclap.** Required after test failure because the sacrifice perm_id didn't match the expected Mountain — a Volcanic Island was found first. Could have been anticipated: `_we_control_mountain` uses a set of dual-land names, and the initial state always has a Volcanic Island. Grep + quick read of `_MOUNTAIN_LANDS` before writing the test would have caught this.

### Concrete recommendations for next bucket

- **Grep ManaPool usage before writing tests.** `grep -n "ManaPool" mtg_sim/tests/test_blazing_shoal.py` takes one tool call and prevents a whole debug cycle.
- **Grep state fields before assuming they exist.** `grep -n "_opponent" mtg_sim/sim/state.py` answers "is there a player dummy?" in one call, not a 130-line read.
- **Read the registry with a grep, not a file read.** `grep -n "Snapback\|Boomerang\|Cave" card_behaviors.py` instead of reading lines 1680-1730.
- **Check initial state contents before writing battlefield-sensitive tests.** `_build_initial_state` puts a Volcanic Island on the battlefield by default. Any test that checks for "Mountain" removal should grep the initial state setup first.
- **Prefer one wider read over two narrow sequential reads.** For action_generator.py, the five separate range reads (192-276, 308-400, 641-753, 747-753, 772-778) could have been two: read lines 192-400 for cast/alt scaffolding, read 641-778 for target helpers. Same information, two tool calls instead of five.
- **Write `_drain_stack` helper first, before any resolution tests.** Every test that resolves spells needs it. Defining it upfront (one read of any existing test that resolves spells) saves multiple debug cycles.

---

## Nonland Mana Sources

**Session:** 2026-05-05, nonland_mana_sources bucket. Fixed 3 behaviors (Rite of Flame, Chrome Mox, Paradise Mantle), added flashback graveyard generation, added 41 tests.

### Estimated token ratio

Input heavy — roughly **6:1 input:output**. The behavior code reads were large and sequential. Output (test file + code edits) was relatively compact, but context loaded to arrive there was substantial.

### What was useful

- `docs/nonland_mana_sources_claude_prompt_concise.txt` — high signal. Exact line anchors for `card_behaviors.py` ranges prevented all exploratory reads. Worth every token.
- `card_behaviors.py:48-358` in one read — the right granularity. All mana-source behaviors in sequence; no second pass needed.
- `grep -n "CARD_BEHAVIORS"` to locate the registry — one call, answered immediately.
- `grep -n "Paradise Mantle\|Ragavan" card_library.csv` — one call confirmed both cards' CSV fields before writing any behavior.
- `sed -n '513,540p' action_generator.py` to check the mana action loop — small targeted read, directly answered "will `generate_mana_actions` be called for Paradise Mantle?"

### Main token drains

1. **Sequential resolver.py reads.** Read lines 271-320 then 320-360 separately because 271-320 didn't include the full `_resolve_activate_mana` body. A single `sed -n '271,360p'` would have covered both in one tool call. This pattern repeated across the session: read a range, realize it ends mid-function, read again.

2. **`actions.py` orientation read.** Read lines 8-20 to get action type constants, but these were already visible in the earlier `grep -n "ACTIVATE_MANA\|SACRIFICE_FOR_MANA"` result. The grep output had the constants inline — reading the file added nothing new. Cost: ~25 lines for zero new information.

3. **`_gen_special_hand_actions` read after SSG duplicate bug.** When SSG produced 2 duplicate actions in tests, the fix required reading `action_generator.py:598-618` plus `action_generator.py:190-216`. These were already partially covered by the earlier `sed -n '513,540p'` read. A grep for `generate_actions.*state.*card_name` before writing the test would have flagged the dual-path issue upfront.

4. **Test file written without `_resolve_stack` helper.** The Rite of Flame and Strike It Rich tests used inline `RESOLVE_STACK_OBJECT` loops that broke because they didn't handle the draw trigger on the stack. The previous session's audit already flagged this exact pattern ("Write `_drain_stack` helper first"). The lesson was not applied: `_resolve_stack` was only added after two test failures, costing one full debug cycle.

5. **Four Python debug one-liners for Strike It Rich flashback.** After the flashback tests failed, the diagnosis required: (1) verifying `alt_costs` field name, (2) tracing through `_gen_normal_and_alt_cast_actions`, (3) checking cost parsing for `2R`, (4) confirming `can_pay_cost` result. Steps 1-2 could have been combined into a single debug call that printed both the field and the generated actions. Steps 3-4 were needed but the wrong mana amount (`R=2` instead of `R=3`) was a test authoring error—checking `2R` = 3 mana total before writing the test would have prevented it.

6. **`state.py:14-25` read.** Read to check `attached_to` field exists on `Permanent`. This could have been a grep: `grep -n "attached_to" mtg_sim/sim/state.py` — one line, same answer.

### Concrete recommendations for next bucket

- **Apply the `_resolve_stack` lesson from last session before writing any cast/resolve tests.** Define the helper in the first 10 lines of the test file. This session repeated the exact failure mode documented in the previous audit entry.
- **Check mana cost arithmetic before setting test mana amounts.** For any flashback/alt cost with a numeric component (e.g. `2R`), compute `generic + pips = total` before writing `ManaPool(...)`. `2R` = 3 mana, not 2. Takes 5 seconds; saves a debug cycle.
- **Grep field existence, don't read the file.** `grep -n "attached_to\|imprinted_card" state.py` answers field questions in one line. Reading `state.py:14-25` added no new information beyond what a grep returns.
- **Combine sequential small reads into one range.** Any time you read lines N–M, ask whether the function continues past M. If yes, extend the range before issuing the read. This session issued at least 3 pairs of sequential reads on resolver.py/action_generator.py that could have been single reads.
- **Before writing a behavior that uses a new `alt_cost_type`, grep resolver.py for how existing ones are handled.** The `equip_mantle:` and `tap_mantle_vivi` handlers were added correctly first-try because the `tap_creature:` precedent was visible in the context — but that was from reading 50+ lines to find it. A grep `grep -n "alt_cost_type" resolver.py` returns all 8 handlers in one shot and takes 1/10th the context.
- **Don't re-read action type constants after a grep already showed them.** If `grep -n "ACTIVATE_MANA"` returns the constant definition inline, the file read is redundant. Trust grep output for simple constant lookups.

---

## Mana Payment Fix

**Session summary**: Read 6 file ranges, made 2 edits (mana.py + test file), ran 2 test commands. The actual fix was 8 lines swapped in one function.

**Estimated token ratio**: ~5:1 input:output. Input dominated by file reads (~350 lines total) and system context (CLAUDE.md, MEMORY.md, RefineMana.md). Output was small — the edits and test runs.

**What was useful:**
- `RefineMana.md` — high signal. Directed every touchpoint, explained the goal clearly, and included the test tips section which prevented the usual mana arithmetic bug.
- `mana.py` full read — the entire file was the edit surface; reading it in full was appropriate at 169 lines.
- `test_mana_payment.py` full read — needed to write non-duplicate regression tests and verify existing test coverage.

**Main token drains:**
1. **Full test suite output with 189 warnings** — the broad `pytest mtg_sim/tests/ -q` run printed ~130 warning lines that were pure noise. The focused test already passed; the broad run added zero correctness signal beyond confirming no regressions, but consumed ~2× the output tokens of the focused run.
2. **resolver.py reads (two ranges, ~41 lines)** — required by RefineMana.md "required touchpoints" but contributed nothing to the fix. Both ranges confirmed `pay_cost` is called the same way in two places. The actual edit never touched resolver.py. These were insurance reads.
3. **actions.py read (42 lines)** — same pattern: confirmed CostBundle structure hadn't changed. Zero edit value. Required by spec but the conclusion was "no change needed."

**Concrete reductions for next session:**
- **Run focused test first, broad suite only if it passes.** `pytest test_mana_payment.py -q` is 5 lines of output. Only escalate to the full suite after the focused test is green. This session ran focused first but then ran full suite unconditionally — the full suite output was ~10× larger.
- **Suppress warnings in broad runs.** `pytest mtg_sim/tests/ -q -W ignore::UserWarning` would have cut the broad-run output by ~80%. The warnings are known noise (unregistered cards) and add no debugging value.
- **Demote resolver/actions reads to conditional.** RefineMana.md put them in "required touchpoints" but they were effectively conditional — only needed if the fix required changes there. A 1-line grep (`grep -n "pay_cost" resolver.py`) answers "is pay_cost called here?" without reading 40 lines of context.
- **RefineMana.md tip**: Keep "required touchpoints" to files that will actually be edited. Move read-to-verify touchpoints (resolver.py, actions.py) under "conditional" with a trigger condition like "only if mana.py edit changes pay_cost signature."

---

## Exile Display Fix

**Session:** 2026-05-07, added `Exile:` line to `_manual_choose_action`, created runner.py CompanionDoc, updated sim-notes.md rule for permission-gated CompanionDoc creation, refined introspect skill (Steps 4/7 split).

### Estimated token ratio

~3:1 input:output. Smallest session to date — 2-line fix plus housekeeping. Input dominated by system context and session prompt rather than exploratory reads.

### What was useful

- `runner.py:186–219` — directly edited, earned.
- `state.py:65–96` — confirmed `exile` field, earned.
- `state.py.md` CompanionDoc — format reference for creating runner.py.md, earned.
- Greps for action type constants and function locations — all single-call, high yield.

### Main token drains

1. **`actions.py:1–55` read** — needed only because `Action(...)` kwargs were guessed wrong (`cost=` instead of `costs=`, `PASS_PRIORITY` which doesn't exist). One grep of an existing test for `Action(` would have prevented it entirely.
2. **Test file written twice** — wrong import and wrong kwarg names required a grep + read + rewrite cycle. Same root cause as drain 1.
3. **Session prompt overhead** — ~150-line task prompt for a 2-line fix; not actionable but reflects in ratio.

### Concrete recommendations

- **Before writing any `Action(...)` in a test, grep an existing test for `Action(` to get exact kwarg names.** `grep -n "Action(" mtg_sim/tests/test_nonland_mana_sources.py` returns `source_card=`, `costs=`, `effects=` in one shot. This is now logged as a [SUGGESTION] task to add to `tests.md`.
- **Introspect skill: log/notes writes are unconditional; only ask confirmation for routing changes.** Split SUGGESTION report into Step 7 so it can't be skipped as housekeeping. (Implemented this session.)

---

## Policy Priorities Refactor

**Session:** 2026-05-07, policy scoring refactor — pitch penalty, free mana source bonus, win-cast mana priority, red mana preference, red-spend penalty. 390 tests pass; 10 new tests added.

### Estimated token ratio

~4:1 input:output. Lighter than recent sessions — no exploratory reads, mostly targeted greps and one full file read.

### What was useful

- `policies.py` full read — earned; full rewrite of scoring logic.
- `docs/notes/sim/policies.py.md` — earned; touchpoints confirmed before editing.
- Targeted greps (alt_cost_type values, CostBundle fields, ManaPool fields, card data fields) — all high yield, single-call each.
- `test_policy_config.py` full read — earned; needed insertion point and helper patterns.

### Main token drains

1. **`test_manual_policy_feedback.py` head read (80 lines)** — only needed `_cast()` helper pattern (~15 lines). A single `grep -n "def _cast"` would have been sufficient.
2. **Wrong mana cost for Final Fortune in tests** — assumed pip_r=1 (costs {R}) but it costs {R}{R} (pip_r=2). Two tests failed; required inspect + fix cycle. A `get_card('Final Fortune').pip_r` one-liner before writing the assertion would have prevented this entirely.
3. **policy.toml discovered late** — noticed only when sanity check showed `mana_ritual_bonus=40` (old value). Should check for TOML file existence at the start of any policy session and treat it as the canonical source.

### Concrete recommendations

- **Extend "verify ManaPool arithmetic" rule to cover card pip counts.** `get_card('<name>').pip_r` before writing cost-sensitive tests prevents wrong-amount cycles. (Added to `tests.md`.)
- **At start of any policy session, check if `policy.toml` exists and treat it as authoritative.** Update it alongside `_DEFAULTS` whenever new keys are added. (Added to `policies.py.md` Gotchas.)
- **When only the helper pattern is needed from a test file, grep `def _cast` instead of reading the file.** Saves ~65 lines of context.

---

## Policy Config + Scoring Visibility

**Session:** 2026-05-07, policy scoring refactor. Moved weights to `mtg_sim/config/policy.toml`, added `ScoredAction`/`rank_actions`/`score_action_with_reasons`, rewired manual mode to display scores/delta/reasons and log JSONL overrides. 380 tests pass; 19 new tests added (1 minor fix during test run).

### Estimated token ratio

~8:1 input:output. Heavy reading phase from session prompt's pre-listed touchpoints, then large parallel writes.

### What was useful

- Session prompt's explicit required/conditional/do-not-read structure — eliminated all exploratory reads. Every file touched was pre-identified with line anchors.
- `policies.py` full read (368 lines) — necessary; full rewrite required full read.
- `test_runner_manual_display.py` full read — confirmed backward compatibility before editing `_manual_choose_action`.
- `mana.py:1–50` and `state.py:51–130` — both needed for JSONL snapshot field names.

### Main token drains

1. **runner.py read in 3 separate chunks with overlap** (1–65, 63–120, 117–242). A single read of 1–250 would have covered all three. Recurring pattern from prior sessions.
2. **Test grep returned 30+ lines across many files before reading `test_runner_manual_display.py` directly.** The grep confirmed which file to read, but a direct read would have been faster. If the target file is already known from the session prompt, skip the grep.
3. **`state.py:51–130` included opponent-dummy fields (100–130) not needed for snapshot serialization.** Limit of ~90 would have been sufficient.

### Concrete recommendations

- **When the session prompt already names the target file, read it directly; skip the broad grep.** The grep for test patterns returned `test_runner_manual_display.py` as the only relevant file — which was already in the session prompt's touchpoints. Direct read would have saved ~20 lines of grep noise.
- **For runner.py sessions touching both RunConfig and simulate_run: read lines 1–250 in one shot.** (Added to runner.py.md CompanionDoc.)
- **Module-level caches need `_clear_cache()` + conftest.py autouse.** Discovered here for `_config_cache`; added to `tests.md`.
- **Recurring drain: sequential narrow reads of runner.py.** Third session to exhibit this. If it appears again, escalate to CLAUDE.md.

---

## Manual Observation Logging

**Session:** 2026-05-08. Added obs buffer, n/m/i/r commands, session-end save, v2 state snapshot, `RunConfig.manual_observation_log_path`, CLI arg. 400/400 pass; 10 new tests.

### Estimated token ratio

~4:1 input:output. Reads were targeted; output was dense (runner.py rewrite + new tests).

### What was useful

- Session prompt with explicit required/avoid touchpoints — eliminated all exploratory reads.
- Sample JSON files (`sample_manual_decision_snapshot.json`, `sample_state_snapshot_v2.json`) — confirmed exact schema shape before writing `_state_snapshot`.
- `runner.py` full read — appropriate; entire file was the implementation surface.
- Targeted greps for `ScoredAction`, `Permanent`, `StackObject` fields — single calls, high yield.

### Main token drains

1. **Full test file read (234 lines)** — needed `Action(` kwargs, `log_path=` call sites, and helper patterns. All three could have been targeted greps (~15 lines total). Full-file-read-for-test pattern recurred from "Policy Priorities Refactor" session.
2. **Post-rename grep to find remaining `log_path=` call sites** — should have grepped before renaming to know the blast radius. Two multi-pass fix rounds resulted.
3. **Two-pass grep to confirm `get_card_by_id`** — one well-formed grep would have sufficed.

### Concrete recommendations

- **Full-test-file-read pattern escalated to `tests.md`** (two new rules added this session): grep for specific patterns before reading; grep for parameter names before renaming.
- **No new destinations needed** — both takeaways routed to `tests.md` where they're auto-loaded for test-file work.

---

## Default Obs Log Path

**Session:** 2026-05-08. Added default path for `--manual-observation-log` in `run_single.py`; runner already appends. Closed backlog task #3.

### Estimated token ratio

~15:1 input:output. Micro-session; two edits.

### What was useful

- Single targeted grep on runner.py confirmed append behavior without reading the file.
- No exploration reads needed.

### Main token drains

1. **Ambient context load** — unavoidable; dwarfs actual work.
2. Nothing else notable at this scale.

### Concrete recommendations

None. Session too small to surface new patterns.

---

## Sparse Policy Ranker Refactor

**Session:** 2026-05-10. Refactored `policies.py` scoring into sparse feature extraction, config-adapted weights, and weighted feature scoring. 416/416 pass.

### Estimated token ratio

~6:1 input:output. The implementation was moderately sized, but read/test output was heavier than necessary.

### What was useful

- User prompt with required and conditional touchpoints — kept the edit surface limited to policy scoring and tests.
- `docs/notes/sim/policies.py.md` — earned its tokens; it captured config/cache gotchas and recent policy priorities.
- Targeted reads of `actions.py` and `state.py` field ranges — high value for feature extraction.
- Focused policy and LED tests before full suite — caught contract changes without broad simulation runs.

### Main token drains

1. **Full `test_policy_config.py` read (~530 lines)** — recurring waste; targeted greps plus smaller ranges around assertions would have been enough.
2. **Large `git diff` output** — useful for review, but too broad; a stat plus focused hunks around new APIs would have been cheaper.
3. **Full-suite warning output** — known warnings dominated output; should have used the documented `-W ignore::UserWarning` form after focused tests passed.

### Recurring mistakes

- **Repeated:** full-test-file-read pattern from the Manual Observation Logging session recurred. Even focused test files should be approached with greps for helpers/assertions first.

### Concrete recommendations

- For policy/test refactors, grep test helper names and expected reason labels before reading long test ranges.
- Use `python3 -m pytest mtg_sim/tests/ -q -W ignore::UserWarning` for final full-suite verification when warning contents are already known and unrelated.

---

## B01 Agent Scaffold

**Session:** 2026-05-13. Created `.agents/` directory scaffolding, config, schemas, skill placeholder. Pure file-creation; no simulator code touched.

### Estimated token ratio

~4:1 input:output.

### What was useful

- `workstream.md` and `B01_scaffold-agents.md` — essential; drove all tasks.
- `.gitignore`, `.codex/hooks.json` — small, needed for existence checks.

### Main token drains

1. **`AGENTS.md` full read (~800 tokens)** — required touchpoint per bucket spec, but only existence + first few lines were needed for a file-creation-only bucket. A `head -5` check would have sufficed.
2. **Bucket boilerplate** — "Report First", "Do-not-read", "Conditional touchpoints" sections are structural scaffolding re-read every session; rarely changes.
3. **`find` output** — minor; returned unrelated `.claude/` paths.

### Concrete recommendations

- For buckets whose task is only creating new files (not editing existing ones), `AGENTS.md` should be a conditional touchpoint (existence check only), not a required full read.
- Consider trimming bucket boilerplate sections (`Report First`, `Do-not-read`) — they're structural reminders that cost tokens every session. → **`docs/prompts/workstream_bucket_generator_prompt.md`** candidate.

---

## B02 Task Queue + Generator Fix

**Session:** 2026-05-13. Implemented `scripts/agents/task_queue.py` (load/save/upsert/status/run-metadata), 24 tests. Fixed bucket generator prompt: removed `## Report First` (duplicate of workstream protocol), added `## Do-not-read` omit-when-empty note, added `AGENTS.md` conditional-only rule for file-creation buckets.

### Estimated token ratio

~5:1 input:output. Two buckets in one session.

### What was useful

- `workstream.md` and both bucket files — essential.
- `mtg_sim/tests/` head reads — quick, confirmed test style.

### Main token drains

1. **`AGENTS.md` full read (B01)** — second occurrence; now fixed at generator level.
2. **Bucket boilerplate re-read** — second occurrence; now fixed (Report First removed, Do-not-read conditionalized).
3. **Workstream/bucket update overhead** — 4+ field edits across 2 files after each bucket; mechanical but unavoidable.

### Recurring mistakes

- `AGENTS.md` full read: appeared in B01 session, recurred here. Root cause was bucket authoring (planning session), not generator. Fixed inline in generator rules.
- Bucket boilerplate drain: appeared in B01 session, recurred. Fixed by removing `## Report First` from template.

### Concrete recommendations

- Both recurring patterns now fixed at source. No further action needed unless they reappear in future generated buckets.

---

## B03 Worktree Runner

**Session:** 2026-05-13. Built `scripts/agents/run_codex_task.py` and 16 tests. Require-in-ledger policy confirmed by user (no auto-import from handoffs).

### Estimated token ratio

~5:1 input:output.

### What was useful

- `task_queue.py` full read — essential; runner imports and reuses all helpers directly.
- `B03_worktree-runner-dry-run.md` — drove all tasks.
- `test_task_queue.py` first 50 lines — quick fixture pattern check, cheap.

### Main token drains

1. **Compact summary re-ingestion** — large prior-session context paid on first turn; unavoidable.
2. **Three debug cycles on `RUNS_DIR`/`_safe_name`** — two bugs (missing constant, unsanitized filename) caught only in test runs; could have been pre-empted by noting that `write_run_metadata` takes raw task_id.
3. **`## Report First` dead weight in B03 bucket** — section was removed from generator template but B03 pre-dates the fix; harmless but wasted read tokens.

### Concrete recommendations

- Add ContextNote for `task_queue.py`: `write_run_metadata` does not sanitize `task_id` — callers must apply `_safe_name()` before passing. → `docs/notes/scripts/agents/task_queue.py.md`
- After a generator template change, audit open bucket files for stale boilerplate. → minor note in generator Updates.

---

## B05 Apply Review Cleanup

**Session:** 2026-05-13. Created `apply_codex_patch.py`, `cleanup_codex_task.py`, and 25 tests. 72 total agents tests pass.

### Estimated token ratio

~4:1 input:output. Clean implementation session.

### What was useful

- `workstream.md` + `B05_apply-review-cleanup.md` — drove all tasks.
- `.agents/config.toml` — essential for policy constants.
- `task_queue.py` full read — essential; reused helpers directly.
- `run_codex_task.py` targeted greps — cheap, confirmed path/constant names.
- `test_run_codex_task.py` first 100 lines — fixture patterns reused directly.

### Main token drains

1. **`test_run_codex_task.py` first 100 lines** — could have grepped for `git_repo` fixture and `_task()` helper instead of reading 100 lines.
2. **Workstream/bucket update overhead** — 6+ edit/sed operations for progress fields; mechanical but unavoidable.
3. **Auto-loaded context baseline** — CLAUDE.md + rules; no waste within, just baseline cost.

### Recurring mistakes

None recurred from prior sessions.

### Concrete recommendations

- Add ContextNote for `apply_codex_patch.py`: `patch_path` comes from `run_meta["artifacts"]["patch_path"]`, not from task fields — run metadata must exist before calling `apply()`.
- Add ContextNote for `cleanup_codex_task.py`: `git worktree remove --force` only works on git-tracked worktrees; manually created dirs are silently skipped.

---

## B06 Claude Codex Instructions

**Session:** 2026-05-13. Short doc/instruction session — updated SKILL.md, created codex-implementer SKILL.md, updated AGENTS.md.

### Estimated token ratio

~3:1 input:output. Very short session, mostly instruction writing.

### What was useful

- `workstream.md` + `B06` bucket — essential.
- Script head reads (apply, cleanup) — confirmed no CLI; key discovery.
- `.agents/config.toml` — all keys needed for config table.

### Main token drains

1. **AGENTS.md full read** — only needed insertion point; grep for section headings would have sufficed. Recurs from B01.
2. **Conditional touchpoints in B06** — both evaluated, neither needed.
3. **Baseline auto-load** — unavoidable.

### Recurring mistakes

- AGENTS.md full read recurred (flagged in B01, never routed). Added "no CLI" gotcha to apply/cleanup ContextNotes.

### Concrete recommendations

- When inserting a new section into AGENTS.md, grep `^##` first — never read the full file just to find placement.

## B07 Docs Smoke Valid

- Token ratio ~8:1. Main work: created .agents/README.md, fixed 2 apply_codex_patch.py bugs, verified dry-run Route B end-to-end, updated how_to_use.md and workstream docs.
- Useful: workstream.md + B07 bucket (essential), config.toml (all knobs needed), apply script targeted reads (found real bug).
- Drain 1: docs/road.md over-read — used roadmap to find workstream path when `ls docs/workstreams/` would have been 1 command. Routed: added workstream-routing rule to CLAUDE.md.
- Drain 2: AGENTS.md read in two halves (~160 lines) — third recurrence of this pattern. Not routeable via rules (AGENTS.md isn't under a rules-triggered glob). Routed to CLAUDE.md instead (already done).
- Drain 3: exploratory ls/grep cascade at session start before settling on workstream directory.
- Concrete change: CLAUDE.md now says `ls docs/workstreams/` first for workstream tasks. apply_codex_patch.py ContextNote corrected (patch_path key) and extended (empty-patch gotcha).

## Reset Status CLI

- Token ratio ~5:1. Short focused session: added `--reset-status` flag to `run_codex_task.py` + 3 tests.
- Useful: targeted greps on task_queue.py + run_codex_task.py — found signature, imports, and main() structure without any full-file reads.
- Drain 1: ToolSearch for TaskList/TaskGet schemas — 2 extra round-trips per session for tools that are used every introspect.
- Drain 2: tail read of test file to find insertion point — grep for last `^def test` would have been lighter.
- Drain 3: baseline auto-load (unavoidable).
- No recurring mistakes. No routing changes needed.
