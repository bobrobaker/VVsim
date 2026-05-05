"""Main simulation runner."""
from __future__ import annotations
from dataclasses import dataclass, field
from random import Random
from pathlib import Path
from typing import Optional
from .mana import ManaPool
from .state import GameState, Permanent, ActionLog, OPPONENT_COUNT
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
    starting_battlefield: list = field(default_factory=lambda: ["Volcanic Island"])
    # Cards in starting_battlefield that enter tapped (Volcanic Island already tapped because
    # we tapped it for the starting mana floating into the sim).
    starting_battlefield_tapped: list = field(default_factory=lambda: ["Volcanic Island"])
    land_play_available: bool = False
    debug: bool = False
    # Interactive mode: pause after each action generation and let the user pick.
    manual_mode: bool = False
    # Simulation assumptions
    opponent_controls_island: bool = True  # almost always true in cEDH


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
    from .state import validate_state
    rng = Random(config.seed)
    state = _build_initial_state(config, all_card_names, rng)
    validate_state(state)

    # Capture initial state info before the draw
    bf_names = [p.card_name for p in state.battlefield]
    hand_str = ", ".join(config.starting_hand) if config.starting_hand else "(empty)"

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
        notes=[
            f"Battlefield: {bf_names}",
            f"Starting hand: {hand_str}",
            f"Starting mana: {config.starting_floating_mana}",
            f"Land play available: {state.land_play_available}",
        ],
    ))

    for step in range(MAX_STEPS):
        if config.debug:
            validate_state(state)
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
        if config.manual_mode:
            chosen = _manual_choose_action(state, actions, step)
        else:
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


def _manual_choose_action(state: GameState, actions: list, step: int) -> Optional:
    """Present actions to the user and return their choice, or None to brick."""
    from .actions import Action
    print(f"\n{'='*60}")
    print(f"Step {step + 1} | Spells cast: {state.noncreature_spells_cast} | "
          f"Pending draws: {state.pending_curiosity_draws}")
    print(f"Mana: {state.floating_mana}")
    print(f"Hand ({len(state.hand)}): {state.hand}")
    print(f"Battlefield: {state.battlefield}")
    if state.stack:
        print(f"Stack: {[str(o) for o in state.stack]}")
    if state.graveyard:
        print(f"Graveyard: {state.graveyard}")
    print(f"\nAvailable actions:")
    for i, action in enumerate(actions):
        print(f"  [{i:2d}] {action.description}")
    print(f"  [ q] Quit (brick)")

    while True:
        try:
            raw = input("\nChoose action number: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if raw.lower() == "q":
            return None
        try:
            idx = int(raw)
            if 0 <= idx < len(actions):
                chosen = actions[idx]
                print(f">>> {chosen.description}")
                return chosen
        except ValueError:
            pass
        print(f"Enter a number 0-{len(actions)-1} or 'q'.")


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
    vivi = "Vivi Ornitier"
    remaining = [c for c in all_card_names if c != vivi and c not in config.starting_hand]

    # Remove starting_battlefield cards from the library pool (zone consistency)
    for card_name in config.starting_battlefield:
        assert card_name in remaining, (
            f"starting_battlefield card '{card_name}' not found in decklist "
            f"(or conflicts with starting_hand / another starting_battlefield entry)"
        )
        remaining.remove(card_name)

    if config.library_order is not None:
        library = [c for c in config.library_order if c in remaining]
    else:
        library = remaining.copy()
        rng.shuffle(library)

    tapped_set = set(config.starting_battlefield_tapped)

    state = GameState(
        hand=list(config.starting_hand),
        library=library,
        floating_mana=config.starting_floating_mana.copy(),
        curiosity_effect_count=config.curiosity_effect_count,
        cards_drawn_per_noncreature_spell=OPPONENT_COUNT * config.curiosity_effect_count,
        land_play_available=config.land_play_available,
        vivi_on_battlefield=True,
        vivi_available_as_creature_to_tap=True,
        legendary_permanent_available=True,
        rng=rng,
        jeska_opponent_hand_size=config.jeska_opponent_hand_size,
        opponent_controls_island=config.opponent_controls_island,
    )

    # Vivi always starts on the battlefield
    state.battlefield.append(Permanent(card_name=vivi, tapped=False))

    # Place starting battlefield permanents (already removed from library above)
    for card_name in config.starting_battlefield:
        tapped = card_name in tapped_set
        state.battlefield.append(Permanent(card_name=card_name, tapped=tapped))

    return state
