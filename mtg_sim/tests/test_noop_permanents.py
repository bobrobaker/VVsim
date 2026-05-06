"""Tests for Generic No-Op Permanents bucket: Mystic Remora, Rhystic Study."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from random import Random
from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.actions import CAST_SPELL, RESOLVE_STACK_OBJECT


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def _make_state(hand, mana):
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=mana)
    state = _build_initial_state(cfg, cards, Random(1))
    draw_cards(state, 5)
    return state


def _cast(state, card_name):
    actions = generate_actions(state)
    cast = next(a for a in actions if a.action_type == CAST_SPELL and a.source_card == card_name)
    resolve_action(state, cast)
    return cast


# ── Bucket-level tests ────────────────────────────────────────────────────────

NOOP_PERMANENTS = [
    ("Mystic Remora", ManaPool(U=1)),
    ("Rhystic Study", ManaPool(U=3)),
]


def test_cast_action_generated(monkeypatch):
    """Default cast action is generated when mana is available."""
    for card_name, mana in NOOP_PERMANENTS:
        state = _make_state([card_name], mana)
        actions = generate_actions(state)
        cast_actions = [a for a in actions if a.action_type == CAST_SPELL and a.source_card == card_name]
        assert cast_actions, f"No cast action generated for {card_name}"


def test_cast_not_generated_without_mana():
    """No cast action generated when mana is insufficient."""
    for card_name, _ in NOOP_PERMANENTS:
        state = _make_state([card_name], ManaPool())
        actions = generate_actions(state)
        cast_actions = [a for a in actions if a.action_type == CAST_SPELL and a.source_card == card_name]
        assert not cast_actions, f"Cast action generated without mana for {card_name}"


def test_cast_triggers_curiosity_draw():
    """Casting a noop permanent creates a Vivi/Curiosity draw trigger."""
    for card_name, mana in NOOP_PERMANENTS:
        state = _make_state([card_name], mana)
        hand_before = len(state.hand)
        _cast(state, card_name)
        assert state.noncreature_spells_cast == 1
        assert state.stack, f"Stack empty after casting {card_name}"
        # Top of stack: the card itself, with draw trigger above it
        draw_triggers = [o for o in state.stack if o.is_draw_trigger]
        assert draw_triggers, f"No draw trigger on stack after casting {card_name}"


def test_resolution_enters_battlefield():
    """After cast and stack resolution, card is on the battlefield."""
    for card_name, mana in NOOP_PERMANENTS:
        state = _make_state([card_name], mana)
        _cast(state, card_name)
        # Resolve all stack objects
        while state.stack:
            acts = generate_actions(state)
            resolve_acts = [a for a in acts if a.action_type == RESOLVE_STACK_OBJECT]
            assert resolve_acts, f"No resolve actions for {card_name} stack"
            resolve_action(state, resolve_acts[0])
        perm_names = [p.card_name for p in state.battlefield]
        assert card_name in perm_names, f"{card_name} not on battlefield after resolution"


def test_no_extra_draw_beyond_curiosity():
    """Resolving a noop permanent does not draw extra cards beyond normal Curiosity trigger."""
    for card_name, mana in NOOP_PERMANENTS:
        state = _make_state([card_name], mana)
        hand_before = len(state.hand)
        _cast(state, card_name)
        hand_after_cast = len(state.hand)
        assert hand_after_cast == hand_before - 1  # card left hand, no draws yet

        # Resolve all stack objects
        while state.stack:
            acts = generate_actions(state)
            resolve_acts = [a for a in acts if a.action_type == RESOLVE_STACK_OBJECT]
            resolve_action(state, resolve_acts[0])

        # Only draws from the Curiosity trigger (3 draws for noncreature with Vivi+Curiosity)
        expected_hand = hand_before - 1 + 3
        assert len(state.hand) == expected_hand, (
            f"{card_name}: expected {expected_hand} cards, got {len(state.hand)}"
        )
