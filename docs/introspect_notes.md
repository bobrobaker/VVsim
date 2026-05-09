# Introspection Notes

Qualitative findings from past sessions. Append new entries via `/introspect`.

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
