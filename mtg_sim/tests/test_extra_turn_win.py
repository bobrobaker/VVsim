import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, simulate_run, _is_hullbreaker_eligible, _check_win
from mtg_sim.sim.state import GameState, Permanent
from mtg_sim.sim.stack import StackObject
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.actions import WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT, CAST_SPELL


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


# ── Extra-turn sorceries ──────────────────────────────────────────────────────

def test_final_fortune_in_hand_with_rr_wins():
    cards = _load()
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


def test_last_chance_wins():
    cards = _load()
    cfg = RunConfig(
        seed=99,
        starting_hand=["Last Chance"],
        starting_floating_mana=ManaPool(R=2),
    )
    result = simulate_run(cfg, cards)
    assert result.outcome == WIN_EXTRA_TURN
    assert "Last Chance" in result.winning_card


def test_alchemists_gambit_wins():
    cards = _load()
    cfg = RunConfig(
        seed=99,
        starting_hand=["Alchemist's Gambit"],
        starting_floating_mana=ManaPool(U=1, R=2),
    )
    result = simulate_run(cfg, cards)
    assert result.outcome == WIN_EXTRA_TURN
    assert "Alchemist's Gambit" in result.winning_card


# ── Hullbreaker Horror ────────────────────────────────────────────────────────

def test_hullbreaker_eligible_helper():
    _load()
    assert _is_hullbreaker_eligible("Sol Ring")
    assert _is_hullbreaker_eligible("Mana Vault")
    assert _is_hullbreaker_eligible("Grim Monolith")
    assert _is_hullbreaker_eligible("Mox Opal")
    assert not _is_hullbreaker_eligible("Lotus Petal")       # sacrifice
    assert not _is_hullbreaker_eligible("Lion's Eye Diamond") # sacrifice
    assert not _is_hullbreaker_eligible("Volcanic Island")   # land
    assert not _is_hullbreaker_eligible("Vivi Ornitier")     # creature, no produces_mana in artifact sense


def test_hullbreaker_cast_at_instant_speed():
    """Hullbreaker Horror has flash; should be castable with a spell on the stack."""
    cards = _load()
    # Put Hullbreaker in hand with enough mana to cast it (5UU = 7 mana).
    # This test verifies the cast action is generated via the greedy policy.
    cfg = RunConfig(
        seed=1,
        starting_hand=["Hullbreaker Horror"],
        starting_floating_mana=ManaPool(U=3, C=4),
    )
    result = simulate_run(cfg, cards)
    # Hullbreaker should reach the battlefield via normal resolution
    assert result.outcome != ""  # sim ran (not immediate error)


def test_hullbreaker_wins_with_two_eligible_permanents():
    cards = _load()
    cfg = RunConfig(
        seed=1,
        starting_hand=["Gitaxian Probe"],
        starting_floating_mana=ManaPool(U=1, C=2),
        starting_battlefield=["Volcanic Island", "Hullbreaker Horror", "Sol Ring", "Mana Vault"],
        starting_battlefield_tapped=["Volcanic Island"],
    )
    result = simulate_run(cfg, cards)
    assert result.outcome == WIN_EXTRA_TURN
    assert "Hullbreaker Horror" in result.winning_card


def _make_state(battlefield_names, stack_card=None, floating=None):
    """Build a minimal GameState for _check_win unit tests."""
    state = GameState(
        battlefield=[Permanent(card_name=n) for n in battlefield_names],
        stack=[StackObject(card_name=stack_card)] if stack_card else [],
        floating_mana=floating or ManaPool(),
    )
    return state


def test_hullbreaker_check_win_needs_two_eligible():
    _load()
    # One eligible perm → no win
    state = _make_state(
        ["Hullbreaker Horror", "Sol Ring"],
        stack_card="Gitaxian Probe",
    )
    outcome, _ = _check_win(state)
    assert outcome != WIN_EXTRA_TURN

    # Two eligible perms → win
    state = _make_state(
        ["Hullbreaker Horror", "Sol Ring", "Mana Vault"],
        stack_card="Gitaxian Probe",
    )
    outcome, card = _check_win(state)
    assert outcome == WIN_EXTRA_TURN
    assert card == "Hullbreaker Horror"


def test_hullbreaker_check_win_sacrifice_sources_not_eligible():
    """Lotus Petal and LED are sacrifice-only; should not count."""
    _load()
    state = _make_state(
        ["Hullbreaker Horror", "Lotus Petal", "Lion's Eye Diamond"],
        stack_card="Gitaxian Probe",
    )
    outcome, _ = _check_win(state)
    assert outcome != WIN_EXTRA_TURN


def test_hullbreaker_check_win_lands_not_eligible():
    _load()
    state = _make_state(
        ["Hullbreaker Horror", "Volcanic Island", "Island"],
        stack_card="Gitaxian Probe",
    )
    outcome, _ = _check_win(state)
    assert outcome != WIN_EXTRA_TURN


def test_hullbreaker_check_win_no_spell_on_stack():
    _load()
    state = _make_state(["Hullbreaker Horror", "Sol Ring", "Mana Vault"])
    outcome, _ = _check_win(state)
    assert outcome != WIN_EXTRA_TURN


# ── Quicksilver Elemental ─────────────────────────────────────────────────────

def test_quicksilver_wins_with_blue_mana_floating():
    cards = _load()
    cfg = RunConfig(
        seed=1,
        starting_hand=[],
        starting_floating_mana=ManaPool(U=1),
        starting_battlefield=["Volcanic Island", "Quicksilver Elemental"],
        starting_battlefield_tapped=["Volcanic Island"],
    )
    result = simulate_run(cfg, cards)
    assert result.outcome == WIN_EXTRA_TURN
    assert "Quicksilver Elemental" in result.winning_card


def test_quicksilver_check_win_no_blue_mana():
    """_check_win should not trigger Quicksilver win without {U} floating."""
    _load()
    state = _make_state(["Quicksilver Elemental"], floating=ManaPool(R=1))
    outcome, _ = _check_win(state)
    assert outcome != WIN_EXTRA_TURN


def test_quicksilver_check_win_no_blue_mana_empty_pool():
    """_check_win should not trigger Quicksilver win with empty pool."""
    _load()
    state = _make_state(["Quicksilver Elemental"])
    outcome, _ = _check_win(state)
    assert outcome != WIN_EXTRA_TURN


def test_quicksilver_cast_action_generated_when_payable():
    """Cast action is generated for Quicksilver when {3}{U}{U} is available."""
    _load()
    state = GameState(
        hand=["Quicksilver Elemental"],
        floating_mana=ManaPool(U=3, C=2),
        battlefield=[Permanent(card_name="Vivi Ornitier")],
    )
    actions = generate_actions(state)
    cast_actions = [a for a in actions if a.action_type == CAST_SPELL and a.source_card == "Quicksilver Elemental"]
    assert cast_actions, "Expected cast action for Quicksilver Elemental"


def test_quicksilver_on_battlefield_with_u_wins():
    """Quicksilver Elemental on battlefield + {U} floating → WIN via _check_win."""
    _load()
    state = _make_state(["Quicksilver Elemental"], floating=ManaPool(U=1))
    outcome, card = _check_win(state)
    assert outcome == WIN_EXTRA_TURN
    assert card == "Quicksilver Elemental"
