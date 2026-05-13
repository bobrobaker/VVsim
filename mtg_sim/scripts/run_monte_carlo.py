#!/usr/bin/env python3
"""Run many simulations and report aggregate metrics."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run
from mtg_sim.sim.metrics import aggregate, format_metrics

DATA_DIR = Path(__file__).parent.parent.parent
DEFAULT_LIBRARY = DATA_DIR / "card_library.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Monte Carlo simulation of Vivi chain")
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1, help="Base seed (each run gets seed+i)")
    parser.add_argument("--mana-u", type=int, default=1)
    parser.add_argument("--mana-r", type=int, default=0)
    parser.add_argument("--mana-c", type=int, default=0)
    parser.add_argument("--curiosity-count", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1, help="Parallel workers")
    parser.add_argument("--deck-ids", nargs="*", type=int, default=None,
                        help="Card IDs for active deck (default: IDs 2-100)")
    args = parser.parse_args()

    load_card_library(str(DEFAULT_LIBRARY))
    active_deck = build_active_deck(args.deck_ids)

    base_mana = ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c)

    print(f"Running {args.runs} simulations... ", end="", flush=True)

    if args.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        configs = [RunConfig(
            seed=args.seed + i,
            starting_hand=[],
            starting_floating_mana=ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c),
            curiosity_effect_count=args.curiosity_count,
        ) for i in range(args.runs)]
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            results = list(ex.map(_run_one, configs,
                                  [active_deck] * args.runs))
    else:
        results = []
        for i in range(args.runs):
            cfg = RunConfig(
                seed=args.seed + i,
                starting_hand=[],
                starting_floating_mana=base_mana,
                curiosity_effect_count=args.curiosity_count,
            )
            results.append(simulate_run(cfg, active_deck))
            if (i + 1) % 100 == 0:
                print(f"{i+1}...", end="", flush=True)

    print(" done.")
    m = aggregate(results)
    print(format_metrics(m))


def _run_one(args):
    cfg, cards = args
    return simulate_run(cfg, cards)


if __name__ == "__main__":
    main()
