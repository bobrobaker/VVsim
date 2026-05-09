# Backlog Log

Issues and resolutions related to the task backlog system.

---

## 2026-05-07 — Tasks not persisting across sessions

**Symptom:** Tasks created via `TaskCreate` were not visible in new sessions (`TaskList` returned empty).

**Root cause:** `CLAUDE_CODE_TASK_LIST_ID` was not set in the shell environment. Without it, each Claude Code session creates tasks under a fresh UUID-based directory (e.g. `~/.claude/tasks/<uuid>/`), which is invisible to other sessions.

**Fix applied:**
1. Added `export CLAUDE_CODE_TASK_LIST_ID=vvsim-backlog` above the non-interactive guard in `~/.bashrc` so it is available to all shells (interactive and non-interactive).
2. Created `~/.claude/tasks/vvsim-backlog/` and seeded it with the existing lookahead task JSON recovered from the orphaned UUID directory.

**Verification:** New terminal tab with `echo $CLAUDE_CODE_TASK_LIST_ID` prints `vvsim-backlog`; `TaskList` now returns the shared backlog.
