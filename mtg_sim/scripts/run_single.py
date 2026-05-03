#!/usr/bin/env python3
"""Run a single simulation and print the trace."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.cards import load_cards, load_decklist
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run
from mtg_sim.sim.trace import format_trace

DATA_DIR = Path(__file__).parent.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single Vivi chain simulation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hand", nargs="*", default=[], help="Starting hand card names")
    parser.add_argument("--mana-u", type=int, default=1, help="Starting U mana")
    parser.add_argument("--mana-r", type=int, default=0, help="Starting R mana")
    parser.add_argument("--mana-c", type=int, default=0, help="Starting colorless mana")
    parser.add_argument("--curiosity-count", type=int, default=1)
    parser.add_argument("--short", action="store_true", help="Print summary only")
    parser.add_argument(
        "--csv", default=str(DATA_DIR / "mtg_sim_card_data_v1.csv")
    )
    parser.add_argument(
        "--decklist", default=str(DATA_DIR / "testdecklist.txt")
    )
    args = parser.parse_args()

    card_db = load_cards(args.csv)
    all_cards = load_decklist(args.decklist)

    # Validate hand
    for c in args.hand:
        if c not in card_db:
            print(f"WARNING: '{c}' not found in card database", file=sys.stderr)

    config = RunConfig(
        seed=args.seed,
        starting_hand=args.hand,
        starting_floating_mana=ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c),
        curiosity_effect_count=args.curiosity_count,
        csv_path=args.csv,
        decklist_path=args.decklist,
    )

    result = simulate_run(config, all_cards)
    print(format_trace(result, show_full=not args.short))


if __name__ == "__main__":
    main()
