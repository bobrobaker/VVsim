import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_cards, load_decklist
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run, _build_initial_state
from mtg_sim.sim.resolver import draw_cards
from random import Random


def _load():
    load_cards(str(DATA_DIR / "mtg_sim_card_data_v1.csv"))
    return load_decklist(str(DATA_DIR / "testdecklist.txt"))


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
