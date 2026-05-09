# Human-managed todos

## Current architecture direction (agreed)

- `action_generator.py` owns generic scaffolding: iterate zones, enforce timing/stack rules, call behavior hooks.
- Each card behavior owns both action generation (when/what) and resolution (what happens).

## Long-term todos

- **Policy refining**: refactor policy to have weights in a text-editable config file. In manual mode, display what the policy system thinks of each choice. If the user picks a non-top action, prompt for why and log state/action/reason to a policy-adjustment log. Review the log with Claude to refine policy behavior.
- **Policy sophistication**: current policy uses heuristic scoring per action in isolation; a smarter approach would look ahead (e.g. "if I cast this, what options open up?") or model a simple value function over GameState (mana available, spells castable, distance to win). Key known gaps: (a) EXILE_FOR_MANA penalty doesn't factor in how scarce the exiled card is vs. alternatives; (b) no lookahead to distinguish "this free spell blocks a 3-card chain" vs. "this free spell leads nowhere"; (c) color-of-mana sensitivity is heuristic, not modelled precisely.
- **Per-card file split**: explore feasibility of splitting card-specific code into per-card files so each card's full behavior (generation + resolution + tests) can be handed off cleanly.

## Next todo

- Context optimization refactor (in progress)
