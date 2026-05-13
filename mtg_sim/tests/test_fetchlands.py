"""Tests for fetchland bucket (lines 49-102 of docs/specs/card_specifics.md)."""
import pytest
from pathlib import Path
from mtg_sim.sim.cards import load_card_library
from mtg_sim.sim.state import GameState, Permanent
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action
from mtg_sim.sim.actions import FETCH_LAND

_DATA_DIR = Path(__file__).parent.parent.parent
load_card_library(str(_DATA_DIR / "card_library.csv"))


def _make_state(**kwargs) -> GameState:
    defaults = dict(hand=[], library=[], battlefield=[], graveyard=[])
    defaults.update(kwargs)
    return GameState(**defaults)


def _fetchland_perm(name: str) -> Permanent:
    p = Permanent(card_name=name)
    p.counters["fetchable"] = 1
    return p


def _fetch_actions(state):
    return [a for a in generate_actions(state) if a.action_type == FETCH_LAND]


# ── Priority / target selection ───────────────────────────────────────────────

def test_island_fetchland_prefers_volcanic_island():
    perm = _fetchland_perm("Scalding Tarn")
    state = _make_state(
        battlefield=[perm],
        library=["Volcanic Island", "Steam Vents", "Island"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    assert actions[0].effects.fetch_target_card == "Volcanic Island"


def test_island_fetchland_falls_back_to_steam_vents():
    perm = _fetchland_perm("Flooded Strand")
    state = _make_state(
        battlefield=[perm],
        library=["Steam Vents", "Island"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    assert actions[0].effects.fetch_target_card == "Steam Vents"


def test_island_fetchland_falls_back_to_basic_island():
    perm = _fetchland_perm("Misty Rainforest")
    state = _make_state(
        battlefield=[perm],
        library=["Island"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    assert actions[0].effects.fetch_target_card == "Island"


def test_mountain_fetchland_prefers_volcanic_island():
    perm = _fetchland_perm("Arid Mesa")
    state = _make_state(
        battlefield=[perm],
        library=["Volcanic Island", "Mountain"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    assert actions[0].effects.fetch_target_card == "Volcanic Island"


def test_mountain_fetchland_falls_back_to_basic_mountain():
    perm = _fetchland_perm("Wooded Foothills")
    state = _make_state(
        battlefield=[perm],
        library=["Mountain"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    assert actions[0].effects.fetch_target_card == "Mountain"


# ── Scalding Tarn: flex behavior (island or mountain) ────────────────────────

def test_scalding_tarn_offers_both_basics_when_no_dual():
    perm = _fetchland_perm("Scalding Tarn")
    state = _make_state(
        battlefield=[perm],
        library=["Island", "Mountain"],
    )
    actions = _fetch_actions(state)
    targets = {a.effects.fetch_target_card for a in actions}
    assert targets == {"Island", "Mountain"}


def test_scalding_tarn_picks_volcanic_island_over_basics():
    perm = _fetchland_perm("Scalding Tarn")
    state = _make_state(
        battlefield=[perm],
        library=["Volcanic Island", "Island", "Mountain"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    assert actions[0].effects.fetch_target_card == "Volcanic Island"


# ── Prismatic Vista: basics only ─────────────────────────────────────────────

def test_prismatic_vista_offers_both_basics():
    perm = _fetchland_perm("Prismatic Vista")
    state = _make_state(
        battlefield=[perm],
        library=["Island", "Mountain"],
    )
    actions = _fetch_actions(state)
    targets = {a.effects.fetch_target_card for a in actions}
    assert targets == {"Island", "Mountain"}


def test_prismatic_vista_only_available_basic():
    perm = _fetchland_perm("Prismatic Vista")
    state = _make_state(
        battlefield=[perm],
        library=["Island"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    assert actions[0].effects.fetch_target_card == "Island"


# ── No target → no action ─────────────────────────────────────────────────────

def test_no_action_when_no_valid_target():
    perm = _fetchland_perm("Scalding Tarn")
    state = _make_state(battlefield=[perm], library=[])
    assert _fetch_actions(state) == []


def test_no_action_when_only_wrong_land_type():
    # Flooded Strand can't fetch Mountain
    perm = _fetchland_perm("Flooded Strand")
    state = _make_state(battlefield=[perm], library=["Mountain"])
    assert _fetch_actions(state) == []


# ── Resolution: sacrifice + battlefield placement ─────────────────────────────

def test_resolution_sacrifices_fetchland_puts_land_on_battlefield():
    perm = _fetchland_perm("Scalding Tarn")
    state = _make_state(
        battlefield=[perm],
        library=["Volcanic Island"],
    )
    actions = _fetch_actions(state)
    assert len(actions) == 1
    resolve_action(state, actions[0])

    # fetchland is gone from battlefield
    assert not any(p.card_name == "Scalding Tarn" for p in state.battlefield)
    # fetchland is in graveyard
    assert "Scalding Tarn" in state.graveyard
    # target removed from library
    assert "Volcanic Island" not in state.library
    # target is on battlefield
    assert any(p.card_name == "Volcanic Island" for p in state.battlefield)


def test_resolution_enters_untapped():
    perm = _fetchland_perm("Flooded Strand")
    state = _make_state(battlefield=[perm], library=["Volcanic Island"])
    actions = _fetch_actions(state)
    resolve_action(state, actions[0])
    vol = next(p for p in state.battlefield if p.card_name == "Volcanic Island")
    assert not vol.tapped


def test_cannot_reuse_after_sacrifice():
    perm = _fetchland_perm("Scalding Tarn")
    state = _make_state(
        battlefield=[perm],
        library=["Volcanic Island", "Island"],
    )
    actions = _fetch_actions(state)
    resolve_action(state, actions[0])
    # after sacrifice no fetch actions remain
    assert _fetch_actions(state) == []
