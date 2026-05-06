"""Tests for nonland mana source card behaviors."""
import pytest
from pathlib import Path
from mtg_sim.sim.cards import load_card_library
from mtg_sim.sim.state import GameState, Permanent
from mtg_sim.sim.actions import ACTIVATE_MANA_ABILITY, SACRIFICE_FOR_MANA, EXILE_FOR_MANA, CAST_SPELL
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action

_DATA_DIR = Path(__file__).parent.parent.parent
load_card_library(str(_DATA_DIR / "card_library.csv"))


def _make_state(**kwargs) -> GameState:
    defaults = dict(hand=[], library=[], battlefield=[], graveyard=[])
    defaults.update(kwargs)
    return GameState(**defaults)


def _mana_actions(state):
    return [a for a in generate_actions(state) if a.action_type in (ACTIVATE_MANA_ABILITY, SACRIFICE_FOR_MANA, EXILE_FOR_MANA)]


def _actions_for(state, source):
    return [a for a in _mana_actions(state) if a.source_card == source]


# ── Sol Ring ──────────────────────────────────────────────────────────────────

def test_sol_ring_taps_for_two_colorless():
    perm = Permanent(card_name="Sol Ring")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Sol Ring")
    assert len(acts) == 1
    assert acts[0].effects.add_mana.C == 2


def test_sol_ring_cannot_tap_while_tapped():
    perm = Permanent(card_name="Sol Ring", tapped=True)
    state = _make_state(battlefield=[perm])
    assert not _actions_for(state, "Sol Ring")


# ── Mana Vault ────────────────────────────────────────────────────────────────

def test_mana_vault_taps_for_three_colorless():
    perm = Permanent(card_name="Mana Vault")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Mana Vault")
    assert len(acts) == 1
    assert acts[0].effects.add_mana.C == 3


def test_mana_vault_cannot_tap_while_tapped():
    perm = Permanent(card_name="Mana Vault", tapped=True)
    state = _make_state(battlefield=[perm])
    assert not _actions_for(state, "Mana Vault")


# ── Grim Monolith ─────────────────────────────────────────────────────────────

def test_grim_monolith_taps_for_three_colorless():
    perm = Permanent(card_name="Grim Monolith")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Grim Monolith")
    assert len(acts) == 1
    assert acts[0].effects.add_mana.C == 3


def test_grim_monolith_cannot_tap_while_tapped():
    perm = Permanent(card_name="Grim Monolith", tapped=True)
    state = _make_state(battlefield=[perm])
    assert not _actions_for(state, "Grim Monolith")


# ── Lotus Petal ───────────────────────────────────────────────────────────────

def test_lotus_petal_offers_three_colors():
    perm = Permanent(card_name="Lotus Petal")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Lotus Petal")
    colors = {a.effects.add_mana.U + a.effects.add_mana.R + a.effects.add_mana.C for a in acts}
    assert len(acts) == 3
    assert any(a.effects.add_mana.U == 1 for a in acts)
    assert any(a.effects.add_mana.R == 1 for a in acts)
    assert any(a.effects.add_mana.C == 1 for a in acts)


def test_lotus_petal_sacrifice_goes_to_graveyard():
    perm = Permanent(card_name="Lotus Petal")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Lotus Petal")
    act_u = next(a for a in acts if a.effects.add_mana.U == 1)
    resolve_action(state, act_u)
    assert not any(p.card_name == "Lotus Petal" for p in state.battlefield)
    assert "Lotus Petal" in state.graveyard


def test_lotus_petal_cannot_reuse():
    perm = Permanent(card_name="Lotus Petal")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Lotus Petal")
    resolve_action(state, acts[0])
    assert not _actions_for(state, "Lotus Petal")


# ── Mox Opal ─────────────────────────────────────────────────────────────────

def test_mox_opal_no_mana_without_metalcraft():
    perm = Permanent(card_name="Mox Opal")
    state = _make_state(battlefield=[perm])
    assert not _actions_for(state, "Mox Opal")


def test_mox_opal_mana_with_metalcraft():
    perms = [Permanent(card_name="Mox Opal"),
             Permanent(card_name="Sol Ring"),
             Permanent(card_name="Mana Vault")]
    state = _make_state(battlefield=perms)
    acts = _actions_for(state, "Mox Opal")
    assert len(acts) == 3
    assert any(a.effects.add_mana.U == 1 for a in acts)
    assert any(a.effects.add_mana.R == 1 for a in acts)
    assert any(a.effects.add_mana.C == 1 for a in acts)


def test_mox_opal_cannot_tap_while_tapped():
    perms = [Permanent(card_name="Mox Opal", tapped=True),
             Permanent(card_name="Sol Ring"),
             Permanent(card_name="Mana Vault")]
    state = _make_state(battlefield=perms)
    assert not _actions_for(state, "Mox Opal")


# ── Mox Amber ────────────────────────────────────────────────────────────────

def test_mox_amber_no_mana_without_legendary():
    perm = Permanent(card_name="Mox Amber")
    state = _make_state(battlefield=[perm])
    state.legendary_permanent_available = False
    assert not _actions_for(state, "Mox Amber")


def test_mox_amber_produces_u_and_r_with_vivi():
    perm = Permanent(card_name="Mox Amber")
    state = _make_state(battlefield=[perm])
    state.legendary_permanent_available = True
    acts = _actions_for(state, "Mox Amber")
    assert any(a.effects.add_mana.U == 1 for a in acts)
    assert any(a.effects.add_mana.R == 1 for a in acts)
    assert not any(a.effects.add_mana.C == 1 for a in acts)


def test_mox_amber_cannot_tap_while_tapped():
    perm = Permanent(card_name="Mox Amber", tapped=True)
    state = _make_state(battlefield=[perm])
    state.legendary_permanent_available = True
    assert not _actions_for(state, "Mox Amber")


# ── Chrome Mox ───────────────────────────────────────────────────────────────

def test_chrome_mox_no_mana_without_imprint():
    perm = Permanent(card_name="Chrome Mox")
    state = _make_state(battlefield=[perm])
    assert not _actions_for(state, "Chrome Mox")


def test_chrome_mox_taps_for_blue_when_blue_imprint():
    perm = Permanent(card_name="Chrome Mox", imprinted_card="Gitaxian Probe")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Chrome Mox")
    assert len(acts) == 1
    assert acts[0].effects.add_mana.U == 1


def test_chrome_mox_offers_both_colors_for_ur_imprint():
    perm = Permanent(card_name="Chrome Mox", imprinted_card="Rite of Flame")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Chrome Mox")
    # Rite of Flame is a red card; should produce R
    assert any(a.effects.add_mana.R == 1 for a in acts)


def test_chrome_mox_no_colorless_from_imprint():
    perm = Permanent(card_name="Chrome Mox", imprinted_card="Gitaxian Probe")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Chrome Mox")
    assert not any(a.effects.add_mana.C == 1 for a in acts)


# ── Mox Diamond ──────────────────────────────────────────────────────────────

def test_mox_diamond_taps_for_u_r_c():
    perm = Permanent(card_name="Mox Diamond")
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Mox Diamond")
    assert any(a.effects.add_mana.U == 1 for a in acts)
    assert any(a.effects.add_mana.R == 1 for a in acts)
    assert any(a.effects.add_mana.C == 1 for a in acts)


def test_mox_diamond_cannot_tap_while_tapped():
    perm = Permanent(card_name="Mox Diamond", tapped=True)
    state = _make_state(battlefield=[perm])
    assert not _actions_for(state, "Mox Diamond")


# ── Simian Spirit Guide ───────────────────────────────────────────────────────

def test_ssg_exile_from_hand_adds_r():
    state = _make_state(hand=["Simian Spirit Guide"])
    acts = [a for a in generate_actions(state) if a.source_card == "Simian Spirit Guide"]
    assert acts
    assert all(a.effects.add_mana.R == 1 for a in acts)


def test_ssg_moves_to_exile():
    state = _make_state(hand=["Simian Spirit Guide"])
    acts = [a for a in generate_actions(state) if a.source_card == "Simian Spirit Guide"]
    resolve_action(state, acts[0])
    assert "Simian Spirit Guide" not in state.hand
    assert "Simian Spirit Guide" in state.exile


def test_ssg_cannot_reuse():
    state = _make_state(hand=["Simian Spirit Guide"])
    acts = [a for a in generate_actions(state) if a.source_card == "Simian Spirit Guide"]
    resolve_action(state, acts[0])
    assert not any(a.source_card == "Simian Spirit Guide" for a in generate_actions(state))


# ── Springleaf Drum ───────────────────────────────────────────────────────────

def test_springleaf_drum_requires_untapped_creature():
    perm = Permanent(card_name="Springleaf Drum")
    state = _make_state(battlefield=[perm])
    state.vivi_available_as_creature_to_tap = False
    assert not _actions_for(state, "Springleaf Drum")


def test_springleaf_drum_offers_mana_with_creature():
    perm = Permanent(card_name="Springleaf Drum")
    state = _make_state(battlefield=[perm])
    state.vivi_available_as_creature_to_tap = True
    acts = _actions_for(state, "Springleaf Drum")
    assert any(a.effects.add_mana.U == 1 for a in acts)
    assert any(a.effects.add_mana.R == 1 for a in acts)


# ── Jeweled Amulet ────────────────────────────────────────────────────────────

def test_jeweled_amulet_no_mana_without_charge():
    perm = Permanent(card_name="Jeweled Amulet")
    state = _make_state(battlefield=[perm])
    assert not _actions_for(state, "Jeweled Amulet")


def test_jeweled_amulet_charged_produces_stored_mana():
    perm = Permanent(card_name="Jeweled Amulet", counters={"charge": 1, "color": "U"})
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Jeweled Amulet")
    assert len(acts) == 1
    assert acts[0].effects.add_mana.U == 1


def test_jeweled_amulet_sacrifice_on_use():
    perm = Permanent(card_name="Jeweled Amulet", counters={"charge": 1, "color": "R"})
    state = _make_state(battlefield=[perm])
    acts = _actions_for(state, "Jeweled Amulet")
    resolve_action(state, acts[0])
    assert not any(p.card_name == "Jeweled Amulet" for p in state.battlefield)


# ── Rite of Flame ─────────────────────────────────────────────────────────────

def _resolve_stack(state):
    from mtg_sim.sim.actions import RESOLVE_STACK_OBJECT
    while state.stack:
        res_acts = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
        if not res_acts:
            break
        resolve_action(state, res_acts[0])


def test_rite_of_flame_adds_rr():
    from mtg_sim.sim.mana import ManaPool
    state = _make_state(hand=["Rite of Flame"])
    state.floating_mana = ManaPool(R=1)
    acts = [a for a in generate_actions(state) if a.source_card == "Rite of Flame" and a.action_type == CAST_SPELL]
    assert acts
    resolve_action(state, acts[0])
    _resolve_stack(state)
    assert state.floating_mana.R == 2  # paid 1R, got 2R back


def test_rite_of_flame_graveyard_bonus_ignored():
    from mtg_sim.sim.mana import ManaPool
    state = _make_state(hand=["Rite of Flame"], graveyard=["Rite of Flame", "Rite of Flame"])
    state.floating_mana = ManaPool(R=1)
    acts = [a for a in generate_actions(state) if a.source_card == "Rite of Flame" and a.action_type == CAST_SPELL]
    resolve_action(state, acts[0])
    _resolve_stack(state)
    assert state.floating_mana.R == 2  # still 2R regardless of 2 rites in graveyard


# ── Simian Spirit Guide (instant speed) ──────────────────────────────────────

def test_ssg_available_with_stack_nonempty():
    from mtg_sim.sim.stack import StackObject
    state = _make_state(hand=["Simian Spirit Guide"])
    state.stack = [StackObject(card_name="some spell", stack_id="x")]
    acts = [a for a in generate_actions(state) if a.source_card == "Simian Spirit Guide"]
    assert acts  # instant speed, available on non-empty stack


# ── Paradise Mantle ───────────────────────────────────────────────────────────

def test_paradise_mantle_equip_action_at_sorcery_speed():
    perm = Permanent(card_name="Paradise Mantle")
    state = _make_state(battlefield=[perm])
    state.vivi_available_as_creature_to_tap = True
    acts = _actions_for(state, "Paradise Mantle")
    equip_acts = [a for a in acts if "Equip" in a.description]
    assert equip_acts


def test_paradise_mantle_no_equip_with_stack():
    from mtg_sim.sim.stack import StackObject
    perm = Permanent(card_name="Paradise Mantle")
    state = _make_state(battlefield=[perm])
    state.stack = [StackObject(card_name="spell", stack_id="x")]
    state.vivi_available_as_creature_to_tap = True
    acts = _actions_for(state, "Paradise Mantle")
    equip_acts = [a for a in acts if "Equip" in a.description]
    assert not equip_acts


def test_paradise_mantle_equip_attaches_to_vivi():
    perm = Permanent(card_name="Paradise Mantle")
    state = _make_state(battlefield=[perm])
    state.vivi_available_as_creature_to_tap = True
    acts = _actions_for(state, "Paradise Mantle")
    equip_act = next(a for a in acts if "Equip" in a.description)
    resolve_action(state, equip_act)
    mantle_perm = next(p for p in state.battlefield if p.card_name == "Paradise Mantle")
    assert mantle_perm.attached_to == "vivi"


def test_paradise_mantle_equipped_vivi_taps_for_u_and_r():
    perm = Permanent(card_name="Paradise Mantle", attached_to="vivi")
    state = _make_state(battlefield=[perm])
    state.vivi_available_as_creature_to_tap = True
    acts = _actions_for(state, "Paradise Mantle")
    assert any(a.effects.add_mana.U == 1 for a in acts)
    assert any(a.effects.add_mana.R == 1 for a in acts)


def test_paradise_mantle_no_mana_if_vivi_tapped():
    perm = Permanent(card_name="Paradise Mantle", attached_to="vivi")
    state = _make_state(battlefield=[perm])
    state.vivi_available_as_creature_to_tap = False
    acts = [a for a in _actions_for(state, "Paradise Mantle") if a.effects.add_mana.U or a.effects.add_mana.R]
    assert not acts


def test_paradise_mantle_tap_vivi_marks_as_tapped():
    perm = Permanent(card_name="Paradise Mantle", attached_to="vivi")
    state = _make_state(battlefield=[perm])
    state.vivi_available_as_creature_to_tap = True
    acts = _actions_for(state, "Paradise Mantle")
    act_u = next(a for a in acts if a.effects.add_mana.U == 1)
    resolve_action(state, act_u)
    assert not state.vivi_available_as_creature_to_tap


# ── Strike It Rich ────────────────────────────────────────────────────────────

def test_strike_it_rich_creates_treasure():
    from mtg_sim.sim.mana import ManaPool
    state = _make_state(hand=["Strike It Rich"])
    state.floating_mana = ManaPool(R=1)
    acts = [a for a in generate_actions(state) if a.source_card == "Strike It Rich" and a.action_type == CAST_SPELL]
    assert acts
    resolve_action(state, acts[0])
    _resolve_stack(state)
    assert any(p.card_name == "_Treasure" for p in state.battlefield)


def test_strike_it_rich_flashback_from_graveyard():
    from mtg_sim.sim.mana import ManaPool
    # Flashback cost is {2R} = 3 mana total
    state = _make_state(graveyard=["Strike It Rich"])
    state.floating_mana = ManaPool(R=3)
    acts = [a for a in generate_actions(state) if a.source_card == "Strike It Rich" and a.action_type == CAST_SPELL]
    assert acts
    flashback_act = next((a for a in acts if a.alt_cost_type == "flashback"), None)
    assert flashback_act


def test_strike_it_rich_flashback_exiles_card():
    from mtg_sim.sim.mana import ManaPool
    state = _make_state(graveyard=["Strike It Rich"])
    state.floating_mana = ManaPool(R=3)
    acts = [a for a in generate_actions(state) if a.source_card == "Strike It Rich" and a.alt_cost_type == "flashback"]
    assert acts
    resolve_action(state, acts[0])
    _resolve_stack(state)
    assert "Strike It Rich" not in state.graveyard
    assert "Strike It Rich" in state.exile
