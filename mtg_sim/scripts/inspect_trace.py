#!/usr/bin/env python3
"""Re-run with a specific seed and show detailed trace. Useful for debugging."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run
from mtg_sim.sim.trace import format_trace

DATA_DIR = Path(__file__).parent.parent.parent
DEFAULT_LIBRARY = DATA_DIR / "card_library.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("seed", type=int)
    parser.add_argument("--mana-u", type=int, default=1)
    parser.add_argument("--mana-r", type=int, default=0)
    parser.add_argument("--mana-c", type=int, default=0)
    parser.add_argument("--curiosity-count", type=int, default=1)
    parser.add_argument("--deck-ids", nargs="*", type=int, default=None,
                        help="Card IDs for active deck (default: IDs 2-100)")
    args = parser.parse_args()

    load_card_library(str(DEFAULT_LIBRARY))
    active_deck = build_active_deck(args.deck_ids)

    cfg = RunConfig(
        seed=args.seed,
        starting_hand=[],
        starting_floating_mana=ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c),
        curiosity_effect_count=args.curiosity_count,
    )

    result = simulate_run(cfg, active_deck)
    print(format_trace(result, show_full=True))


if __name__ == "__main__":
    main()
