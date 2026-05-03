"""Aggregate metrics across many simulation runs."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
import statistics
from .runner import RunResult
from .actions import (
    WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT,
    BRICK_NO_ACTIONS, BRICK_NO_USEFUL_ACTIONS, ERROR_INVALID_STATE,
)


@dataclass
class AggregateMetrics:
    total_runs: int = 0
    win_count: int = 0
    win_extra_turn_count: int = 0
    win_spell_count: int = 0
    brick_no_actions_count: int = 0
    brick_no_useful_count: int = 0
    error_count: int = 0

    spells_cast_list: list = field(default_factory=list)
    cards_drawn_list: list = field(default_factory=list)
    hand_size_list: list = field(default_factory=list)

    brick_reasons: Counter = field(default_factory=Counter)
    winning_cards: Counter = field(default_factory=Counter)
    stranded_cards: Counter = field(default_factory=Counter)

    @property
    def win_rate(self) -> float:
        return self.win_count / self.total_runs if self.total_runs else 0.0

    @property
    def avg_spells(self) -> float:
        return statistics.mean(self.spells_cast_list) if self.spells_cast_list else 0.0

    @property
    def median_cards_drawn(self) -> float:
        return statistics.median(self.cards_drawn_list) if self.cards_drawn_list else 0.0

    @property
    def avg_cards_drawn(self) -> float:
        return statistics.mean(self.cards_drawn_list) if self.cards_drawn_list else 0.0


def aggregate(results: list[RunResult]) -> AggregateMetrics:
    m = AggregateMetrics(total_runs=len(results))

    for r in results:
        if r.outcome == WIN_EXTRA_TURN:
            m.win_count += 1
            m.win_extra_turn_count += 1
            if r.winning_card:
                m.winning_cards[r.winning_card] += 1
        elif r.outcome == WIN_NONCREATURE_SPELL_COUNT:
            m.win_count += 1
            m.win_spell_count += 1
        elif r.outcome == BRICK_NO_ACTIONS:
            m.brick_no_actions_count += 1
        elif r.outcome == BRICK_NO_USEFUL_ACTIONS:
            m.brick_no_useful_count += 1
        else:
            m.error_count += 1

        if r.brick_reason:
            m.brick_reasons[r.brick_reason] += 1

        m.spells_cast_list.append(r.noncreature_spells_cast)
        m.cards_drawn_list.append(r.total_cards_drawn)
        m.hand_size_list.append(r.final_hand_size)

        for card in r.stranded_cards:
            m.stranded_cards[card] += 1

    return m


def format_metrics(m: AggregateMetrics) -> str:
    lines: list[str] = []
    w = 60

    lines.append("=" * w)
    lines.append(f"MONTE CARLO RESULTS  ({m.total_runs} runs)")
    lines.append("-" * w)
    lines.append(f"Win rate          : {m.win_rate:.1%}")
    lines.append(f"  Extra-turn wins : {m.win_extra_turn_count} ({m.win_extra_turn_count/m.total_runs:.1%})")
    lines.append(f"  40-spell wins   : {m.win_spell_count} ({m.win_spell_count/m.total_runs:.1%})")
    lines.append(f"Brick: no actions : {m.brick_no_actions_count}")
    lines.append(f"Brick: no useful  : {m.brick_no_useful_count}")
    lines.append(f"Errors            : {m.error_count}")
    lines.append("-" * w)
    lines.append(f"Avg spells cast   : {m.avg_spells:.1f}")
    lines.append(f"Avg cards drawn   : {m.avg_cards_drawn:.1f}")
    lines.append(f"Median cards drawn: {m.median_cards_drawn:.1f}")

    if m.winning_cards:
        lines.append("-" * w)
        lines.append("Top winning cards:")
        for card, cnt in m.winning_cards.most_common(5):
            lines.append(f"  {card:<30} {cnt}")

    if m.brick_reasons:
        lines.append("-" * w)
        lines.append("Brick reasons:")
        for reason, cnt in m.brick_reasons.most_common(5):
            lines.append(f"  {reason:<40} {cnt}")

    if m.stranded_cards:
        lines.append("-" * w)
        lines.append("Most stranded cards:")
        for card, cnt in m.stranded_cards.most_common(10):
            pct = cnt / m.total_runs * 100
            lines.append(f"  {card:<35} {cnt:>4} ({pct:.0f}%)")

    lines.append("=" * w)
    return "\n".join(lines)
