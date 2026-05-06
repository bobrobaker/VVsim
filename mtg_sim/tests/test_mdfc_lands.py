"""Tests for MDFC Lands bucket (lines 103–146 of docs/card_specifics.md)."""
import pytest
from pathlib import Path
from mtg_sim.sim.cards import load_card_library
from mtg_sim.sim.state import GameState, Permanent
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.actions import (
    PLAY_LAND, CAST_SPELL, ACTIVATE_MANA_ABILITY, RESOLVE_STACK_OBJECT,
    CHOOSE_GRAVEYARD_RETURN,
)

_DATA_DIR = Path(__file__).parent.parent.parent
load_card_library(str(_DATA_DIR / "card_library.csv"))


def _make_state(**kwargs) -> GameState:
    defaults = dict(hand=[], library=[], battlefield=[], graveyard=[])
    defaults.update(kwargs)
    return GameState(**defaults)


# ── Bucket: land face plays untapped and taps for correct color ───────────────

@pytest.mark.parametrize("card_name,expected_color", [
    ("Hydroelectric Specimen / Hydroelectric Laboratory", "U"),
    ("Pinnacle Monk / Mystic Peak", "R"),
    ("Sea Gate Restoration / Sea Gate, Reborn", "U"),
    ("Shatterskull Smashing / Shatterskull, the Hammer Pass", "R"),
    ("Sink into Stupor / Soporific Springs", "U"),
    ("Sundering Eruption / Volcanic Fissure", "R"),
])
def test_mdfc_land_play_action_generated(card_name, expected_color):
    state = _make_state(hand=[card_name], land_play_available=True)
    actions = [a for a in generate_actions(state) if a.action_type == PLAY_LAND]
    assert len(actions) == 1
    assert card_name in actions[0].description


@pytest.mark.parametrize("card_name,expected_color", [
    ("Hydroelectric Specimen / Hydroelectric Laboratory", "U"),
    ("Pinnacle Monk / Mystic Peak", "R"),
    ("Sea Gate Restoration / Sea Gate, Reborn", "U"),
    ("Shatterskull Smashing / Shatterskull, the Hammer Pass", "R"),
    ("Sink into Stupor / Soporific Springs", "U"),
    ("Sundering Eruption / Volcanic Fissure", "R"),
])
def test_mdfc_land_enters_untapped(card_name, expected_color):
    state = _make_state(hand=[card_name], land_play_available=True)
    land_actions = [a for a in generate_actions(state) if a.action_type == PLAY_LAND]
    resolve_action(state, land_actions[0])
    assert len(state.battlefield) == 1
    assert state.battlefield[0].card_name == card_name
    assert not state.battlefield[0].tapped


@pytest.mark.parametrize("card_name,expected_color", [
    ("Hydroelectric Specimen / Hydroelectric Laboratory", "U"),
    ("Pinnacle Monk / Mystic Peak", "R"),
    ("Sea Gate Restoration / Sea Gate, Reborn", "U"),
    ("Shatterskull Smashing / Shatterskull, the Hammer Pass", "R"),
    ("Sink into Stupor / Soporific Springs", "U"),
    ("Sundering Eruption / Volcanic Fissure", "R"),
])
def test_mdfc_land_taps_for_correct_color(card_name, expected_color):
    perm = Permanent(card_name=card_name)
    state = _make_state(battlefield=[perm])
    mana_actions = [a for a in generate_actions(state) if a.action_type == ACTIVATE_MANA_ABILITY
                    and a.source_card == card_name]
    assert len(mana_actions) == 1
    assert getattr(mana_actions[0].effects.add_mana, expected_color, 0) == 1


def test_mdfc_no_land_play_without_land_drop():
    state = _make_state(
        hand=["Hydroelectric Specimen / Hydroelectric Laboratory"],
        land_play_available=False,
    )
    land_actions = [a for a in generate_actions(state) if a.action_type == PLAY_LAND]
    assert len(land_actions) == 0


# ── Hydroelectric Specimen / Hydroelectric Laboratory ────────────────────────

def test_hydro_specimen_etb_pushes_stack_object():
    """Creature ETB creates a stack object that can be targeted by Deflecting Swat."""
    state = _make_state(
        hand=["Hydroelectric Specimen / Hydroelectric Laboratory"],
        floating_mana=ManaPool(U=3),
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL]
    assert any("Hydroelectric Specimen" in a.description for a in cast_actions)
    # Resolve the cast
    cast_act = next(a for a in cast_actions if "Hydroelectric Specimen" in a.description
                    and "as land" not in a.description)
    resolve_action(state, cast_act)
    # Stack now has: the creature spell + draw trigger + ETB ability (after creature enters)
    # Resolve draw trigger first, then the ETB ability is on stack
    while state.stack and state.stack[-1].is_draw_trigger:
        res_act = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
        resolve_action(state, res_act[0])
    # Resolve the creature spell itself
    res_actions = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
    if res_actions:
        resolve_action(state, res_actions[0])
    # ETB ability should be on the stack
    etb_on_stack = [o for o in state.stack if "ETB" in o.card_name]
    assert len(etb_on_stack) == 1


def test_hydro_etb_resolves_cleanly():
    """ETB stack object resolves without error and without entering graveyard as a card."""
    from mtg_sim.sim.stack import StackObject
    state = _make_state()
    etb = StackObject(card_name="Hydroelectric Specimen ETB")
    state.stack.append(etb)
    res_actions = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
    resolve_action(state, res_actions[0])
    assert len(state.stack) == 0
    assert "Hydroelectric Specimen ETB" not in state.graveyard


# ── Pinnacle Monk / Mystic Peak ───────────────────────────────────────────────

def test_pinnacle_monk_etb_creates_pending_graveyard_choice():
    state = _make_state(
        hand=["Pinnacle Monk / Mystic Peak"],
        floating_mana=ManaPool(R=5),
        graveyard=["Brainstorm", "Ponder"],  # dummy instants for targets
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Pinnacle Monk" in a.description and "as land" not in a.description]
    resolve_action(state, cast_actions[0])
    # Drain stack (draw trigger + spell)
    while state.stack:
        res_acts = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
        if not res_acts:
            break
        resolve_action(state, res_acts[0])
    assert any(c.choice_type == "graveyard_return" for c in state.pending_choices)


def test_pinnacle_monk_graveyard_return_generates_choices():
    state = _make_state(graveyard=["Brainstorm"])
    from mtg_sim.sim.state import PendingChoice
    state.pending_choices.append(PendingChoice(
        choice_type="graveyard_return",
        tutor_filter="instant_sorcery",
        source_card="Pinnacle Monk / Mystic Peak",
    ))
    # Brainstorm is an instant — but we only have card_library loaded, so let's use a known card
    # Swap graveyard to a card we know is an instant in library
    state.graveyard = ["Gitaxian Probe"]
    actions = [a for a in generate_actions(state) if a.action_type == CHOOSE_GRAVEYARD_RETURN]
    assert len(actions) >= 1
    assert actions[0].source_card == "Gitaxian Probe"


def test_pinnacle_monk_graveyard_return_resolves_to_hand():
    state = _make_state(graveyard=["Gitaxian Probe"])
    from mtg_sim.sim.state import PendingChoice
    state.pending_choices.append(PendingChoice(
        choice_type="graveyard_return",
        tutor_filter="instant_sorcery",
        source_card="Pinnacle Monk / Mystic Peak",
    ))
    actions = [a for a in generate_actions(state) if a.action_type == CHOOSE_GRAVEYARD_RETURN]
    resolve_action(state, actions[0])
    assert "Gitaxian Probe" in state.hand
    assert "Gitaxian Probe" not in state.graveyard
    assert not state.pending_choices


def test_pinnacle_monk_no_graveyard_target_generates_skip():
    state = _make_state(graveyard=[])
    from mtg_sim.sim.state import PendingChoice
    state.pending_choices.append(PendingChoice(
        choice_type="graveyard_return",
        tutor_filter="instant_sorcery",
        source_card="Pinnacle Monk / Mystic Peak",
    ))
    actions = [a for a in generate_actions(state) if a.action_type == CHOOSE_GRAVEYARD_RETURN]
    assert len(actions) == 1
    assert actions[0].source_card is None


# ── Sea Gate Restoration / Sea Gate, Reborn ───────────────────────────────────

def test_sea_gate_restoration_draws_hand_size_plus_one():
    from mtg_sim.sim.stack import StackObject
    state = _make_state(
        hand=["Gitaxian Probe", "Rite of Flame"],  # 2 cards in hand
        library=["Island", "Mountain", "Sol Ring", "Lotus Petal"],
    )
    obj = StackObject(card_name="Sea Gate Restoration / Sea Gate, Reborn")
    state.stack.append(obj)
    res_act = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
    initial_hand_size = len(state.hand)  # 2
    resolve_action(state, res_act[0])
    expected_draws = initial_hand_size + 1  # 3
    assert len(state.hand) == initial_hand_size + expected_draws


def test_sea_gate_restoration_sorcery_speed_blocked_by_stack():
    from mtg_sim.sim.stack import StackObject
    state = _make_state(
        hand=["Sea Gate Restoration / Sea Gate, Reborn"],
        floating_mana=ManaPool(U=7),
        stack=[StackObject(card_name="Gitaxian Probe")],
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Sea Gate" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 0


# ── Shatterskull Smashing / Shatterskull, the Hammer Pass ────────────────────

def test_shatterskull_only_x0_generated():
    state = _make_state(
        hand=["Shatterskull Smashing / Shatterskull, the Hammer Pass"],
        floating_mana=ManaPool(R=10),
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Shatterskull" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 1
    assert cast_actions[0].x_value == 0


def test_shatterskull_sorcery_speed_blocked_by_stack():
    from mtg_sim.sim.stack import StackObject
    state = _make_state(
        hand=["Shatterskull Smashing / Shatterskull, the Hammer Pass"],
        floating_mana=ManaPool(R=10),
        stack=[StackObject(card_name="Gitaxian Probe")],
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Shatterskull" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 0


def test_shatterskull_not_generated_when_unaffordable():
    state = _make_state(
        hand=["Shatterskull Smashing / Shatterskull, the Hammer Pass"],
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Shatterskull" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 0


# ── Sink into Stupor / Soporific Springs ─────────────────────────────────────

def test_sink_into_stupor_requires_opponent_permanent():
    state = _make_state(
        hand=["Sink into Stupor / Soporific Springs"],
        floating_mana=ManaPool(U=3),
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Sink into Stupor" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 1
    assert "opponent" in cast_actions[0].description


def test_sink_into_stupor_not_generated_when_unaffordable():
    state = _make_state(
        hand=["Sink into Stupor / Soporific Springs"],
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Sink into Stupor" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 0


def test_sink_into_stupor_castable_with_stack():
    """Sink into Stupor is an instant and can be cast with a non-empty stack."""
    from mtg_sim.sim.stack import StackObject
    state = _make_state(
        hand=["Sink into Stupor / Soporific Springs"],
        floating_mana=ManaPool(U=3),
        stack=[StackObject(card_name="Gitaxian Probe")],
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Sink into Stupor" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 1


# ── Sundering Eruption / Volcanic Fissure ────────────────────────────────────

def test_sundering_eruption_requires_opponent_land():
    state = _make_state(
        hand=["Sundering Eruption / Volcanic Fissure"],
        floating_mana=ManaPool(R=3),
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Sundering Eruption" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 1
    assert "opponent" in cast_actions[0].description


def test_sundering_eruption_not_generated_when_unaffordable():
    state = _make_state(
        hand=["Sundering Eruption / Volcanic Fissure"],
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Sundering Eruption" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 0


def test_sundering_eruption_sorcery_speed_blocked_by_stack():
    from mtg_sim.sim.stack import StackObject
    state = _make_state(
        hand=["Sundering Eruption / Volcanic Fissure"],
        floating_mana=ManaPool(R=3),
        stack=[StackObject(card_name="Gitaxian Probe")],
    )
    cast_actions = [a for a in generate_actions(state) if a.action_type == CAST_SPELL
                    and "Sundering Eruption" in a.description and "as land" not in a.description]
    assert len(cast_actions) == 0
