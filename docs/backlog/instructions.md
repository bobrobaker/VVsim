For every [SUGGESTION] task, the description field must include:
- FILE: relative path(s) to relevant file(s)
- LINES: approximate line range or function/class name
- TRIGGER: one sentence on what pattern or issue was noticed
- GOAL: one sentence on what the ideal outcome looks like
- GREP: 1-2 search terms or ripgrep commands to relocate the relevant code
  e.g. `rg "functionName" --type ts` or `rg "TODO|FIXME" src/auth/`
- EFFORT: low / medium / high
- VALUE: low / medium / high

Keep the entire description under 120 words.
