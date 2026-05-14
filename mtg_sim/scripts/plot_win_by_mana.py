#!/usr/bin/env python3
"""Graph win rate by starting blue/red mana."""
from __future__ import annotations

import argparse
import csv
import html
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.cards import build_active_deck, load_card_library
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, RunResult, simulate_run

DATA_DIR = Path(__file__).parent.parent.parent
DEFAULT_LIBRARY = DATA_DIR / "card_library.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "datasets"


@dataclass(frozen=True)
class ManaWinRate:
    blue_mana: int
    red_mana: int
    runs: int
    wins: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.runs if self.runs else 0.0


@dataclass(frozen=True)
class SimulationTask:
    blue_mana: int
    red_mana: int
    config: RunConfig
    active_deck: list[str]


@dataclass(frozen=True)
class SimulationResult:
    blue_mana: int
    red_mana: int
    result: RunResult


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot win rate by starting blue/red mana"
    )
    parser.add_argument("--runs-per-cell", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1, help="Base seed")
    parser.add_argument("--min-mana", type=int, default=0)
    parser.add_argument("--max-mana", type=int, default=5)
    parser.add_argument("--mana-c", type=int, default=0)
    parser.add_argument("--curiosity-count", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1, help="Parallel workers")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output", type=Path, default=None,
                        help="SVG output path (default: timestamped win_by_mana SVG)")
    parser.add_argument("--csv-output", type=Path, default=None,
                        help="CSV output path (default: matching timestamped CSV)")
    parser.add_argument("--deck-ids", nargs="*", type=int, default=None,
                        help="Card IDs for active deck (default: IDs 2-100)")
    args = parser.parse_args()

    load_card_library(str(DEFAULT_LIBRARY))
    active_deck = build_active_deck(args.deck_ids)
    svg_output, csv_output = _output_paths(args)

    total_runs = _mana_value_count(args) ** 2 * args.runs_per_cell
    print(
        f"Running {total_runs} simulations "
        f"({args.runs_per_cell} per mana pair)... ",
        end="",
        flush=True,
    )
    results = run_simulations(args, active_deck)
    print(" done.")

    points = build_win_rate_grid(results, args.runs_per_cell)
    write_csv(points, csv_output)
    write_svg(points, svg_output, args.runs_per_cell)

    print(f"Wrote CSV: {csv_output}")
    print(f"Wrote SVG: {svg_output}")
    print_table(points)


def run_simulations(args: argparse.Namespace, active_deck: list[str]) -> list[SimulationResult]:
    tasks = list(_simulation_tasks(args, active_deck))
    if args.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            return list(ex.map(_run_one, tasks))

    results: list[SimulationResult] = []
    for i, task in enumerate(tasks):
        results.append(_run_one(task))
        if (i + 1) % 100 == 0:
            print(f"{i + 1}...", end="", flush=True)
    return results


def _simulation_tasks(
    args: argparse.Namespace,
    active_deck: list[str],
) -> list[SimulationTask]:
    tasks: list[SimulationTask] = []
    mana_values = range(args.min_mana, args.max_mana + 1)
    cell_index = 0
    for blue_mana in mana_values:
        for red_mana in mana_values:
            for run_index in range(args.runs_per_cell):
                seed = args.seed + cell_index * args.runs_per_cell + run_index
                config = RunConfig(
                    seed=seed,
                    starting_hand=[],
                    starting_floating_mana=ManaPool(
                        U=blue_mana,
                        R=red_mana,
                        C=args.mana_c,
                    ),
                    curiosity_effect_count=args.curiosity_count,
                )
                tasks.append(SimulationTask(blue_mana, red_mana, config, active_deck))
            cell_index += 1
    return tasks


def _run_one(task: SimulationTask) -> SimulationResult:
    return SimulationResult(
        blue_mana=task.blue_mana,
        red_mana=task.red_mana,
        result=simulate_run(task.config, task.active_deck),
    )


def build_win_rate_grid(
    results: list[SimulationResult],
    runs_per_cell: int,
) -> list[ManaWinRate]:
    by_pair: dict[tuple[int, int], int] = {}
    for result in results:
        key = (result.blue_mana, result.red_mana)
        by_pair[key] = by_pair.get(key, 0) + int(result.result.won)

    return [
        ManaWinRate(blue_mana=blue, red_mana=red, runs=runs_per_cell, wins=wins)
        for (blue, red), wins in sorted(by_pair.items())
    ]


def write_csv(points: list[ManaWinRate], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["blue_mana", "red_mana", "runs", "wins", "win_rate"])
        for point in points:
            writer.writerow([
                point.blue_mana,
                point.red_mana,
                point.runs,
                point.wins,
                f"{point.win_rate:.6f}",
            ])


def write_svg(points: list[ManaWinRate], path: Path, runs_per_cell: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    blue_values = sorted({point.blue_mana for point in points})
    red_values = sorted({point.red_mana for point in points})
    point_by_pair = {(point.blue_mana, point.red_mana): point for point in points}

    width = 820
    height = 680
    margin_left = 96
    margin_top = 76
    cell_size = 74
    gap = 8
    grid_width = len(red_values) * cell_size + (len(red_values) - 1) * gap
    grid_height = len(blue_values) * cell_size + (len(blue_values) - 1) * gap
    legend_x = margin_left + grid_width + 50
    legend_y = margin_top + 54
    title = f"Win Rate by Starting Mana ({runs_per_cell} runs per cell)"

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text { font-family: Arial, sans-serif; fill: #1f2933; }",
        ".title { font-size: 22px; font-weight: 700; }",
        ".axis-label { font-size: 15px; font-weight: 700; }",
        ".tick { font-size: 13px; fill: #52606d; }",
        ".cell-label { font-size: 16px; font-weight: 700; fill: #102a43; }",
        ".cell-sub { font-size: 11px; fill: #334e68; }",
        ".legend { font-size: 12px; fill: #52606d; }",
        "</style>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text class="title" x="{margin_left}" y="36">{html.escape(title)}</text>',
    ]

    for index, red_mana in enumerate(red_values):
        x = margin_left + index * (cell_size + gap) + cell_size / 2
        parts.append(f'<text class="tick" x="{x:.1f}" y="{margin_top - 16}" text-anchor="middle">{red_mana}</text>')
    for index, blue_mana in enumerate(reversed(blue_values)):
        y = margin_top + index * (cell_size + gap) + cell_size / 2
        parts.append(f'<text class="tick" x="{margin_left - 18}" y="{y + 5:.1f}" text-anchor="end">{blue_mana}</text>')

    for y_index, blue_mana in enumerate(reversed(blue_values)):
        for x_index, red_mana in enumerate(red_values):
            point = point_by_pair[(blue_mana, red_mana)]
            x = margin_left + x_index * (cell_size + gap)
            y = margin_top + y_index * (cell_size + gap)
            fill = _heat_color(point.win_rate)
            label = f"{point.win_rate:.0%}"
            detail = f"{point.wins}/{point.runs}"
            title_text = (
                f"U={point.blue_mana}, R={point.red_mana}: "
                f"{point.win_rate:.1%} ({point.wins}/{point.runs})"
            )
            parts.extend([
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="6" fill="{fill}">',
                f'<title>{html.escape(title_text)}</title>',
                "</rect>",
                f'<text class="cell-label" x="{x + cell_size / 2:.1f}" y="{y + 34:.1f}" text-anchor="middle">{label}</text>',
                f'<text class="cell-sub" x="{x + cell_size / 2:.1f}" y="{y + 52:.1f}" text-anchor="middle">{detail}</text>',
            ])

    parts.extend([
        f'<text class="axis-label" x="{margin_left + grid_width / 2:.1f}" y="{margin_top + grid_height + 48}" text-anchor="middle">Starting red mana</text>',
        f'<text class="axis-label" x="28" y="{margin_top + grid_height / 2:.1f}" text-anchor="middle" transform="rotate(-90 28 {margin_top + grid_height / 2:.1f})">Starting blue mana</text>',
        f'<text class="legend" x="{legend_x}" y="{legend_y - 18}">Win rate</text>',
    ])

    for index, pct in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
        y = legend_y + index * 42
        parts.append(f'<rect x="{legend_x}" y="{y}" width="28" height="28" rx="4" fill="{_heat_color(pct)}"/>')
        parts.append(f'<text class="legend" x="{legend_x + 40}" y="{y + 19}">{pct:.0%}</text>')

    parts.extend(["</svg>", ""])
    path.write_text("\n".join(parts))


def print_table(points: list[ManaWinRate]) -> None:
    blue_values = sorted({point.blue_mana for point in points}, reverse=True)
    red_values = sorted({point.red_mana for point in points})
    point_by_pair = {(point.blue_mana, point.red_mana): point for point in points}

    header = "Blue\\Red | " + " | ".join(f"{red:>4}" for red in red_values)
    print(header)
    print("-" * len(header))
    for blue_mana in blue_values:
        cells = [
            f"{point_by_pair[(blue_mana, red_mana)].win_rate:>4.0%}"
            for red_mana in red_values
        ]
        print(f"{blue_mana:>8} | " + " | ".join(cells))


def _output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = f"{timestamp}_win_by_mana"
    svg_output = args.output or args.output_dir / f"{base}.svg"
    csv_output = args.csv_output or svg_output.with_suffix(".csv")
    return svg_output, csv_output


def _mana_value_count(args: argparse.Namespace) -> int:
    return args.max_mana - args.min_mana + 1


def _heat_color(value: float) -> str:
    value = max(0.0, min(1.0, value))
    low = (239, 246, 255)
    high = (20, 184, 166)
    red = round(low[0] + (high[0] - low[0]) * value)
    green = round(low[1] + (high[1] - low[1]) * value)
    blue = round(low[2] + (high[2] - low[2]) * value)
    return f"rgb({red},{green},{blue})"


if __name__ == "__main__":
    main()
