# Human-managed todos

## Current architecture direction (agreed)

- `action_generator.py` owns generic scaffolding: iterate zones, enforce timing/stack rules, call behavior hooks.
- Each card behavior owns both action generation (when/what) and resolution (what happens).

## Long-term todos

- **Policy refining**: refactor policy to have weights in a text-editable config file. In manual mode, display what the policy system thinks of each choice. If the user picks a non-top action, prompt for why and log state/action/reason to a policy-adjustment log. Review the log with Claude to refine policy behavior.
- **Per-card file split**: explore feasibility of splitting card-specific code into per-card files so each card's full behavior (generation + resolution + tests) can be handed off cleanly.

## Next todo

- Context optimization refactor (in progress)
