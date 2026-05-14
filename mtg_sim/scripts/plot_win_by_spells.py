#!/usr/bin/env python3
"""Graph eventual win rate by noncreature spells cast so far."""
from __future__ import annotations

import argparse
import csv
import html
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.cards import build_active_deck, load_card_library
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, RunResult, simulate_run

DATA_DIR = Path(__file__).parent.parent.parent
DEFAULT_LIBRARY = DATA_DIR / "card_library.csv"
DEFAULT_OUTPUT = Path("win_by_spells.svg")


@dataclass(frozen=True)
class WinRatePoint:
    spells_cast: int
    runs_reached: int
    wins_from_here: int
    win_rate: float


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot eventual win rate conditional on noncreature spells cast"
    )
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1, help="Base seed (each run gets seed+i)")
    parser.add_argument("--mana-u", type=int, default=1)
    parser.add_argument("--mana-r", type=int, default=0)
    parser.add_argument("--mana-c", type=int, default=0)
    parser.add_argument("--curiosity-count", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1, help="Parallel workers")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="SVG output path")
    parser.add_argument("--csv-output", type=Path, default=None,
                        help="CSV output path (default: output path with .csv suffix)")
    parser.add_argument("--deck-ids", nargs="*", type=int, default=None,
                        help="Card IDs for active deck (default: IDs 2-100)")
    args = parser.parse_args()

    load_card_library(str(DEFAULT_LIBRARY))
    active_deck = build_active_deck(args.deck_ids)

    print(f"Running {args.runs} simulations... ", end="", flush=True)
    results = run_simulations(args, active_deck)
    print(" done.")

    points = build_win_rate_points(results)
    csv_output = args.csv_output or args.output.with_suffix(".csv")
    write_csv(points, csv_output)
    write_svg(points, args.output, args.runs)

    print(f"Wrote CSV: {csv_output}")
    print(f"Wrote SVG: {args.output}")
    if points:
        print("Spell count | Reached | Win rate")
        for point in points:
            print(f"{point.spells_cast:>11} | {point.runs_reached:>7} | {point.win_rate:>7.1%}")


def run_simulations(args: argparse.Namespace, active_deck: list[str]) -> list[RunResult]:
    if args.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        configs = [_make_config(args, args.seed + i) for i in range(args.runs)]
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            return list(ex.map(_run_one, configs, [active_deck] * args.runs))

    results: list[RunResult] = []
    for i in range(args.runs):
        results.append(simulate_run(_make_config(args, args.seed + i), active_deck))
        if (i + 1) % 100 == 0:
            print(f"{i + 1}...", end="", flush=True)
    return results


def _make_config(args: argparse.Namespace, seed: int) -> RunConfig:
    return RunConfig(
        seed=seed,
        starting_hand=[],
        starting_floating_mana=ManaPool(U=args.mana_u, R=args.mana_r, C=args.mana_c),
        curiosity_effect_count=args.curiosity_count,
    )


def _run_one(config: RunConfig, active_deck: list[str]) -> RunResult:
    return simulate_run(config, active_deck)


def build_win_rate_points(results: list[RunResult]) -> list[WinRatePoint]:
    max_spells = max((r.noncreature_spells_cast for r in results), default=0)
    points: list[WinRatePoint] = []

    for spell_count in range(max_spells + 1):
        reached = [
            r for r in results
            if r.noncreature_spells_cast >= spell_count
        ]
        wins = sum(1 for r in reached if r.won)
        win_rate = wins / len(reached) if reached else 0.0
        points.append(WinRatePoint(
            spells_cast=spell_count,
            runs_reached=len(reached),
            wins_from_here=wins,
            win_rate=win_rate,
        ))

    return points


def write_csv(points: list[WinRatePoint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["spells_cast", "runs_reached", "wins_from_here", "win_rate"])
        for point in points:
            writer.writerow([
                point.spells_cast,
                point.runs_reached,
                point.wins_from_here,
                f"{point.win_rate:.6f}",
            ])


def write_svg(points: list[WinRatePoint], path: Path, total_runs: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    width = 900
    height = 560
    margin_left = 72
    margin_right = 28
    margin_top = 52
    margin_bottom = 72
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    max_spells = max((p.spells_cast for p in points), default=0)
    x_denominator = max(max_spells, 1)

    def x_pos(spells_cast: int) -> float:
        return margin_left + (spells_cast / x_denominator) * plot_width

    def y_pos(win_rate: float) -> float:
        return margin_top + (1.0 - win_rate) * plot_height

    polyline = " ".join(
        f"{x_pos(point.spells_cast):.1f},{y_pos(point.win_rate):.1f}"
        for point in points
    )

    x_ticks = _ticks(max_spells)
    y_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    title = f"Eventual Win Rate by Noncreature Spells Cast ({total_runs} runs)"

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text { font-family: Arial, sans-serif; fill: #1f2933; }",
        ".title { font-size: 22px; font-weight: 700; }",
        ".label { font-size: 14px; }",
        ".tick { font-size: 12px; fill: #52606d; }",
        ".grid { stroke: #d9e2ec; stroke-width: 1; }",
        ".axis { stroke: #334e68; stroke-width: 1.5; }",
        ".line { fill: none; stroke: #0b7285; stroke-width: 3; }",
        ".dot { fill: #0b7285; }",
        "</style>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text class="title" x="{margin_left}" y="32">{html.escape(title)}</text>',
    ]

    for tick in y_ticks:
        y = y_pos(tick)
        parts.append(f'<line class="grid" x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{margin_left - 12}" y="{y + 4:.1f}" text-anchor="end">{tick:.0%}</text>')

    for tick in x_ticks:
        x = x_pos(tick)
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="{margin_top}" x2="{x:.1f}" y2="{height - margin_bottom}"/>')
        parts.append(f'<text class="tick" x="{x:.1f}" y="{height - margin_bottom + 22}" text-anchor="middle">{tick}</text>')

    parts.extend([
        f'<line class="axis" x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}"/>',
        f'<line class="axis" x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}"/>',
        f'<polyline class="line" points="{polyline}"/>',
    ])

    for point in points:
        x = x_pos(point.spells_cast)
        y = y_pos(point.win_rate)
        label = (
            f"{point.spells_cast} spells: {point.win_rate:.1%} "
            f"({point.wins_from_here}/{point.runs_reached})"
        )
        parts.append(
            f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="3">'
            f'<title>{html.escape(label)}</title></circle>'
        )

    parts.extend([
        f'<text class="label" x="{margin_left + plot_width / 2:.1f}" y="{height - 22}" text-anchor="middle">Noncreature spells cast so far</text>',
        f'<text class="label" x="20" y="{margin_top + plot_height / 2:.1f}" text-anchor="middle" transform="rotate(-90 20 {margin_top + plot_height / 2:.1f})">Eventual win rate</text>',
        "</svg>",
        "",
    ])

    path.write_text("\n".join(parts))


def _ticks(max_value: int) -> list[int]:
    if max_value <= 10:
        return list(range(max_value + 1))

    step = 5
    if max_value > 50:
        step = 10
    ticks = list(range(0, max_value + 1, step))
    if ticks[-1] != max_value:
        ticks.append(max_value)
    return ticks


if __name__ == "__main__":
    main()
