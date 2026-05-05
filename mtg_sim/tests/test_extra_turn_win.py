import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run
from mtg_sim.sim.actions import WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def test_final_fortune_in_hand_with_rr_wins():
    cards = _load()
    # Start with Final Fortune in hand and enough R to cast it
    cfg = RunConfig(
        seed=99,
        starting_hand=["Final Fortune"],
        starting_floating_mana=ManaPool(R=2),
    )
    result = simulate_run(cfg, cards)
    assert result.outcome == WIN_EXTRA_TURN
    assert "Final Fortune" in result.winning_card


def test_warriors_oath_wins():
    cards = _load()
    cfg = RunConfig(
        seed=99,
        starting_hand=["Warrior's Oath"],
        starting_floating_mana=ManaPool(R=2),
    )
    result = simulate_run(cfg, cards)
    assert result.outcome == WIN_EXTRA_TURN
