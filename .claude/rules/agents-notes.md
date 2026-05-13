---
globs:
  - "scripts/agents/**"
  - "tests/agents/**"
---

Before editing any file in `scripts/agents/` or `tests/agents/`, check whether a matching CompanionDoc exists under `docs/notes/<relative-path>.md`. If found, read it before editing. Use the Touchpoints section to avoid unnecessary full-file reads.

At the end of a session, for any source file you edited:
- Refresh Touchpoints if functions/classes moved.
- Prepend one bullet to Recent changes; keep only the last 2.
- Update Gotchas only when you discovered a non-obvious invariant.
- Keep the whole file under 20 lines.

For test files you edited, update Helpers and Setup pattern only. No Recent changes section. Keep the whole file under 15 lines.

If no CompanionDoc exists for a file you edited and you have a meaningful update to record (new Touchpoints, a non-obvious Gotcha, or a significant Recent change), ask the user for permission before creating one. Do not create one silently.
