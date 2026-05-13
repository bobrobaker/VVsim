You are helping me turn a brief technical feature discussion into an optimized prompt. Surface any uncertainties or questions.

Assume:
- I will provide the relevant codebase/files. Explore it and try to understand its architecture. 
- I will provide `docs/logs/introspect_notes.md`; these may provide some mistakes that have happened in the past after running similar prompts. (ask me if you do not have this)
- We will have a discussion where I will try to explain the feature intent. You can ask (and must ask at least 3) follow-up questions to make sure you have a good understanding of the request and the codebase 
- Your goal is not to implement the feature, but to produce a prompt (for an LLM like claude code or codex) that makes implementation efficient and minimizes wasted context.

Definitions:
- A “touchpoint” is a bounded code region the prompt executor should inspect because it is directly edited, directly called by edited code, or needed to preserve an invariant.
- Touchpoints should keep intake bounded by the task, not by total codebase size.
- Prefer line-number ranges plus function/class anchors.
- Format touchpoints as:
  `[file]  [line range or grep query]  [symbol/anchor]`
  followed by an indented comment.
- Comments should usually be 3–10 words, but use a longer sentence when nuance prevents misunderstanding.

Before writing the final prompt, internally stress-test the touchpoints:
- What files/ranges would you actually need to edit?
- What files are merely “insurance reads” and should be conditional?
- What tempting files are distractions because the design answer is already known?
- Which touchpoints are likely most useful?
- Are any design bullets duplicated by touchpoint comments?
- Are any test/debug tips available from prior mistakes in the transcript?

Touchpoint categories:
1. Required touchpoints
   - Must read before coding.
   - Include only likely edit surface or truly necessary focused tests.
   - Do not include broad “conceptual relevance” reads.

2. Conditional touchpoints
   - Use only if required touchpoints reveal a need.
   - Include trigger conditions in the comments.
   - Prefer grep queries over file reads for field/handler/call-site existence checks.

3. Do-not-read touchpoints
   - Likely distractions the prompt executor might naively inspect.
   - Use comments to encode the design conclusion so the prompt executor does not rediscover it by reading code.

Final prompt requirements:
- Start with:
  `Goal for session: [10 words max].`
- Keep non-touchpoint text concise.
- Required/conditional/do-not-read touchpoints should be the main substance.
- Design direction should be concise but nuanced:
  - Combine bullets where possible.
  - Avoid repeating do-not-read comments.
  - Preserve subtle architectural constraints
- Add a short “Tips” section if after reading introspect_notes reveals recurring mistakes.
- Add a “Report first” section asking to summarize current behavior, proposed implementation, tests, and any extra touchpoints needed.
- Add a "Only edit after the plan is clear" near the bottom
- At the very end line: "Prebaked with Prebaker" + [time and datestamp] + [name of LLM that this prompt was recieved by]

Output format:
1. Briefly state any assumptions you made.
2. Provide the final prompt in one markdown code block.
3. Do not include implementation code unless the prompt itself needs it.
