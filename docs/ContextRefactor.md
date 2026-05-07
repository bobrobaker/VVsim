
## Context optimization refactor

### Prebaker (not implemented by claude- ignore)
Instruction file on how to prebake the generic tasks with the help of chatGPT. After a brief technical discussion and access to the code base, chatGPT (or a claude agent optimized for this activity) uses the reference docs/Prebaker.md to produce a prompt that is copy+pasted into a new session of claude.

### .claude/rules/ 
Move the Testing rules (from claude.md) to go into a glob-scoped rule file for all tests. 

#### CompanionDoc system 
 Task: Set up CompanionDocsystem for session notes

  Create a file-tree under docs/notes/ that mirrors mtg_sim/sim/ and mtg_sim/tests/. Each CompanionDoc file stores file-specific context that prevents Claude from re-deriving it each session.

  Loading mechanism: A .claude/rules/ glob-scoped rule file that fires when Claude touches files in the relevant directories. The rule instructs Claude to check for and read the CompanionDoc before editing, and to update source-file CompanionDoc at session end.

  To disable: Delete or rename .claude/rules/sim-notes.md. The docs/notes/ tree stays inert — nothing reads it without the rule file.

  CompanionDoc format — source files (≤20 lines):
  - ## Gotchas — non-obvious invariants (max 5 bullets)
  - ## Touchpoints — key function/class ranges to skip full-file reads
  - ## Recent changes (last 2 sessions) — rolling log, drop oldest when adding

  CompanionDoc format — test files (≤15 lines, no recent-changes section):
  - ## Helpers defined here — name + line range for each helper function
  - ## Setup pattern — ManaPool conventions, initial state gotchas (e.g. "initial BF always has Volcanic Island — check before asserting Mountain removal")

  Files to create:
  1. .claude/rules/sim-notes.md — glob mtg_sim/**, contains the read/update instructions below
  2. docs/notes/sim/ — initial CompanionDocs for: mana.py, card_behaviors.py, action_generator.py, resolver.py, state.py
  3. docs/notes/tests/ — initial CompanionDocs for the highest-traffic test files (grep for the largest ones by line count)

  Rule file instructions (to put inside .claude/rules/sim-notes.md):
  Before editing any file in mtg_sim/, check whether docs/notes/<relative-path>.md
  exists and read it if found. Use Touchpoints to skip full-file reads.

  At end of session, for any source file you edited:
  - Refresh Touchpoints if functions moved
  - Prepend one bullet to Recent changes, drop the oldest
  - Update Gotchas only if you discovered something non-obvious
  - Keep the whole file under 20 lines

  For test files you edited, update Helpers and Setup pattern only. No Recent changes section.

  Populate initial CompanionDocs from current file state: grep for function/class locations to fill Touchpoints; seed Gotchas from known issues in docs/introspecttokens.md and CLAUDE.md. Seed test CompanionDocs by scanning each test file for helper function definitions.


### Token_introspect
- should be a skill, so I can easily call it at the end of sessions I choose. invoke the skill via: "/introspect" 
- Take the token_introspect prompt at the head of the current docs/introspecttokens.md and keep it: move everything else to docs/introspect_notes.md
    - docs/introspect_log.md or similar append-only file to house the token counts and input/output ratio, 
    - docs/introspect_notes.md for the rest of the output 
- for each specific actionable takeaway: recommend how to implement changes to whichever best context management tools would be suited to that specific takeaway. Perhaps:
    - workstream instructions (if this session was derived from a workstream, and there are takeaways that may improve future buckets in that workstream)
    - basic_task_generator.md (if this session was derived from a prompt produced by the basic_task_generator)
    - rules (if its likely that syntatical triggering )
    - claude.md (general to the project and needing to be read in every session)
    - memory (general to the user and needing to be read in every session)
- confirm only routing changes (CLAUDE.md, rules, memory, workstream docs); write introspect_notes.md and introspect_log.md unconditionally without asking.
- after implementing: separately report how many [SUGGESTION] tasks were added this session (Step 7, not bundled with log write). If zero, what's the one thing you would have logged? Give a one-line summary of the highest-value item added if any.


### Claude.md changes:
- In general, make changes to claude.md so that it only contains information that is relevant to every session, is stable (shouldn't have known reasons for changing in between sessions), and must provide ways to cause claude to "hook" into the other files for context optimization
    - Pull the "Current Status / Next todo" block out of CLAUDE.md into docs/TODO.md or project memory
    - (already mentioned above but) Move testing rules to a glob-scoped rule (e.g., fires on mtg_sim/tests/**)
    - Architectural next-steps (things that constrain current decisions) → stay in CLAUDE.md under a small "Planned extensions" section
- Add the following line: When you notice an opportunity to refactor, improve architecture, reduce technical debt, or spot a better long-term approach — but it is not needed for the current task —say "→ create a TaskCreate with status `pending`, subject prefixed [SUGGESTION] and a structured description (see docs/backlog_instructions.md). Do not create a task for low-value style nits -- only medium or high value improvements.  
- Tasklist lives in .claude/tasks/ and human-managed todo will live in docs/todo.md (move current todo lines in claude.md to there)


### Other actions: 
- Upload and debug the script file claude-backlog.py that claude chat provided to introspect onto tasks. 
- Git-tracking the task folder: ~/.claude/tasks/ is outside your repo, so suggestions won't travel with the project. If portability matters, consider symlinking ~/.claude/tasks/myproject-backlog into your repo's .claude/ folder and gitignoring sensitive fields.
- Refactor docs/claude_bucket_instructions into "workstream_card_specific." Bucket: A scoped cluster of similar tasks sharing logic patterns and likely touchpoints, intended for one focused Claude session. Workstream: A broader multi-session effort composed of buckets, organized to preserve architectural continuity while limiting per-session context.
- add a hook to the TaskCreated to Print a formatted terminal notification: "→ [BACKLOG] logged: <subject>" and play a subtle sound.
- For persistent task backlog (survives /clear): add `export CLAUDE_CODE_TASK_LIST_ID=vvsim-backlog` to ~/.bashrc and `source ~/.bashrc`. Without this, TaskCreate uses a session UUID directory and tasks are orphaned on /clear.
- Add a hook so that terminal gives me a Desktop notification when Claude needs input, so you can switch to other tasks without watching the terminal
- Recommend me how to change .claude/memory to improve educational value of using claude in general. I'd like to: learn claude, AI-assisted development (not necessarily programming), SW dev and learn specifically python. (If it doesn't cost me signifcantly extra tokens to do so)  


