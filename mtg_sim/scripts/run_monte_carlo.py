#!/usr/bin/env python3
"""Run many simulations and report aggregate metrics."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.cards import load_cards, load_decklist
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run
from mtg_sim.sim.metrics import aggregate, format_metrics

DATA_DIR = Path(__file__).parent.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Monte Carlo simulation of Vivi chain")
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0, help="Base seed (each run gets seed+i)")
    parser.add_argument("--mana-u", type=int, default=1)
    parser.add_argument("--mana-r", type=int, default=0)
    parser.add_argument("--mana-c", type=int, default=0)
    parser.add_argument("--curiosity-count", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1, help="Parallel workers")
    parser.add_argument(
        "--csv", default=str(DATA_DIR / "mtg_sim_card_data_v1.csv")
    )
    parser.add_argument(
        "--decklist", default=str(DATA_DIR / "testdecklist.txt")
    )
    args = parser.parse_args()

    card_db = load_cards(args.csv)
    all_cards = load_decklist(args.decklist)

    base_config = RunConfig(
        seed=0,
        starting_hand=[],
        starting_floating_mana=ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c),
        curiosity_effect_count=args.curiosity_count,
        csv_path=args.csv,
        decklist_path=args.decklist,
    )

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
                                  [all_cards] * args.runs))
    else:
        results = []
        for i in range(args.runs):
            cfg = RunConfig(
                seed=args.seed + i,
                starting_hand=[],
                starting_floating_mana=ManaPool(
                    U=args.mana_u, R=args.mana_r, C=args.mana_c
                ),
                curiosity_effect_count=args.curiosity_count,
            )
            results.append(simulate_run(cfg, all_cards))
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
