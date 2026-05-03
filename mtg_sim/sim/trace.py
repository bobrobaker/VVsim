"""Pretty-print run traces."""
from __future__ import annotations
from .runner import RunResult
from .actions import WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT


def format_trace(result: RunResult, show_full: bool = True) -> str:
    lines: list[str] = []
    w = 76

    lines.append("=" * w)
    outcome_label = {
        WIN_EXTRA_TURN:              "WIN  (extra turn)",
        WIN_NONCREATURE_SPELL_COUNT: "WIN  (40 spells)",
    }.get(result.outcome, f"BRICK ({result.brick_reason})")

    lines.append(f"OUTCOME : {outcome_label}")
    lines.append(f"Spells  : {result.noncreature_spells_cast} noncreature | "
                 f"{result.steps} steps | {result.total_cards_drawn} cards drawn")
    if result.winning_card:
        lines.append(f"Win card: {result.winning_card}")
    if result.stranded_cards:
        lines.append(f"Stranded: {', '.join(result.stranded_cards[:10])}")
    lines.append(f"Final   : hand={result.final_hand_size} | mana={result.final_mana}")
    lines.append("-" * w)

    if not show_full:
        lines.append("(use show_full=True for step-by-step trace)")
        lines.append("=" * w)
        return "\n".join(lines)

    for log in result.trace:
        step_str = f"[{log.step:>3}]"
        type_str = f"{log.event_type:<20}"
        mana = f"mana:{log.mana_before}→{log.mana_after}"
        hand = f"hand:{log.hand_size_before}→{log.hand_size_after}"
        sp_str = f"sp:{log.noncreature_spells_cast}"

        lines.append(f"{step_str} {type_str} {mana}  {hand}  {sp_str}")
        lines.append(f"       {log.action_description}")

        if log.cards_drawn:
            lines.append(f"       Drew: {', '.join(log.cards_drawn)}")
        if log.stack_snapshot:
            lines.append(f"       Stack: {' | '.join(log.stack_snapshot)}")
        for note in log.notes:
            lines.append(f"       > {note}")
        lines.append("")

    lines.append("=" * w)
    return "\n".join(lines)
