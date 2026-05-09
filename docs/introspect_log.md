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
