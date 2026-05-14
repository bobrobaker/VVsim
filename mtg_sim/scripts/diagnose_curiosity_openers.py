#!/usr/bin/env python3
"""Diagnose which two-card openers can put a Curiosity trigger on stack.

This is an exploratory helper, not a regression test.  For each card X in the
default active deck except Ragavan, it starts with X + Ragavan in hand, Vivi and
a tapped Volcanic Island on the battlefield, a Curiosity effect active, no land
drop available, and no initial Curiosity draw.  It then resolves each legal
one-step action sourced from X and reports whether any action creates a
Curiosity draw trigger.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import warnings
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.actions import CAST_SPELL
from mtg_sim.sim.cards import build_active_deck, load_card_library
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.resolver import resolve_action
from mtg_sim.sim.runner import RunConfig, _build_initial_state

DATA_DIR = Path(__file__).parent.parent.parent
DEFAULT_LIBRARY = DATA_DIR / "card_library.csv"
RAGAVAN = "Ragavan, Nimble Pilferer"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report which default-deck cards can one-step trigger Curiosity."
    )
    parser.add_argument("--mana-u", type=int, default=0, help="Starting U mana")
    parser.add_argument("--mana-r", type=int, default=0, help="Starting R mana")
    parser.add_argument("--mana-c", type=int, default=0, help="Starting colorless mana")
    parser.add_argument("--seed", type=int, default=1, help="Seed for deterministic library order")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a text table",
    )
    return parser.parse_args()


def _build_state(card_name: str, active_deck: list[str], args: argparse.Namespace):
    config = RunConfig(
        seed=args.seed,
        starting_hand=[card_name, RAGAVAN],
        starting_floating_mana=ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c),
        curiosity_effect_count=1,
        starting_battlefield=["Volcanic Island"],
        starting_battlefield_tapped=["Volcanic Island"],
        land_play_available=False,
    )
    return _build_initial_state(config, active_deck, Random(args.seed))


def _diagnose_card(card_name: str, active_deck: list[str], args: argparse.Namespace) -> dict:
    try:
        state = _build_state(card_name, active_deck, args)
    except AssertionError as exc:
        return {
            "card": card_name,
            "status": "setup_error",
            "trigger": False,
            "trigger_actions": [],
            "legal_x_actions": [],
            "error": str(exc),
        }

    actions = [action for action in generate_actions(state) if action.source_card == card_name]
    trigger_actions = []

    for action in actions:
        if action.action_type != CAST_SPELL:
            continue
        trial_state = copy.deepcopy(state)
        before = sum(1 for obj in trial_state.stack if obj.is_draw_trigger)
        resolve_action(trial_state, copy.deepcopy(action))
        after = sum(1 for obj in trial_state.stack if obj.is_draw_trigger)
        if after > before:
            trigger_actions.append(action.description)

    return {
        "card": card_name,
        "status": "triggers" if trigger_actions else "no_trigger",
        "trigger": bool(trigger_actions),
        "trigger_actions": trigger_actions,
        "legal_x_actions": [action.description for action in actions],
        "error": "",
    }


def _checksum(results: list[dict], mana: dict) -> str:
    payload = {
        "mana": mana,
        "results": [
            {
                "card": result["card"],
                "status": result["status"],
                "trigger_actions": result["trigger_actions"],
                "legal_x_actions": result["legal_x_actions"],
                "error": result["error"],
            }
            for result in results
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _print_text(results: list[dict], checksum: str, mana: dict) -> None:
    print(f"Mana: U={mana['U']} R={mana['R']} C={mana['C']}")
    print(f"Checksum: {checksum}")
    print()
    print(f"{'Status':<12} Card")
    print(f"{'-' * 12} {'-' * 60}")
    for result in results:
        print(f"{result['status']:<12} {result['card']}")
        for description in result["trigger_actions"]:
            print(f"{'':<12} -> {description}")
        if result["status"] == "setup_error":
            print(f"{'':<12} !! {result['error']}")


def main() -> None:
    args = _parse_args()
    load_card_library(str(DEFAULT_LIBRARY))
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Active deck contains cards with no registered behavior.*",
            category=UserWarning,
        )
        active_deck = build_active_deck()
    cards_to_check = [card_name for card_name in active_deck if card_name != RAGAVAN]

    results = [_diagnose_card(card_name, active_deck, args) for card_name in cards_to_check]
    mana = {"U": args.mana_u, "R": args.mana_r, "C": args.mana_c}
    checksum = _checksum(results, mana)

    if args.json:
        print(json.dumps({"mana": mana, "checksum": checksum, "results": results}, indent=2))
    else:
        _print_text(results, checksum, mana)


if __name__ == "__main__":
    main()
