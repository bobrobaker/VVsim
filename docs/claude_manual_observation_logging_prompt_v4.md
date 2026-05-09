# Claude Prompt: Manual Observation Logging

Goal for session: Improve manual observation logging.

## Phase 1 purpose

This is Phase 1 of the policy-improvement pipeline: observation logging.

Before building a policy trainer or changing policy architecture, we need better manual-mode logs because action iteration, action generation, and resolution may still be imperfect. The logging system should help identify:
- policy mistakes
- missing legal actions
- illegal/generated-when-wrong actions
- wrong resolution/state mutation behavior
- states that should be excluded from later policy training

Do not treat these logs as only policy-training data. They are also the first tool for validating and debugging the simulator’s action/reality model.

## Context

We want better manual-mode logging before policy-training work. The immediate goal is to collect structured manual-mode data with minimal architectural risk.

Current behavior:
- Manual mode can rank actions and write policy-adjustment JSONL when the user chooses a non-top-ranked action.
- Manual mode currently displays reason labels for actions.
- Snapshot/log helpers currently live in `runner.py`.
- Existing path plumbing uses `RunConfig`, e.g. `adjustment_log_path=args.adjustment_log`.

Desired behavior:
1. Add/manual-observation log path plumbing using the same style as existing `adjustment_log_path`.
2. Buffer every manual decision snapshot in memory during manual mode.
3. At manual session end, ask whether to save buffered decision snapshots.
4. Save normal manual-decision snapshots separately from policy-adjustment entries.
5. Add manual note commands.
6. Always save current full library order as card IDs in decision snapshots.
7. Remove reason labels from manual display entirely.

## Reference schemas

Use these examples as the target shape, not as exact mandatory field order:
- `sample_manual_decision_snapshot.json`
- `sample_state_snapshot_v2.json`

Keep the actual implementation concise. Preserve the main design:
- every manual decision snapshot is machine-readable
- `state.library_ids` is always saved
- policy-adjustment entries remain separate from manual-observation entries
- action-generation/resolution bug notes are not mixed into policy-adjustment logs
- bug-note snapshots are saved because they are useful for simulator debugging

## Log paths

Add a new manual-observation log path in the same style as the existing policy adjustment log path.

Expected shape:
- `RunConfig.manual_observation_log_path`
- CLI argument similar to `--adjustment-log`
- construction similar to `adjustment_log_path=args.adjustment_log`

Keep existing `adjustment_log_path` behavior separate and avoid breaking it.

## Manual display

Display action menu with:
- index
- policy score
- best marker or delta
- action description

Do not display reason labels.

Example:
```text
[ 0]  180.0  ★ BEST   Cast Gitaxian Probe
[ 1]   90.0  Δ-90.0   Tap Mox Opal for {R}
```

## Manual commands

Add commands alongside numeric action choice:

- `n` / `note`: add general observation note; continue choosing
- `m` / `missing`: log expected missing action text + note; continue choosing
- `i` / `illegal`: log action index that should not exist + note; continue choosing
- `r` / `resolution`: log that the previous action/resolution seemed wrong + note; continue choosing if possible
- `q`: quit/brick as current behavior, but still allow normal end-of-session save confirmation

## Policy-training cleanliness

Use a `policy_trainable` field on saved manual-observation entries to mark whether that decision should be used later as policy-training data.

Bug-note handling:
- `missing`: action list is incomplete; mark the current decision snapshot `policy_trainable: false`.
- `illegal`: action list contains a bad action; mark the current decision snapshot `policy_trainable: false`.
- `resolution`: state may already be corrupted by a prior action; mark the current and later decision snapshots in the same session `policy_trainable: false` unless there is an obvious safe boundary.
- `note`: policy-trainable by default unless the user says the state/action list/resolution is wrong.

Do not discard bug-note snapshots. Save them as manual observations because they are useful for action-generator/resolution debugging. Just mark them out of policy training.

## Library IDs

Save current `library_ids` directly in every decision snapshot. Use card IDs for compactness. Include names where useful for readability, but `library_ids` is the required durable field.

## Near-term architecture

It is acceptable to keep the first implementation mostly in `runner.py` if that is the smallest safe change.

However, design helper boundaries so a near-future session can move reusable pieces into `mtg_sim/sim/observations.py`, likely:
- `snapshot_state(...)`
- `snapshot_action(...)`
- `snapshot_scored_action(...)`
- `append_jsonl(...)`
- `build_manual_decision_entry(...)`
- `build_policy_override_entry(...)`
- `build_manual_note_entry(...)`

Runner should orchestrate user input and sim flow. Snapshot/log schema construction should be isolated enough to extract later.

## Session-end save

If buffered decision snapshots exist:
- print a brief summary: decision count, note count, bug-note count, policy-trainable count
- ask whether to save
- if yes, append entries as JSONL
- if no, discard
- do not write every decision snapshot immediately

If the current manual-mode function return shape makes buffering awkward, choose the smallest safe interface change. Avoid global mutable state if practical.

## Required touchpoints

- `mtg_sim/sim/runner.py`
  - Main implementation surface for manual mode, buffering, save confirmation, and `RunConfig` field.
- CLI script that builds `RunConfig`
  - Add the manual-observation log argument using the existing adjustment-log pattern.
- `mtg_sim/sim/cards.py`
  - Use existing card ID/name lookup; add tiny helper only if needed.
- `mtg_sim/sim/state.py`
  - Read state fields needed for snapshots.
- Existing manual-mode/policy logging tests
  - Update only as needed.

## Conditional touchpoints

- `mtg_sim/sim/policies.py`
  - Only if needed to understand `rank_actions` / scored action shape.
- `mtg_sim/sim/stack.py`
  - Only if stack snapshot fields need explicit serialization.

## Avoid

- Do not read full `card_behaviors.py`.
- Do not refactor action generation.
- Do not refactor resolver.
- Do not implement trainer/autodebugger/sparse-ranker work.

Only edit after the implementation path is clear.
