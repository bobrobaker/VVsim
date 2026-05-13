# Filesystem Snapshot - 2026-05-12 20:09:45 PDT

Purpose: compact project file inventory for sharing with another LLM.

Scope: source, docs, tests, scripts, datasets, visible archived project files, and checked-in agent/tooling context found from the repository root. Excluded transient directories and generated artifacts include `.git/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, build outputs, and `*.pyc`.

Note: the worktree had pre-existing modified, deleted, and untracked files when this snapshot was created. This file is an inventory of files visible to the snapshot command, not a clean git tree report.

## Root

| Path | Description |
| --- | --- |
| `AGENTS.md` | Codex project instructions |
| `CLAUDE.md` | Claude project instructions |
| `card_library.csv` | Card data library |
| `claude-backlog.py` | Claude backlog helper |
| `vivi_chain_simulator_llm_prompt.md` | LLM simulator prompt |

## Agent Tooling

| Path | Description |
| --- | --- |
| `.claude/settings.json` | Claude local settings |
| `.claude/commands/introspect.md` | Claude introspection command |
| `.claude/rules/sim-notes.md` | Claude sim note rules |
| `.claude/rules/tests.md` | Claude test rules |
| `.codex/hooks.json` | Codex hook config |

## Main Package

| Path | Description |
| --- | --- |
| `mtg_sim/__init__.py` | Package marker |
| `mtg_sim/config/__init__.py` | Config package marker |
| `mtg_sim/config/policy.toml` | Policy scoring config |
| `mtg_sim/sim/AGENTS.md` | Sim-specific instructions |
| `mtg_sim/sim/__init__.py` | Sim package marker |
| `mtg_sim/sim/action_generator.py` | Legal action scaffolding |
| `mtg_sim/sim/actions.py` | Action/cost/effect types |
| `mtg_sim/sim/card_behaviors.py` | Card-specific behavior |
| `mtg_sim/sim/cards.py` | Card definitions/catalog |
| `mtg_sim/sim/mana.py` | Mana pool/payment logic |
| `mtg_sim/sim/metrics.py` | Simulation metrics |
| `mtg_sim/sim/observations.py` | Manual observation data |
| `mtg_sim/sim/policies.py` | Greedy policy scoring |
| `mtg_sim/sim/resolver.py` | Action resolution |
| `mtg_sim/sim/runner.py` | Simulation main loop |
| `mtg_sim/sim/stack.py` | Stack object model |
| `mtg_sim/sim/state.py` | Game state model |
| `mtg_sim/sim/trace.py` | Trace/log formatting |

## Scripts And Outputs

| Path | Description |
| --- | --- |
| `mtg_sim/scripts/__init__.py` | Scripts package marker |
| `mtg_sim/scripts/inspect_trace.py` | Trace inspection CLI |
| `mtg_sim/scripts/plot_win_by_mana.py` | Mana plot script |
| `mtg_sim/scripts/plot_win_by_spells.py` | Spell-count plot script |
| `mtg_sim/scripts/run_monte_carlo.py` | Monte Carlo CLI |
| `mtg_sim/scripts/run_single.py` | Single-run CLI |
| `mtg_sim/scripts/datasets/20260512_1211_win_by_spells.csv` | Spell plot data |
| `mtg_sim/scripts/datasets/20260512_1211_win_by_spells.png` | Spell plot image |
| `mtg_sim/scripts/datasets/20260512_1211_win_by_spells.svg` | Spell plot vector |
| `mtg_sim/scripts/datasets/20260512_1219_win_by_mana.csv` | Mana plot data |
| `mtg_sim/scripts/datasets/20260512_1219_win_by_mana.svg` | Mana plot vector |
| `mtg_sim/scripts/datasets/20260512_1237_win_by_spells.csv` | Spell plot data |
| `mtg_sim/scripts/datasets/20260512_1237_win_by_spells.png` | Spell plot image |
| `mtg_sim/scripts/datasets/20260512_1237_win_by_spells.svg` | Spell plot vector |
| `mtg_sim/scripts/logs/manual_observations.jsonl` | Manual observation log |
| `mtg_sim/scripts/logs/manual_observations_old.jsonl` | Old observation log |
| `mtg_sim/scripts/logs/policy_adjustments.jsonl` | Policy adjustment log |
| `mtg_sim/scripts/logs/policy_adjustments_old.jsonl` | Old policy log |
| `mtg_sim/scripts/logs/policy_adjustments_root_old.jsonl` | Moved root policy log |

## Tests

| Path | Description |
| --- | --- |
| `mtg_sim/tests/AGENTS.md` | Test-specific instructions |
| `mtg_sim/tests/__init__.py` | Tests package marker |
| `mtg_sim/tests/conftest.py` | Pytest fixtures/helpers |
| `mtg_sim/tests/test_basic_brick.py` | Basic brick tests |
| `mtg_sim/tests/test_blazing_shoal.py` | Blazing Shoal tests |
| `mtg_sim/tests/test_cast_noncreature.py` | Noncreature cast tests |
| `mtg_sim/tests/test_counterspells.py` | Counterspell tests |
| `mtg_sim/tests/test_draw_cast_permission_engines.py` | Permission engine tests |
| `mtg_sim/tests/test_extra_turn_win.py` | Extra-turn win tests |
| `mtg_sim/tests/test_fetchlands.py` | Fetchland tests |
| `mtg_sim/tests/test_initial_draw.py` | Opening draw tests |
| `mtg_sim/tests/test_led_preempt.py` | LED preempt tests |
| `mtg_sim/tests/test_manual_policy_feedback.py` | Manual feedback tests |
| `mtg_sim/tests/test_mana_payment.py` | Mana payment tests |
| `mtg_sim/tests/test_mdfc_lands.py` | MDFC land tests |
| `mtg_sim/tests/test_misc_spells.py` | Misc spell tests |
| `mtg_sim/tests/test_nonland_mana_sources.py` | Nonland mana tests |
| `mtg_sim/tests/test_noop_permanents.py` | No-op permanent tests |
| `mtg_sim/tests/test_other_lands.py` | Other land tests |
| `mtg_sim/tests/test_policy_config.py` | Policy config tests |
| `mtg_sim/tests/test_runner_manual_display.py` | Manual display tests |
| `mtg_sim/tests/test_split_card.py` | Split card tests |
| `mtg_sim/tests/test_timing_rules.py` | Timing rule tests |
| `mtg_sim/tests/test_tutors.py` | Tutor tests |

## Documentation

| Path | Description |
| --- | --- |
| `docs/README.md` | Docs overview |
| `docs/road.md` | Project roadmap |
| `docs/todo.md` | Project todo list |
| `docs/backlog/instructions.md` | Backlog instructions |
| `docs/logs/backlog_log.md` | Backlog activity log |
| `docs/logs/introspect_log.md` | Introspection log |
| `docs/logs/introspect_notes.md` | Introspection notes |
| `docs/notes/README.md` | ContextNotes overview |
| `docs/notes/sim/action_generator.py.md` | Action generator notes |
| `docs/notes/sim/card_behaviors.py.md` | Card behavior notes |
| `docs/notes/sim/mana.py.md` | Mana module notes |
| `docs/notes/sim/policies.py.md` | Policy module notes |
| `docs/notes/sim/resolver.py.md` | Resolver notes |
| `docs/notes/sim/runner.py.md` | Runner notes |
| `docs/notes/sim/state.py.md` | State model notes |
| `docs/notes/tests/test_counterspells.py.md` | Counterspell test notes |
| `docs/notes/tests/test_misc_spells.py.md` | Misc spell test notes |
| `docs/notes/tests/test_nonland_mana_sources.py.md` | Nonland mana test notes |
| `docs/notes/tests/test_other_lands.py.md` | Other lands test notes |
| `docs/planning/context_optimization_refactor.prompt.md` | Context refactor prompt |
| `docs/prompts/active/manual_observation_logging.prompt.md` | Active logging prompt |
| `docs/prompts/active/token_introspection.prompt.md` | Active introspection prompt |
| `docs/prompts/archive/context_refactor.md` | Archived context refactor |
| `docs/prompts/archive/old/RefineMana.md` | Old mana prompt |
| `docs/prompts/archive/old/counterspells_instructions.txt` | Old counterspell prompt |
| `docs/prompts/archive/old/draw_cast_permission_engines_claude_prompt_concise.txt` | Old permission prompt |
| `docs/prompts/archive/old/fetchlands_claude_prompt_concise.txt` | Old fetchland prompt |
| `docs/prompts/archive/old/generic_noop_permanents_claude_prompt_concise.txt` | Old noop prompt |
| `docs/prompts/archive/old/misc_spells_claude_prompt_concise.txt` | Old misc prompt |
| `docs/prompts/archive/old/nonland_mana_sources_claude_prompt_concise.txt` | Old mana-source prompt |
| `docs/prompts/prebaker.md` | Prebaker prompt |
| `docs/samples/sample_manual_decision_snapshot.json` | Manual snapshot sample |
| `docs/samples/sample_state_snapshot_v2.json` | State snapshot sample |
| `docs/specs/card_specifics.md` | Card behavior spec |
| `docs/workstreams/card_specific.md` | Card workstream guide |

## Archived Visible Files

| Path | Description |
| --- | --- |
| `Claude-do-not-read-oudated/CLAUDE.md` | Archived Claude instructions |
| `Claude-do-not-read-oudated/Human_TODO.md` | Archived human todos |
| `Claude-do-not-read-oudated/mtg_sim_card_data_v1.csv` | Archived card data |
| `Claude-do-not-read-oudated/mtg_sim_tests.zip` | Archived test bundle |
| `Claude-do-not-read-oudated/old- CLAUDE.md` | Older Claude instructions |
| `Claude-do-not-read-oudated/testdecklist.txt` | Archived decklist |
