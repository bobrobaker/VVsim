"""Tests for Invert // Invent split card handling."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_cards, load_decklist
from mtg_sim.sim.mana import ManaPool, ManaCost
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.actions import CAST_SPELL
from mtg_sim.sim.state import GameState
from random import Random


def _load():
    load_cards(str(DATA_DIR / "mtg_sim_card_data_v1.csv"))
    return load_decklist(str(DATA_DIR / "testdecklist.txt"))


def _state_with_hand(hand, mana, cards):
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=mana)
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    draw_cards(state, 3)  # initial curiosity draw
    return state


def test_invert_face_castable_with_u():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(U=1), cards)
    actions = generate_actions(state)
    invert_casts = [a for a in actions if a.source_card == "Invert / Invent"
                    and a.action_type == CAST_SPELL and a.alt_cost_type != "invent_face"]
    assert len(invert_casts) >= 1, "Invert face should be castable with U=1"


def test_invert_face_castable_with_r():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(R=1), cards)
    actions = generate_actions(state)
    invert_casts = [a for a in actions if a.source_card == "Invert / Invent"
                    and a.action_type == CAST_SPELL and a.alt_cost_type != "invent_face"]
    assert len(invert_casts) >= 1, "Invert face should be castable with R=1"


def test_invert_face_not_castable_with_c_only():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(C=1), cards)
    actions = generate_actions(state)
    invert_casts = [a for a in actions if a.source_card == "Invert / Invent"
                    and a.action_type == CAST_SPELL and a.alt_cost_type != "invent_face"]
    assert len(invert_casts) == 0, "Invert face should not be castable with C only"


def test_invent_face_generated_when_affordable_and_stack_empty():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(U=3, C=4), cards)
    assert not state.stack
    actions = generate_actions(state)
    invent_casts = [a for a in actions if a.source_card == "Invert / Invent"
                    and a.alt_cost_type == "invent_face"]
    assert len(invent_casts) == 1, "Invent face should be generated with {4}{U/R}{U/R} available"


def test_invent_face_not_generated_when_stack_nonempty():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(U=3, C=4), cards)
    # Put something on the stack
    from mtg_sim.sim.stack import StackObject
    state.stack.append(StackObject(card_name="Lotus Petal"))
    actions = generate_actions(state)
    invent_casts = [a for a in actions if a.source_card == "Invert / Invent"
                    and a.alt_cost_type == "invent_face"]
    assert len(invent_casts) == 0, "Invent face (sorcery-speed) must not be generated with stack non-empty"


def test_invent_face_not_generated_when_unaffordable():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(U=1), cards)
    actions = generate_actions(state)
    invent_casts = [a for a in actions if a.source_card == "Invert / Invent"
                    and a.alt_cost_type == "invent_face"]
    assert len(invent_casts) == 0, "Invent face should not be generated without 6 mana"


def test_invent_resolution_tutors_instant_and_sorcery():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(U=3, C=4), cards)

    assert "Invert / Invent" in state.hand

    actions = generate_actions(state)
    invent_action = next(a for a in actions if a.source_card == "Invert / Invent"
                         and a.alt_cost_type == "invent_face")

    # Cast Invent face → stack: [Invent, draw_trigger]
    resolve_action(state, invent_action)
    assert state.noncreature_spells_cast == 1

    # Resolve draw trigger first (it sits above Invent on the stack)
    from mtg_sim.sim.actions import RESOLVE_STACK_OBJECT, CHOOSE_TUTOR
    resolve_actions = generate_actions(state)
    dt_act = next(a for a in resolve_actions if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, dt_act)

    # Resolve Invent → pushes two PendingChoice objects (instant then sorcery)
    resolve_actions = generate_actions(state)
    resolve_act = next(a for a in resolve_actions if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, resolve_act)

    # Resolve first pending tutor choice (instant)
    tutor_actions = generate_actions(state)
    assert any(a.action_type == CHOOSE_TUTOR for a in tutor_actions), \
        "Should have pending CHOOSE_TUTOR for instant"
    tutor_act = next(a for a in tutor_actions if a.action_type == CHOOSE_TUTOR)
    resolve_action(state, tutor_act)

    # Resolve second pending tutor choice (sorcery)
    tutor_actions2 = generate_actions(state)
    assert any(a.action_type == CHOOSE_TUTOR for a in tutor_actions2), \
        "Should have second pending CHOOSE_TUTOR for sorcery"
    tutor_act2 = next(a for a in tutor_actions2 if a.action_type == CHOOSE_TUTOR)
    resolve_action(state, tutor_act2)

    # Verify at least one card was tutored to hand
    all_tutor_notes = [n for entry in state.trace for n in entry.notes if "Tutored" in n]
    assert len(all_tutor_notes) >= 1, f"Expected tutored notes, got trace notes: {[n for e in state.trace for n in e.notes]}"


def test_invert_resolution_is_noop():
    cards = _load()
    state = _state_with_hand(["Invert / Invent"], ManaPool(U=1), cards)

    actions = generate_actions(state)
    invert_action = next(a for a in actions if a.source_card == "Invert / Invent"
                         and a.alt_cost_type != "invent_face")

    spells_before = state.noncreature_spells_cast
    resolve_action(state, invert_action)
    # Stack: [Invert, draw_trigger]; resolve draw trigger first
    from mtg_sim.sim.actions import RESOLVE_STACK_OBJECT
    resolve_actions = generate_actions(state)
    dt_act = next(a for a in resolve_actions if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, dt_act)
    # Now resolve Invert
    resolve_actions = generate_actions(state)
    resolve_act = next(a for a in resolve_actions if a.action_type == RESOLVE_STACK_OBJECT)
    hand_before_resolve = len(state.hand)
    resolve_action(state, resolve_act)

    # Invert has no resolution effect — hand size unchanged (no tutor)
    assert len(state.hand) == hand_before_resolve
    # Card went to graveyard
    assert "Invert / Invent" in state.graveyard


def test_both_faces_trigger_curiosity_draw():
    cards = _load()

    # Invert face
    state = _state_with_hand(["Invert / Invent"], ManaPool(U=1), cards)
    spells_before = state.noncreature_spells_cast
    actions = generate_actions(state)
    invert_action = next(a for a in actions if a.source_card == "Invert / Invent"
                         and a.alt_cost_type != "invent_face")
    resolve_action(state, invert_action)
    assert state.noncreature_spells_cast == spells_before + 1

    # Invent face
    state2 = _state_with_hand(["Invert / Invent"], ManaPool(U=3, C=4), cards)
    spells_before2 = state2.noncreature_spells_cast
    actions2 = generate_actions(state2)
    invent_action = next(a for a in actions2 if a.source_card == "Invert / Invent"
                         and a.alt_cost_type == "invent_face")
    resolve_action(state2, invent_action)
    assert state2.noncreature_spells_cast == spells_before2 + 1
