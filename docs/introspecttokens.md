# Token Introspection Prompt

Audit this Claude Code session’s token use. Estimate input/output ratio, identify which prompts/docs/files were useful vs wasteful, name main token drains, and recommend concrete ways to reduce token use next session without losing correctness. Cite specific examples from this session where possible. Write out the result in docs/introspecttokens.md under a new header with a 2-4 word title that identifies this session

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

2. **`state.py` full orientation read (14-141).** Read ~130 lines to confirm that `_opponent_player_perm` didn’t exist. A single grep (`grep -n "_opponent"`) would have answered the same question in one tool call.

3. **`card_behaviors.py` registry read (1680-1730).** Read to check what was registered. Could have been a grep: `grep -n "Snapback\|Bauble\|Cave\|Boomerang"` which I eventually did anyway.

4. **Blazing Shoal test file read (full, 90 lines).** Needed only the helper pattern (~10 lines). Could have read offset=17, limit=15.

5. **Test debugging loop.** Three test runs were needed: initial run (11 failures), then after `ManaPool(generic=)` fix + `_drain_stack` introduction, then final clean run. The `ManaPool` kwargs error should have been caught by grep before writing the test file: `grep -n "ManaPool(" mtg_sim/tests/test_blazing_shoal.py` would have shown the `ManaPool()` / `ManaPool(U=1)` pattern in 5 seconds.

6. **Debug Python one-liner for Thunderclap.** Required after test failure because the sacrifice perm_id didn’t match the expected Mountain — a Volcanic Island was found first. Could have been anticipated: `_we_control_mountain` uses a set of dual-land names, and the initial state always has a Volcanic Island. Grep + quick read of `_MOUNTAIN_LANDS` before writing the test would have caught this.

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
