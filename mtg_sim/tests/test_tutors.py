"""Tests for the Tutors bucket (docs/card_specifics.md lines 225-288)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.actions import CAST_SPELL, ACTIVATE_TRANSMUTE, CHOOSE_TUTOR
from random import Random

RESOLVE_STACK_OBJECT = "RESOLVE_STACK_OBJECT"


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def _state(hand, mana, library_extra=None):
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=mana)
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    if library_extra is not None:
        state.library = library_extra + [c for c in state.library if c not in library_extra]
    return state


def _drain_stack(state):
    """Resolve all stack objects until stack empty or a pending choice appears."""
    while state.stack and not state.pending_choices:
        actions = generate_actions(state)
        res = next((a for a in actions if a.action_type == RESOLVE_STACK_OBJECT), None)
        if res is None:
            break
        resolve_action(state, res)


def _cast_and_resolve(state, card_name):
    """Cast card_name from hand and fully resolve stack, returning tutor actions."""
    actions = generate_actions(state)
    cast = next(a for a in actions if a.source_card == card_name and a.action_type == CAST_SPELL)
    resolve_action(state, cast)
    _drain_stack(state)
    return [a for a in generate_actions(state) if a.action_type == CHOOSE_TUTOR]


# ── Bucket-level: preferred targets appear first ──────────────────────────────

def test_preferred_targets_appear_first():
    """If a preferred target is in the library, it comes before non-preferred cards."""
    state = _state(["Mystical Tutor"], ManaPool(U=1))
    tutor_actions = _cast_and_resolve(state, "Mystical Tutor")
    names = [a.source_card for a in tutor_actions]
    preferred = {"Final Fortune", "Last Chance", "Warrior's Oath", "Jeska's Will",
                 "Intuition", "Solve the Equation", "Gamble", "Gitaxian Probe"}
    first_preferred_idx = next((i for i, n in enumerate(names) if n in preferred), None)
    first_nonpreferred_idx = next((i for i, n in enumerate(names) if n not in preferred), None)
    if first_preferred_idx is not None and first_nonpreferred_idx is not None:
        assert first_preferred_idx < first_nonpreferred_idx


def test_unavailable_preferred_skipped_fallback_legal():
    """If no preferred targets are in library, fallback legal target is still offered."""
    state = _state(["Merchant Scroll"], ManaPool(U=1, C=1))
    preferred = {"Intuition", "Snapback", "Force of Will", "Fierce Guardianship", "Mystical Tutor"}
    state.library = [c for c in state.library if c not in preferred]
    tutor_actions = _cast_and_resolve(state, "Merchant Scroll")
    assert len(tutor_actions) > 0, "Should still offer a fallback blue instant"
    for a in tutor_actions:
        assert a.source_card not in preferred


def test_chosen_card_moves_to_hand():
    """Resolving a CHOOSE_TUTOR action puts the card in hand."""
    state = _state(["Gamble"], ManaPool(R=1))
    tutor_actions = _cast_and_resolve(state, "Gamble")
    assert tutor_actions, "No tutor choices after Gamble"
    pick = tutor_actions[0]
    target_name = pick.source_card
    resolve_action(state, pick)
    assert target_name in state.hand


# ── Dizzy Spell ───────────────────────────────────────────────────────────────

def test_dizzy_spell_instant_mode_castable():
    """Dizzy Spell can be cast as an instant targeting a creature."""
    state = _state(["Dizzy Spell"], ManaPool(U=1))
    actions = generate_actions(state)
    casts = [a for a in actions if a.source_card == "Dizzy Spell" and a.action_type == CAST_SPELL]
    assert len(casts) >= 1

def test_dizzy_spell_transmute_sorcery_speed_only():
    """Transmute only offered when stack is empty."""
    from mtg_sim.sim.stack import StackObject
    state = _state(["Dizzy Spell"], ManaPool())
    # With empty stack
    actions = generate_actions(state)
    transmutes = [a for a in actions if a.source_card == "Dizzy Spell" and a.action_type == ACTIVATE_TRANSMUTE]
    assert len(transmutes) == 1
    # With non-empty stack
    state.stack.append(StackObject(card_name="Some Spell"))
    actions = generate_actions(state)
    transmutes = [a for a in actions if a.source_card == "Dizzy Spell" and a.action_type == ACTIVATE_TRANSMUTE]
    assert len(transmutes) == 0

def test_dizzy_spell_transmute_tutors_mv1_only():
    """Transmute resolves to a pending tutor choice for MV=1 cards only."""
    state = _state(["Dizzy Spell"], ManaPool())
    # Ensure library has an MV=1 card
    state.library = ["Gitaxian Probe"] + [c for c in state.library if c != "Gitaxian Probe"]
    actions = generate_actions(state)
    transmute = next(a for a in actions if a.source_card == "Dizzy Spell" and a.action_type == ACTIVATE_TRANSMUTE)
    resolve_action(state, transmute)
    assert "Dizzy Spell" in state.graveyard
    tutor_actions = [a for a in generate_actions(state) if a.action_type == CHOOSE_TUTOR]
    from mtg_sim.sim.cards import get_card
    for a in tutor_actions:
        cd = get_card(a.source_card)
        assert cd is not None and cd.mv == 1, f"{a.source_card} is not MV=1"

def test_dizzy_spell_transmute_preferred_first():
    """Gitaxian Probe appears before other MV=1 targets in transmute choice."""
    state = _state(["Dizzy Spell"], ManaPool())
    state.library = ["Rite of Flame", "Gitaxian Probe"] + [c for c in state.library
                      if c not in {"Rite of Flame", "Gitaxian Probe"}]
    actions = generate_actions(state)
    transmute = next(a for a in actions if a.source_card == "Dizzy Spell" and a.action_type == ACTIVATE_TRANSMUTE)
    resolve_action(state, transmute)
    tutor_actions = [a for a in generate_actions(state) if a.action_type == CHOOSE_TUTOR]
    names = [a.source_card for a in tutor_actions]
    assert names[0] == "Gitaxian Probe", f"Expected Gitaxian Probe first, got {names}"

def test_dizzy_spell_transmute_not_a_spell_cast():
    """Transmuting Dizzy Spell does not increment noncreature_spells_cast."""
    state = _state(["Dizzy Spell"], ManaPool())
    before = state.noncreature_spells_cast
    actions = generate_actions(state)
    transmute = next(a for a in actions if a.source_card == "Dizzy Spell" and a.action_type == ACTIVATE_TRANSMUTE)
    resolve_action(state, transmute)
    assert state.noncreature_spells_cast == before


# ── Drift of Phantasms ────────────────────────────────────────────────────────

def test_drift_normal_cast_enters_battlefield():
    """Drift of Phantasms cast normally enters the battlefield."""
    state = _state(["Drift of Phantasms"], ManaPool(U=3))
    actions = generate_actions(state)
    cast = next(a for a in actions if a.source_card == "Drift of Phantasms" and a.action_type == CAST_SPELL)
    resolve_action(state, cast)
    _drain_stack(state)
    assert any(p.card_name == "Drift of Phantasms" for p in state.battlefield)

def test_drift_transmute_only_with_empty_stack():
    """Transmute only offered when stack is empty."""
    from mtg_sim.sim.stack import StackObject
    state = _state(["Drift of Phantasms"], ManaPool())
    actions = generate_actions(state)
    transmutes = [a for a in actions if a.source_card == "Drift of Phantasms" and a.action_type == ACTIVATE_TRANSMUTE]
    assert len(transmutes) == 1
    state.stack.append(StackObject(card_name="Some Spell"))
    actions = generate_actions(state)
    transmutes = [a for a in actions if a.source_card == "Drift of Phantasms" and a.action_type == ACTIVATE_TRANSMUTE]
    assert len(transmutes) == 0

def test_drift_transmute_tutors_mv3_only():
    """Drift transmute produces a tutor choice restricted to MV=3 cards."""
    state = _state(["Drift of Phantasms"], ManaPool())
    actions = generate_actions(state)
    transmute = next(a for a in actions if a.source_card == "Drift of Phantasms" and a.action_type == ACTIVATE_TRANSMUTE)
    resolve_action(state, transmute)
    assert "Drift of Phantasms" in state.graveyard
    tutor_actions = [a for a in generate_actions(state) if a.action_type == CHOOSE_TUTOR]
    from mtg_sim.sim.cards import get_card
    for a in tutor_actions:
        cd = get_card(a.source_card)
        assert cd is not None and cd.mv == 3, f"{a.source_card} is not MV=3"

def test_drift_transmute_preferred_first():
    """Preferred MV=3 targets appear before non-preferred ones."""
    drift_preferred = {"Alchemist's Gambit", "Final Fortune", "Last Chance", "Warrior's Oath",
                       "Jeska's Will", "Intuition", "Solve the Equation", "Snapback", "Tandem Lookout"}
    state = _state(["Drift of Phantasms"], ManaPool())
    actions = generate_actions(state)
    transmute = next(a for a in actions if a.source_card == "Drift of Phantasms" and a.action_type == ACTIVATE_TRANSMUTE)
    resolve_action(state, transmute)
    tutor_actions = [a for a in generate_actions(state) if a.action_type == CHOOSE_TUTOR]
    names = [a.source_card for a in tutor_actions]
    first_pref = next((i for i, n in enumerate(names) if n in drift_preferred), None)
    first_nonpref = next((i for i, n in enumerate(names) if n not in drift_preferred), None)
    if first_pref is not None and first_nonpref is not None:
        assert first_pref < first_nonpref, f"Non-preferred appeared before preferred: {names[:6]}"

def test_drift_transmute_not_a_spell_cast():
    """Transmuting Drift of Phantasms does not increment noncreature_spells_cast."""
    state = _state(["Drift of Phantasms"], ManaPool())
    before = state.noncreature_spells_cast
    actions = generate_actions(state)
    transmute = next(a for a in actions if a.source_card == "Drift of Phantasms" and a.action_type == ACTIVATE_TRANSMUTE)
    resolve_action(state, transmute)
    assert state.noncreature_spells_cast == before


# ── Imperial Recruiter ────────────────────────────────────────────────────────

def _cast_imperial_recruiter(state):
    """Cast Imperial Recruiter and resolve stack, returning tutor actions."""
    actions = generate_actions(state)
    cast = next(a for a in actions if a.source_card == "Imperial Recruiter" and a.action_type == CAST_SPELL)
    resolve_action(state, cast)
    _drain_stack(state)
    return [a for a in generate_actions(state) if a.action_type == CHOOSE_TUTOR]


def test_imperial_recruiter_enters_battlefield():
    """Imperial Recruiter cast normally enters the battlefield."""
    state = _state(["Imperial Recruiter"], ManaPool(R=3))
    _cast_imperial_recruiter(state)
    assert any(p.card_name == "Imperial Recruiter" for p in state.battlefield)

def test_imperial_recruiter_creates_tutor_choice():
    """ETB queues a creature power<=2 tutor choice."""
    state = _state(["Imperial Recruiter"], ManaPool(R=3))
    tutor_actions = _cast_imperial_recruiter(state)
    assert len(tutor_actions) > 0, "ETB should create a creature tutor choice"

def test_imperial_recruiter_only_offers_power_lte2():
    """All tutor options are creatures with power <= 2."""
    from mtg_sim.sim.action_generator import _POWER_LTE2_CREATURES
    state = _state(["Imperial Recruiter"], ManaPool(R=3))
    tutor_actions = _cast_imperial_recruiter(state)
    for a in tutor_actions:
        assert a.source_card in _POWER_LTE2_CREATURES, f"{a.source_card} has power > 2"

def test_imperial_recruiter_preferred_first():
    """Simian Spirit Guide appears before Drift of Phantasms in tutor list."""
    state = _state(["Imperial Recruiter"], ManaPool(R=3))
    state.library = ["Drift of Phantasms", "Simian Spirit Guide"] + [
        c for c in state.library if c not in {"Drift of Phantasms", "Simian Spirit Guide"}]
    tutor_actions = _cast_imperial_recruiter(state)
    names = [a.source_card for a in tutor_actions]
    assert names[0] == "Simian Spirit Guide", f"Expected Simian Spirit Guide first, got {names}"

def test_imperial_recruiter_chosen_creature_goes_to_hand():
    """The tutored creature enters hand."""
    state = _state(["Imperial Recruiter"], ManaPool(R=3))
    state.library = ["Tandem Lookout"] + [c for c in state.library if c != "Tandem Lookout"]
    tutor_actions = _cast_imperial_recruiter(state)
    pick = next(a for a in tutor_actions if a.source_card == "Tandem Lookout")
    resolve_action(state, pick)
    assert "Tandem Lookout" in state.hand


# ── Gamble ────────────────────────────────────────────────────────────────────

def test_gamble_creates_any_card_tutor():
    """Gamble resolves to a tutor choice for any card."""
    state = _state(["Gamble"], ManaPool(R=1))
    tutor_actions = _cast_and_resolve(state, "Gamble")
    assert len(tutor_actions) > 0

def test_gamble_random_discard_after_tutor():
    """After tutoring, a random card from hand is discarded (net hand size unchanged)."""
    state = _state(["Gamble"], ManaPool(R=1))
    tutor_actions = _cast_and_resolve(state, "Gamble")
    assert tutor_actions, "No tutor choices after Gamble"
    hand_before = len(state.hand)
    resolve_action(state, tutor_actions[0])
    # Hand gained tutored card then lost one random card: net 0 change
    assert len(state.hand) == hand_before

def test_gamble_preferred_first():
    """Preferred targets appear before non-preferred targets in Gamble tutor list."""
    gamble_preferred = {"Final Fortune", "Last Chance", "Warrior's Oath", "Lotus Petal", "Jeska's Will"}
    state = _state(["Gamble"], ManaPool(R=1))
    tutor_actions = _cast_and_resolve(state, "Gamble")
    names = [a.source_card for a in tutor_actions]
    first_pref = next((i for i, n in enumerate(names) if n in gamble_preferred), None)
    first_nonpref = next((i for i, n in enumerate(names) if n not in gamble_preferred), None)
    if first_pref is not None and first_nonpref is not None:
        assert first_pref < first_nonpref, f"Preferred target at {first_pref}, non-preferred at {first_nonpref}: {names[:5]}"


# ── Mystical Tutor ────────────────────────────────────────────────────────────

def test_mystical_tutor_instant_speed():
    """Mystical Tutor can be cast while stack is non-empty."""
    from mtg_sim.sim.stack import StackObject
    state = _state(["Mystical Tutor"], ManaPool(U=1))
    state.stack.append(StackObject(card_name="Some Spell"))
    actions = generate_actions(state)
    casts = [a for a in actions if a.source_card == "Mystical Tutor" and a.action_type == CAST_SPELL]
    assert len(casts) >= 1

def test_mystical_tutor_puts_card_on_top():
    """Mystical Tutor puts the chosen card on top of library, not in hand."""
    state = _state(["Mystical Tutor"], ManaPool(U=1))
    tutor_actions = _cast_and_resolve(state, "Mystical Tutor")
    assert tutor_actions, "No tutor choices after Mystical Tutor"
    pick = tutor_actions[0]
    target_name = pick.source_card
    resolve_action(state, pick)
    assert state.library[0] == target_name, f"Expected {target_name} on top, got {state.library[0]}"
    assert target_name not in state.hand

def test_mystical_tutor_instant_sorcery_only():
    """Mystical Tutor only offers instants and sorceries."""
    state = _state(["Mystical Tutor"], ManaPool(U=1))
    tutor_actions = _cast_and_resolve(state, "Mystical Tutor")
    from mtg_sim.sim.cards import get_card
    for a in tutor_actions:
        cd = get_card(a.source_card)
        assert cd is not None and (cd.is_instant or cd.is_sorcery), f"{a.source_card} is not instant/sorcery"


# ── Merchant Scroll ───────────────────────────────────────────────────────────

def test_merchant_scroll_sorcery_speed():
    """Merchant Scroll cannot be cast while stack is non-empty."""
    from mtg_sim.sim.stack import StackObject
    state = _state(["Merchant Scroll"], ManaPool(U=2))
    state.stack.append(StackObject(card_name="Some Spell"))
    actions = generate_actions(state)
    casts = [a for a in actions if a.source_card == "Merchant Scroll" and a.action_type == CAST_SPELL]
    assert len(casts) == 0

def test_merchant_scroll_blue_instant_only():
    """Merchant Scroll only offers blue instants."""
    state = _state(["Merchant Scroll"], ManaPool(U=2))
    tutor_actions = _cast_and_resolve(state, "Merchant Scroll")
    from mtg_sim.sim.cards import get_card
    for a in tutor_actions:
        cd = get_card(a.source_card)
        assert cd is not None and cd.is_instant and cd.has_blue, f"{a.source_card} is not a blue instant"


# ── Solve the Equation ────────────────────────────────────────────────────────

def test_solve_the_equation_tutors_instant_sorcery_to_hand():
    """Solve the Equation puts chosen instant/sorcery into hand."""
    state = _state(["Solve the Equation"], ManaPool(U=3))
    tutor_actions = _cast_and_resolve(state, "Solve the Equation")
    assert tutor_actions, "No tutor choices after Solve the Equation"
    pick = tutor_actions[0]
    target_name = pick.source_card
    resolve_action(state, pick)
    assert target_name in state.hand
    assert state.library[0] != target_name


# ── Intuition ─────────────────────────────────────────────────────────────────

def test_intuition_instant_speed():
    """Intuition can be cast while stack is non-empty."""
    from mtg_sim.sim.stack import StackObject
    state = _state(["Intuition"], ManaPool(U=3))
    state.stack.append(StackObject(card_name="Some Spell"))
    actions = generate_actions(state)
    casts = [a for a in actions if a.source_card == "Intuition" and a.action_type == CAST_SPELL]
    assert len(casts) >= 1

def test_intuition_chosen_card_to_hand_two_to_graveyard():
    """Intuition puts chosen card in hand and two library cards in graveyard."""
    state = _state(["Intuition"], ManaPool(U=3))
    tutor_actions = _cast_and_resolve(state, "Intuition")
    assert tutor_actions, "No tutor choices after Intuition"
    pick = tutor_actions[0]
    target_name = pick.source_card
    gy_before = len(state.graveyard)
    resolve_action(state, pick)
    assert target_name in state.hand
    assert len(state.graveyard) == gy_before + 2
