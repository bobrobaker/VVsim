import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run, _build_initial_state
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.state import ActionLog
from mtg_sim.sim.actions import Action, CostBundle, ManaCost, CAST_SPELL, RESOLVE_STACK_OBJECT, RISK_SAFE
from random import Random


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def test_cast_free_noncreature_draws_three():
    cards = _load()
    hand = ["Lotus Petal", "Gitaxian Probe"]
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=ManaPool(U=1))
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    # Fill library so we can draw
    draw_cards(state, 3)  # initial curiosity

    hand_before = len(state.hand)
    action = Action(
        action_type=CAST_SPELL,
        source_card="Gitaxian Probe",
        description="Cast Gitaxian Probe (free)",
        costs=CostBundle(),
        risk_level=RISK_SAFE,
        alt_cost_type="pay_life",
    )
    resolve_action(state, action)

    # Gitaxian Probe is noncreature → draw trigger placed above it on the stack
    assert state.noncreature_spells_cast == 1
    assert len(state.hand) == hand_before - 1  # probe removed, no draws yet
    assert state.stack[-1].is_draw_trigger
    assert state.stack[-1].draw_count == 3
    assert state.pending_curiosity_draws == 3  # derived from stack

    # Resolving the draw trigger delivers the cards
    draw_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, draw_act)
    assert state.pending_curiosity_draws == 0
    assert len(state.hand) == hand_before - 1 + 3


def test_cast_increments_spell_count():
    cards = _load()
    hand = ["Lotus Petal"]
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=ManaPool())
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    draw_cards(state, 3)

    action = Action(
        action_type=CAST_SPELL,
        source_card="Lotus Petal",
        description="Cast Lotus Petal",
        costs=CostBundle(),
        risk_level=RISK_SAFE,
    )
    resolve_action(state, action)
    assert state.noncreature_spells_cast == 1
    assert state.total_spells_cast == 1
    # Lotus Petal goes to stack
    assert any(o.card_name == "Lotus Petal" for o in state.stack)
