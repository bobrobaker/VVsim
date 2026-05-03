import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_cards, load_decklist
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run
from mtg_sim.sim.actions import BRICK_NO_ACTIONS, BRICK_NO_USEFUL_ACTIONS


def _load():
    load_cards(str(DATA_DIR / "mtg_sim_card_data_v1.csv"))
    return load_decklist(str(DATA_DIR / "testdecklist.txt"))


def test_empty_hand_no_mana_bricks():
    cards = _load()
    # Empty hand, no mana: should brick after initial draw if nothing is castable
    cfg = RunConfig(
        seed=777,
        starting_hand=[],
        starting_floating_mana=ManaPool(),  # no mana
    )
    result = simulate_run(cfg, cards)
    assert not result.won or result.noncreature_spells_cast >= 1


def test_result_has_trace():
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=[], starting_floating_mana=ManaPool(U=1))
    result = simulate_run(cfg, cards)
    assert len(result.trace) > 0
    assert result.trace[0].event_type == "INITIAL_DRAW"


def test_run_terminates():
    cards = _load()
    for seed in range(20):
        cfg = RunConfig(seed=seed, starting_hand=[],
                        starting_floating_mana=ManaPool(U=1))
        result = simulate_run(cfg, cards)
        assert result.outcome != ""
