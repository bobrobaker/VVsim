#!/usr/bin/env python3
"""Run a single simulation and print the trace."""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run
from mtg_sim.sim.trace import format_trace

DATA_DIR = Path(__file__).parent.parent.parent
DEFAULT_LIBRARY = DATA_DIR / "card_library.csv"
DEFAULT_OBSERVATION_LOG = Path(__file__).parent / "logs" / "manual_observations.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single Vivi chain simulation")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed (default: random)")
    parser.add_argument("--hand", nargs="*", default=[], help="Starting hand card names")
    parser.add_argument("--mana-u", type=int, default=0, help="Starting U mana")
    parser.add_argument("--mana-r", type=int, default=1, help="Starting R mana")
    parser.add_argument("--mana-c", type=int, default=0, help="Starting colorless mana")
    parser.add_argument("--curiosity-count", type=int, default=1)
    parser.add_argument("--short", action="store_true", help="Print summary only")
    parser.add_argument("--manual", action="store_true",
                        help="Interactive mode: choose each action manually")
    parser.add_argument("--no-opponent-island", action="store_true",
                        help="Assume opponent does NOT control an island (disables Mogg Salvage free cost)")
    parser.add_argument("--policy-config", type=Path, default=None,
                        help="Path to policy TOML config (default: mtg_sim/config/policy.toml)")
    parser.add_argument("--adjustment-log", type=Path, default=None,
                        help="Path for policy adjustment JSONL log (default: logs/policy_adjustments.jsonl)")
    parser.add_argument("--manual-observation-log", type=Path, default=None,
                        help="Path for manual observation JSONL log (saved at session end)")
    parser.add_argument("--deck-ids", nargs="*", type=int, default=None,
                        help="Card IDs for active deck (default: IDs 2-100)")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else random.randrange(2**32)

    load_card_library(str(DEFAULT_LIBRARY))
    active_deck = build_active_deck(args.deck_ids)

    for c in args.hand:
        if c not in {name for name in active_deck}:
            print(f"WARNING: '{c}' not in active deck", file=sys.stderr)

    config = RunConfig(
        seed=seed,
        starting_hand=args.hand,
        starting_floating_mana=ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c),
        curiosity_effect_count=args.curiosity_count,
        manual_mode=args.manual,
        opponent_controls_island=not args.no_opponent_island,
        policy_config_path=args.policy_config,
        adjustment_log_path=args.adjustment_log or Path("logs/policy_adjustments.jsonl"),
        manual_observation_log_path=args.manual_observation_log or DEFAULT_OBSERVATION_LOG,
    )

    result = simulate_run(config, active_deck)
    print(f"Seed    : {seed}")
    print(format_trace(result, show_full=not args.short))


if __name__ == "__main__":
    main()
