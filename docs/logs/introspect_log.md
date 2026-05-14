# Introspect Log

Append-only token count and ratio log. One row per session.

| Date | Session | Ratio (in:out) | Notes |
|------|---------|---------------|-------|
| 2026-05-05 | Misc Spells Bucket | ~5:1 | |
| 2026-05-05 | Nonland Mana Sources | ~6:1 | |
| 2026-05-05 | Mana Payment Fix | ~5:1 | |
| 2026-05-07 | Exile Display Fix | ~3:1 | Main drain: Action() kwargs guessed wrong; test written twice. Skill restructured (Steps 4/7 split). |
| 2026-05-07 | Policy Config + Scoring Visibility | ~8:1 | Clean session; 380/380 pass, 1 minor test fix. Main drain: runner.py read 3× with overlap (recurring). New rule: process-level caches need _clear_cache() + conftest autouse. |
| 2026-05-07 | Policy Priorities Refactor | ~4:1 | Pitch penalty, free-mana-source bonus, win-cast mana, red preference. 390 pass. Main drain: wrong pip_r for Final Fortune caused 2 test failures; policy.toml discovered late. Added card-pip-count rule to tests.md. |
| 2026-05-08 | Manual Observation Logging | ~4:1 | Added obs buffer, n/m/i/r commands, session-end save, v2 state snapshot, RunConfig path, CLI arg. 400 pass. Main drain: full test file read when greps sufficed. Added two rules to tests.md. |
| 2026-05-08 | Default Obs Log Path | ~15:1 | Micro-session; closed backlog task #3. Single grep confirmed append behavior. No new rules. |
| 2026-05-13 | B01 Agent Scaffold | ~4:1 | Pure scaffolding session. Main drain: AGENTS.md full read unnecessary for file-creation-only bucket. Bucket boilerplate cost flagged as generator prompt candidate. No routing changes. |
| 2026-05-13 | B02 Task Queue + Generator Fix | ~5:1 | 24 tests pass. Fixed generator prompt: removed Report First (duplicate of workstream protocol), added Do-not-read omit-when-empty note, added AGENTS.md conditional-only rule. Both recurring drains now fixed at source. |
| 2026-05-13 | B03 Worktree Runner | ~5:1 | 16 tests pass (40 total). Main drain: write_run_metadata does not sanitize task_id — caused two debug cycles. Added ContextNote for task_queue.py. |
| 2026-05-13 | B04 Result Diff Patch | ~6:1 | 23 tests pass (47 total). 3 test-failure cycles (fake SHA silent-empty diff, stdout pollution, base_commit=""). Added agents-notes.md glob rule; CLAUDE.md now requires rule pairing for all CompanionDocs outside mtg_sim/. |
| 2026-05-13 | B05 Apply Review Cleanup | ~4:1 | 25 new tests (72 total). Clean session. Main drain: test fixture read (100 lines) when grep sufficed. No recurring mistakes. tomllib fallback for 3.10 handled proactively. |
| 2026-05-13 | B06 Codex Instructions | ~3:1 | Short doc session. apply/cleanup have no CLI (library-only) — added to ContextNotes. AGENTS.md full-read recurred from B01; not yet routed. |
| 2026-05-13 | B07 Docs Smoke Valid | ~8:1 | Dry-run flow complete. Fixed 2 apply bugs. AGENTS.md full-read routed to CLAUDE.md workstream-routing rule. ContextNote for apply_codex_patch.py updated with patch_path key and empty-patch gotchas. |
| 2026-05-13 | Route B Scout / Protocol Hardening | ~10:1 | 85 agents tests pass. Fixed codex exec -o contract, OpenAI strict schema (3 cycles), SKILL.md frontmatter, worktree-from-HEAD propagation. Scout: 99 cards, 26 castable. CompanionDoc updated with new gotchas. |
| 2026-05-13 | Reset Status CLI | ~5:1 | Added --reset-status flag + 3 tests. Clean session, no recurring mistakes, no routing changes. |
