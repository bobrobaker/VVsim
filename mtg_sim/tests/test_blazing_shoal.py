"""Tests for Blazing Shoal free pitch (alt_x:pitch_red_mv)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.actions import CAST_SPELL
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


def test_blazing_shoal_castable_by_pitching_red_card():
    cards = _load()
    # Rite of Flame is a red card (pip_r=1) that can be pitched
    state = _state_with_hand(["Blazing Shoal", "Rite of Flame"], ManaPool(), cards)
    actions = generate_actions(state)
    shoal_acts = [a for a in actions if a.source_card == "Blazing Shoal"
                  and a.action_type == CAST_SPELL
                  and a.alt_cost_type == "pitch_red_x"]
    assert len(shoal_acts) >= 1, "Blazing Shoal should be castable by pitching a red card"


def test_blazing_shoal_x_equals_pitched_card_mv():
    cards = _load()
    # Rite of Flame has MV=1; pitching it should give X=1
    state = _state_with_hand(["Blazing Shoal", "Rite of Flame"], ManaPool(), cards)
    actions = generate_actions(state)
    shoal_acts = [a for a in actions if a.source_card == "Blazing Shoal"
                  and a.action_type == CAST_SPELL
                  and a.alt_cost_type == "pitch_red_x"
                  and a.costs.pitched_card == "Rite of Flame"]
    assert len(shoal_acts) >= 1
    assert shoal_acts[0].x_value == 1, "X should equal pitched card's MV (Rite of Flame MV=1)"


def test_blazing_shoal_not_castable_without_red_card():
    cards = _load()
    state = _state_with_hand(["Blazing Shoal"], ManaPool(), cards)
    actions = generate_actions(state)
    shoal_free_acts = [a for a in actions if a.source_card == "Blazing Shoal"
                       and a.action_type == CAST_SPELL
                       and a.alt_cost_type == "pitch_red_x"]
    assert len(shoal_free_acts) == 0, "Blazing Shoal should not be castable for free without a red card to pitch"


def test_blazing_shoal_triggers_curiosity_draw():
    cards = _load()
    state = _state_with_hand(["Blazing Shoal", "Rite of Flame"], ManaPool(), cards)
    spells_before = state.noncreature_spells_cast

    actions = generate_actions(state)
    shoal_act = next(a for a in actions if a.source_card == "Blazing Shoal"
                     and a.alt_cost_type == "pitch_red_x")
    resolve_action(state, shoal_act)

    assert state.noncreature_spells_cast == spells_before + 1, \
        "Blazing Shoal (free cast) should increment noncreature_spells_cast (Curiosity draw)"


def test_blazing_shoal_removes_pitch_from_hand():
    cards = _load()
    state = _state_with_hand(["Blazing Shoal", "Rite of Flame"], ManaPool(), cards)

    actions = generate_actions(state)
    shoal_act = next(a for a in actions if a.source_card == "Blazing Shoal"
                     and a.alt_cost_type == "pitch_red_x"
                     and a.costs.pitched_card == "Rite of Flame")
    resolve_action(state, shoal_act)

    assert "Rite of Flame" not in state.hand, "Pitched card should be removed from hand"
    assert "Rite of Flame" in state.exile, "Pitched card should go to exile"
