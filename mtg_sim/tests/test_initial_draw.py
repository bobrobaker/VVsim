import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run, _build_initial_state
from mtg_sim.sim.resolver import draw_cards
from random import Random


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def test_initial_draw_three():
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=[], starting_floating_mana=ManaPool(U=1))
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    assert len(state.hand) == 0
    drawn = draw_cards(state, 3)
    assert len(drawn) == 3
    assert len(state.hand) == 3


def test_initial_draw_with_two_curiosity():
    cards = _load()
    cfg = RunConfig(seed=2, starting_hand=[], starting_floating_mana=ManaPool(U=1),
                    curiosity_effect_count=2)
    rng = Random(2)
    state = _build_initial_state(cfg, cards, rng)
    drawn = draw_cards(state, state.cards_drawn_per_noncreature_spell)
    assert len(drawn) == 6


def test_library_minus_hand():
    cards = _load()
    hand = ["Sol Ring", "Lotus Petal"]
    cfg = RunConfig(seed=3, starting_hand=hand, starting_floating_mana=ManaPool(U=1))
    rng = Random(3)
    state = _build_initial_state(cfg, cards, rng)
    assert "Sol Ring" not in state.library
    assert "Lotus Petal" not in state.library
    assert "Vivi Ornitier" not in state.library
    assert len(state.hand) == 2


def test_default_starting_battlefield():
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=[], starting_floating_mana=ManaPool(U=1))
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    bf_names = [p.card_name for p in state.battlefield]
    assert "Volcanic Island" in bf_names
    assert "Vivi Ornitier" in bf_names
    assert "Volcanic Island" not in state.library
    assert state.land_play_available is False


def test_custom_starting_battlefield():
    cards = _load()
    cfg = RunConfig(
        seed=1,
        starting_hand=[],
        starting_floating_mana=ManaPool(U=1),
        starting_battlefield=["Island"],
        land_play_available=True,
    )
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    bf_names = [p.card_name for p in state.battlefield]
    assert "Island" in bf_names
    assert "Volcanic Island" not in bf_names
    assert "Island" not in state.library
    assert state.land_play_available is True


def test_validate_state_catches_duplicate():
    from mtg_sim.sim.state import validate_state
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=[], starting_floating_mana=ManaPool(U=1))
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    # Manually corrupt state: put Sol Ring in both hand and library
    state.hand.append("Sol Ring")
    state.library.insert(0, "Sol Ring")
    try:
        validate_state(state)
        assert False, "Expected AssertionError"
    except AssertionError as e:
        assert "Sol Ring" in str(e)
