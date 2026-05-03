"""Greedy action selection policy."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from .actions import (
    Action,
    CAST_SPELL, RESOLVE_STACK_OBJECT, PLAY_LAND,
    ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA, SACRIFICE_FOR_MANA,
    RISK_SAFE, RISK_NORMAL, RISK_EXPENSIVE, RISK_RISKY, RISK_DESPERATE,
    EXTRA_TURN_WIN_CARDS, NONCREATURE_SPELL_WIN_THRESHOLD,
)

if TYPE_CHECKING:
    from .state import GameState


def choose_action(state: GameState, actions: list[Action]) -> Optional[Action]:
    if not actions:
        return None

    scored = [(score_action(state, a), a) for a in actions]
    scored.sort(key=lambda x: -x[0])

    best_score, best_action = scored[0]
    if best_score <= 0:
        return None

    return best_action


def score_action(state: GameState, action: Action) -> float:
    from .cards import get_card

    s_card = action.source_card
    cd = get_card(s_card) if s_card else None

    # ── Instant win ───────────────────────────────────────────────────────────
    if action.action_type == CAST_SPELL and s_card in EXTRA_TURN_WIN_CARDS:
        return 10000.0

    # ── Cast spell ────────────────────────────────────────────────────────────
    if action.action_type == CAST_SPELL:
        if cd is None:
            return 10.0

        score = 0.0

        # Creature spells: limited value (only special cases should appear)
        if cd.is_creature:
            score = 30.0
            return score + _risk_penalty(action.risk_level)

        if not cd.is_noncreature_spell:
            return 5.0

        # Base value: every noncreature spell draws cards
        score = 100.0

        # Free spells are best (cost 0)
        cost = action.costs.mana
        effective_cost = cost.total_mana
        if effective_cost == 0:
            score += 60.0
        elif effective_cost == 1:
            score += 30.0
        elif effective_cost == 2:
            score += 15.0
        elif effective_cost <= 3:
            score += 5.0

        # Mana-producing spells on resolution (rituals)
        if s_card in ("Rite of Flame", "Strike It Rich", "Jeska's Will"):
            score += 40.0

        # Tutors: get us to next play
        if _is_tutor(s_card):
            score += 25.0

        # Draw-on-resolution spells
        if s_card in ("Gitaxian Probe", "Twisted Image", "Repeal"):
            score += 20.0

        # Counterspells targeting own stack objects (counter for draw)
        if action.target and action.requires_target:
            obj = state.get_stack_object(action.target)
            if obj:
                # Countering own spell = net card advantage
                score += 15.0

        # Alt cost that doesn't spend our mana is valuable
        if action.alt_cost_type in ("pay_life", "commander_free", "delayed_upkeep"):
            score += 25.0

        score += _risk_penalty(action.risk_level)

        # Penalize if we need the mana more than the draw
        if effective_cost >= 3 and _mana_is_tight(state):
            score -= 20.0

        return score

    # ── Resolve stack object ──────────────────────────────────────────────────
    if action.action_type == RESOLVE_STACK_OBJECT:
        obj = state.get_stack_object(action.target or "")
        if obj is None:
            return 20.0

        # Resolve mana producers ASAP (Rite of Flame, Strike It Rich, etc.)
        if _will_produce_mana(obj.card_name):
            return 85.0

        # Resolve engine-improving cards ASAP
        if obj.card_name in ("Tandem Lookout", "Curiosity", "Ophidian Eye",
                              "Sol Ring", "Mana Vault", "Grim Monolith",
                              "Lotus Petal", "Chrome Mox", "Mox Diamond",
                              "Mox Opal", "Mox Amber", "Springleaf Drum"):
            return 80.0

        # If nothing else to cast, resolve everything
        castable_count = sum(1 for a in [] if a.action_type == CAST_SPELL)
        return 40.0

    # ── Mana actions ──────────────────────────────────────────────────────────
    if action.action_type in (ACTIVATE_MANA_ABILITY, SACRIFICE_FOR_MANA):
        # Only activate mana if it enables a currently unaffordable spell
        if _mana_enables_new_cast(state, action):
            return 90.0
        # Safe mana that doesn't deplete scarce resources
        if action.risk_level == RISK_SAFE:
            return 70.0
        return 50.0

    if action.action_type == EXILE_FOR_MANA:
        if _mana_enables_new_cast(state, action):
            return 75.0
        return 45.0

    # ── Land play ─────────────────────────────────────────────────────────────
    if action.action_type == PLAY_LAND:
        if _land_enables_new_cast(state, action):
            return 78.0
        return 55.0

    return 0.0


def _risk_penalty(risk: str) -> float:
    return {
        RISK_SAFE:      0.0,
        RISK_NORMAL:    0.0,
        RISK_EXPENSIVE: -15.0,
        RISK_RISKY:     -35.0,
        RISK_DESPERATE: -70.0,
    }.get(risk, 0.0)


def _is_tutor(card_name: str | None) -> bool:
    TUTORS = {
        "Mystical Tutor", "Merchant Scroll", "Solve the Equation",
        "Gamble", "Intuition", "Drift of Phantasms",
    }
    return card_name in TUTORS


def _will_produce_mana(card_name: str) -> bool:
    MANA_PRODUCERS = {
        "Rite of Flame", "Strike It Rich", "Jeska's Will",
        "Sol Ring", "Mana Vault", "Grim Monolith",
        "Lotus Petal", "Lion's Eye Diamond",
        "Chrome Mox", "Mox Diamond", "Mox Opal", "Mox Amber",
        "Springleaf Drum", "Jeweled Amulet",
    }
    return card_name in MANA_PRODUCERS


def _mana_is_tight(state: GameState) -> bool:
    return state.floating_mana.total() <= 2


def _mana_enables_new_cast(state: GameState, mana_action: Action) -> bool:
    """Check if activating this mana source would let us cast something we can't currently."""
    from .mana import ManaPool, can_pay_cost
    from .mana import ManaCost
    from .cards import get_card
    from .action_generator import generate_actions

    # Simulate adding the mana
    gained = mana_action.effects.add_mana
    if gained.total() == 0:
        return False

    simulated_pool = state.floating_mana.copy()
    simulated_pool.add(gained)

    # Check if any card in hand becomes newly castable
    for card_name in state.hand:
        cd = get_card(card_name)
        if cd is None or cd.is_land or cd.is_creature:
            continue
        cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost) and can_pay_cost(simulated_pool, cost):
            return True
    return False


def _land_enables_new_cast(state: GameState, land_action: Action) -> bool:
    """Would playing this land (and tapping it) enable a new cast?"""
    from .cards import get_card
    from .mana import ManaPool, can_pay_cost, ManaCost

    land_name = land_action.source_card
    if not land_name:
        return False
    cd = get_card(land_name)
    if cd is None or not cd.produces_mana:
        return False

    # Estimate mana gain
    if cd.land_enters_tapped == "true":
        return False  # can't tap it this turn

    try:
        amount = int(cd.mana_amount)
    except (ValueError, TypeError):
        amount = 1

    simulated = state.floating_mana.copy()
    if "U" in (cd.mana_colors or ""):
        simulated.U += amount
    elif "R" in (cd.mana_colors or ""):
        simulated.R += amount
    else:
        simulated.ANY += amount

    for card_name in state.hand:
        c = get_card(card_name)
        if c is None or c.is_land:
            continue
        cost = ManaCost(pip_u=c.pip_u, pip_r=c.pip_r, generic=c.generic_mana)
        if not can_pay_cost(state.floating_mana, cost) and can_pay_cost(simulated, cost):
            return True
    return False
