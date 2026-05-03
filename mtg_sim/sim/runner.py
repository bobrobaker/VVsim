"""Main simulation runner."""
from __future__ import annotations
from dataclasses import dataclass, field
from random import Random
from pathlib import Path
from .mana import ManaPool
from .state import GameState, Permanent, ActionLog
from .stack import StackObject
from .actions import (
    WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT,
    BRICK_NO_ACTIONS, BRICK_NO_USEFUL_ACTIONS, ERROR_INVALID_STATE,
    EXTRA_TURN_WIN_CARDS, NONCREATURE_SPELL_WIN_THRESHOLD,
)
from .action_generator import generate_actions
from .resolver import resolve_action, draw_cards
from .policies import choose_action

DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent

MAX_STEPS = 500


@dataclass
class RunConfig:
    seed: int
    starting_hand: list = field(default_factory=list)
    starting_floating_mana: ManaPool = field(default_factory=ManaPool)
    library_order: list | None = None
    curiosity_effect_count: int = 1
    jeska_opponent_hand_size: int = 7
    csv_path: str = ""
    decklist_path: str = ""


@dataclass
class RunResult:
    outcome: str
    noncreature_spells_cast: int = 0
    total_cards_drawn: int = 0
    final_hand_size: int = 0
    final_mana: ManaPool = field(default_factory=ManaPool)
    brick_reason: str = ""
    winning_card: str = ""
    steps: int = 0
    trace: list = field(default_factory=list)
    stranded_cards: list = field(default_factory=list)

    @property
    def won(self) -> bool:
        return self.outcome in (WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT)


def simulate_run(config: RunConfig, all_card_names: list[str]) -> RunResult:
    rng = Random(config.seed)
    state = _build_initial_state(config, all_card_names, rng)

    # Initial Curiosity draw
    drawn = draw_cards(state, state.cards_drawn_per_noncreature_spell)
    state.trace.append(ActionLog(
        step=0,
        event_type="INITIAL_DRAW",
        action_description=f"Initial Curiosity draw: {len(drawn)} cards",
        cards_drawn=drawn,
        mana_before=state.floating_mana.copy(),
        mana_after=state.floating_mana.copy(),
        hand_size_before=0,
        hand_size_after=len(state.hand),
        noncreature_spells_cast=0,
    ))

    for step in range(MAX_STEPS):
        # ── Check win ────────────────────────────────────────────────────────
        outcome, winning_card = _check_win(state)
        if outcome:
            return RunResult(
                outcome=outcome,
                noncreature_spells_cast=state.noncreature_spells_cast,
                total_cards_drawn=state.total_cards_drawn,
                final_hand_size=len(state.hand),
                final_mana=state.floating_mana.copy(),
                winning_card=winning_card,
                steps=step,
                trace=state.trace,
            )

        # ── Generate actions ─────────────────────────────────────────────────
        actions = generate_actions(state)

        if not actions:
            return _brick(state, BRICK_NO_ACTIONS, "No legal actions", step)

        # ── Policy selects action ─────────────────────────────────────────────
        chosen = choose_action(state, actions)

        if chosen is None:
            return _brick(state, BRICK_NO_USEFUL_ACTIONS, "No useful action", step)

        # ── Execute ───────────────────────────────────────────────────────────
        resolve_action(state, chosen)

        # ── Post-action win check ─────────────────────────────────────────────
        outcome, winning_card = _check_win(state)
        if outcome:
            return RunResult(
                outcome=outcome,
                noncreature_spells_cast=state.noncreature_spells_cast,
                total_cards_drawn=state.total_cards_drawn,
                final_hand_size=len(state.hand),
                final_mana=state.floating_mana.copy(),
                winning_card=winning_card,
                steps=step + 1,
                trace=state.trace,
            )

    return _brick(state, ERROR_INVALID_STATE, f"Exceeded {MAX_STEPS} steps", MAX_STEPS)


def _check_win(state: GameState) -> tuple[str, str]:
    # Extra-turn card successfully cast = it's now on the stack. Wins immediately.
    for obj in state.stack:
        if obj.card_name in EXTRA_TURN_WIN_CARDS:
            return WIN_EXTRA_TURN, obj.card_name
    if state.noncreature_spells_cast >= NONCREATURE_SPELL_WIN_THRESHOLD:
        return WIN_NONCREATURE_SPELL_COUNT, f"{state.noncreature_spells_cast} spells"
    return "", ""


def _brick(state: GameState, outcome: str, reason: str, step: int) -> RunResult:
    stranded = [
        c for c in state.hand
        if c not in ("Island", "Mountain")
    ]
    return RunResult(
        outcome=outcome,
        noncreature_spells_cast=state.noncreature_spells_cast,
        total_cards_drawn=state.total_cards_drawn,
        final_hand_size=len(state.hand),
        final_mana=state.floating_mana.copy(),
        brick_reason=reason,
        steps=step,
        trace=state.trace,
        stranded_cards=stranded,
    )


def _build_initial_state(config: RunConfig, all_card_names: list[str], rng: Random) -> GameState:
    # Library = all cards - Vivi - starting hand
    vivi = "Vivi Ornitier"
    remaining = [c for c in all_card_names if c != vivi and c not in config.starting_hand]

    if config.library_order is not None:
        library = [c for c in config.library_order if c in remaining]
    else:
        library = remaining.copy()
        rng.shuffle(library)

    state = GameState(
        hand=list(config.starting_hand),
        library=library,
        floating_mana=config.starting_floating_mana.copy(),
        curiosity_effect_count=config.curiosity_effect_count,
        cards_drawn_per_noncreature_spell=3 * config.curiosity_effect_count,
        vivi_on_battlefield=True,
        vivi_available_as_creature_to_tap=True,
        legendary_permanent_available=True,
        rng=rng,
        jeska_opponent_hand_size=config.jeska_opponent_hand_size,
    )

    # Vivi on battlefield
    state.battlefield.append(Permanent(card_name=vivi, tapped=False))

    return state
