"""Serialization helpers for manual observation and policy feedback logs."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .actions import Action
from .cards import get_card
from .stack import StackObject
from .state import GameState, Permanent


def append_jsonl(path: Path, entry: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def snapshot_action(action: Action) -> dict:
    return {
        "action_type": action.action_type,
        "source_card": action.source_card,
        "source_card_id": _card_id(action.source_card),
        "description": action.description,
        "costs": _serialize_action_costs(action),
        "effects": _serialize_action_effects(action),
        "target": action.target,
        "alt_cost_type": action.alt_cost_type,
        "risk_level": action.risk_level,
    }


def snapshot_scored_action(scored_action: Any, index: int) -> dict:
    return {
        "index": index,
        "rank": scored_action.rank,
        "score": scored_action.score,
        "delta": scored_action.delta,
        **snapshot_action(scored_action.action),
    }


def build_manual_decision_entry(
    state: GameState,
    ranked: list,
    chosen_sa: Any,
    chosen_idx: int,
    step: int,
    seed: int | None,
    session_id: str | None,
    notes: list,
    policy_trainable: bool,
) -> dict:
    top_sa = ranked[0]
    return {
        "entry_type": "manual_decision_snapshot",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": session_id,
        "session_id": session_id,
        "seed": seed,
        "step": step,
        "policy_trainable": policy_trainable,
        "invalid_reason": None,
        "state": snapshot_state(state),
        "ranked_actions": [
            snapshot_scored_action(sa, i)
            for i, sa in enumerate(ranked)
        ],
        "policy_top_action": {
            "index": 0,
            "description": top_sa.action.description,
            "score": top_sa.score,
        },
        "chosen_action": {
            "index": chosen_idx,
            "rank": chosen_sa.rank,
            "score": chosen_sa.score,
            "delta": chosen_sa.delta,
            "description": chosen_sa.action.description,
        },
        "chosen_was_policy_top": chosen_sa.rank == 1,
        "manual_notes": notes,
    }


def build_policy_adjustment_entry(
    state: GameState,
    ranked: list,
    chosen_sa: Any,
    top_sa: Any,
    step: int,
    seed: int | None,
    session_id: str | None,
    reason: str,
) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": session_id,
        "session_id": session_id,
        "seed": seed,
        "step": step,
        "chosen_rank": chosen_sa.rank,
        "chosen_action": chosen_sa.action.description,
        "chosen_score": chosen_sa.score,
        "top_rank": 1,
        "top_action": top_sa.action.description,
        "top_score": top_sa.score,
        "score_delta": chosen_sa.delta,
        "user_reason": reason,
        "all_scored": [
            {
                "rank": sa.rank,
                "action": sa.action.description,
                "costs": _serialize_action_costs(sa.action),
                "effects": _serialize_action_effects(sa.action),
                "score": sa.score,
                "delta": sa.delta,
                "reasons": sa.reasons,
            }
            for sa in ranked
        ],
        "state_snapshot": snapshot_state(state),
    }


def snapshot_permanent(permanent: Permanent) -> dict:
    return {
        "card_name": permanent.card_name,
        "card_id": _card_id(permanent.card_name),
        "perm_id": permanent.perm_id,
        "tapped": permanent.tapped,
        "counters": dict(permanent.counters),
        "imprinted_card": permanent.imprinted_card,
        "attached_to": permanent.attached_to,
    }


def snapshot_stack_object(stack_object: StackObject) -> dict:
    return {
        "card_name": stack_object.card_name,
        "card_id": _card_id(stack_object.card_name),
        "stack_id": stack_object.stack_id,
        "targets": list(stack_object.targets),
        "target_names": list(stack_object.target_names),
        "x_value": stack_object.x_value,
        "alt_cost_used": stack_object.alt_cost_used,
        "is_draw_trigger": stack_object.is_draw_trigger,
        "draw_count": stack_object.draw_count,
    }


def snapshot_state(state: GameState) -> dict:
    return {
        "floating_mana": {
            "U": state.floating_mana.U,
            "R": state.floating_mana.R,
            "C": state.floating_mana.C,
            "ANY": state.floating_mana.ANY,
        },
        "hand": list(state.hand),
        "hand_ids": [_card_id(c) for c in state.hand],
        "library_ids": [_card_id(c) for c in state.library],
        "battlefield": [snapshot_permanent(p) for p in state.battlefield],
        "stack": [snapshot_stack_object(o) for o in state.stack],
        "graveyard": list(state.graveyard),
        "graveyard_ids": [_card_id(c) for c in state.graveyard],
        "exile": list(state.exile),
        "exile_ids": [_card_id(c) for c in state.exile],
        "pending_choices": [str(c) for c in state.pending_choices],
        "permissions": [str(p) for p in state.permissions],
        "pending_curiosity_draws": state.pending_curiosity_draws,
        "noncreature_spells_cast": state.noncreature_spells_cast,
        "total_cards_drawn": state.total_cards_drawn,
        "land_play_available": state.land_play_available,
        "vivi_available_as_creature_to_tap": state.vivi_available_as_creature_to_tap,
        "legendary_permanent_available": state.legendary_permanent_available,
        "virtue_of_courage_on_battlefield": state.virtue_of_courage_on_battlefield,
    }


def _serialize_action_costs(action: Action) -> dict:
    return asdict(action.costs)


def _serialize_action_effects(action: Action) -> dict:
    return asdict(action.effects)


def _card_id(name: str | None) -> int | None:
    if name is None:
        return None
    cd = get_card(name)
    return cd.card_id if cd else None
