"""Tests for timing rules: sorcery-speed restriction and LIFO stack resolution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool, ManaCost
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.actions import CAST_SPELL, RESOLVE_STACK_OBJECT
from mtg_sim.sim.stack import StackObject
from random import Random


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def _state_with_hand(hand, mana, cards):
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=mana)
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    draw_cards(state, 3)
    return state


# ── Sorcery-speed restriction ─────────────────────────────────────────────────

def test_sorcery_not_castable_while_stack_nonempty():
    cards = _load()
    # Gamble is a Sorcery that costs {R}
    state = _state_with_hand(["Gamble"], ManaPool(R=1), cards)
    state.stack.append(StackObject(card_name="Lotus Petal"))

    actions = generate_actions(state)
    cast_actions = [a for a in actions if a.action_type == CAST_SPELL
                    and a.source_card == "Gamble"]
    assert len(cast_actions) == 0, "Sorcery must not be castable while stack is non-empty"


def test_sorcery_castable_with_empty_stack():
    cards = _load()
    state = _state_with_hand(["Gamble"], ManaPool(R=1), cards)
    assert not state.stack

    actions = generate_actions(state)
    cast_actions = [a for a in actions if a.action_type == CAST_SPELL
                    and a.source_card == "Gamble"]
    assert len(cast_actions) >= 1, "Sorcery must be castable with empty stack"


def test_instant_castable_while_stack_nonempty():
    cards = _load()
    # Mystical Tutor is an Instant that costs {U}
    state = _state_with_hand(["Mystical Tutor"], ManaPool(U=1), cards)
    state.stack.append(StackObject(card_name="Lotus Petal"))

    actions = generate_actions(state)
    cast_actions = [a for a in actions if a.action_type == CAST_SPELL
                    and a.source_card == "Mystical Tutor"]
    assert len(cast_actions) >= 1, "Instant must be castable while stack is non-empty"


def test_flash_card_castable_while_stack_nonempty():
    cards = _load()
    # Ophidian Eye has flash
    state = _state_with_hand(["Ophidian Eye"], ManaPool(U=3), cards)
    state.stack.append(StackObject(card_name="Lotus Petal"))

    actions = generate_actions(state)
    cast_actions = [a for a in actions if a.action_type == CAST_SPELL
                    and a.source_card == "Ophidian Eye"]
    assert len(cast_actions) >= 1, "Flash card must be castable while stack is non-empty"


# ── LIFO stack resolution ──────────────────────────────────────────────────────

def test_only_top_of_stack_resolvable():
    cards = _load()
    state = _state_with_hand([], ManaPool(), cards)
    state.stack.append(StackObject(card_name="Brainstorm"))
    state.stack.append(StackObject(card_name="Ponder"))

    actions = generate_actions(state)
    resolve_actions = [a for a in actions if a.action_type == RESOLVE_STACK_OBJECT]

    assert len(resolve_actions) == 1, "Only one stack object should be resolvable at a time (LIFO)"
    assert resolve_actions[0].source_card == "Ponder", "Top of stack (most recently pushed) must resolve first"


def test_single_stack_object_is_resolvable():
    cards = _load()
    state = _state_with_hand([], ManaPool(), cards)
    state.stack.append(StackObject(card_name="Brainstorm"))

    actions = generate_actions(state)
    resolve_actions = [a for a in actions if a.action_type == RESOLVE_STACK_OBJECT]

    assert len(resolve_actions) == 1
    assert resolve_actions[0].source_card == "Brainstorm"


def test_empty_stack_no_resolve_actions():
    cards = _load()
    state = _state_with_hand([], ManaPool(), cards)
    assert not state.stack

    actions = generate_actions(state)
    resolve_actions = [a for a in actions if a.action_type == RESOLVE_STACK_OBJECT]
    assert len(resolve_actions) == 0
