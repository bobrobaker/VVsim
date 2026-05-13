"""Tests for Other Lands bucket (lines 147-224 of docs/specs/card_specifics.md)."""
import pytest
from pathlib import Path
from mtg_sim.sim.cards import load_card_library
from mtg_sim.sim.state import GameState, Permanent
from mtg_sim.sim.action_generator import generate_actions, _is_island, _we_control_mountain
from mtg_sim.sim.resolver import resolve_action
from mtg_sim.sim.actions import PLAY_LAND, ACTIVATE_MANA_ABILITY, SACRIFICE_FOR_MANA, CHOOSE_LAND_TYPE

_DATA_DIR = Path(__file__).parent.parent.parent
load_card_library(str(_DATA_DIR / "card_library.csv"))


def _make_state(**kwargs) -> GameState:
    defaults = dict(hand=[], library=[], battlefield=[], graveyard=[])
    defaults.update(kwargs)
    return GameState(**defaults)


def _mana_actions(state):
    return [a for a in generate_actions(state) if a.action_type == ACTIVATE_MANA_ABILITY]


def _land_play_actions(state):
    return [a for a in generate_actions(state) if a.action_type == PLAY_LAND]


def _land_type_actions(state):
    return [a for a in generate_actions(state) if a.action_type == CHOOSE_LAND_TYPE]


# ── Ancient Tomb ──────────────────────────────────────────────────────────────

def test_ancient_tomb_playable_as_land():
    state = _make_state(hand=["Ancient Tomb"])
    assert any(a.source_card == "Ancient Tomb" for a in _land_play_actions(state))


def test_ancient_tomb_enters_untapped():
    state = _make_state(hand=["Ancient Tomb"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Ancient Tomb")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Ancient Tomb")
    assert not perm.tapped


def test_ancient_tomb_taps_for_two_colorless():
    perm = Permanent(card_name="Ancient Tomb")
    state = _make_state(battlefield=[perm])
    actions = _mana_actions(state)
    ancient_tomb_actions = [a for a in actions if a.source_card == "Ancient Tomb"]
    assert len(ancient_tomb_actions) == 1
    assert ancient_tomb_actions[0].effects.add_mana.C == 2


def test_ancient_tomb_cannot_tap_while_tapped():
    perm = Permanent(card_name="Ancient Tomb", tapped=True)
    state = _make_state(battlefield=[perm])
    assert not any(a.source_card == "Ancient Tomb" for a in _mana_actions(state))


# ── Island ────────────────────────────────────────────────────────────────────

def test_island_playable_as_land():
    state = _make_state(hand=["Island"])
    assert any(a.source_card == "Island" for a in _land_play_actions(state))


def test_island_enters_untapped():
    state = _make_state(hand=["Island"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Island")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Island")
    assert not perm.tapped


def test_island_taps_for_u():
    perm = Permanent(card_name="Island")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Island"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.U == 1


def test_island_cannot_tap_while_tapped():
    perm = Permanent(card_name="Island", tapped=True)
    state = _make_state(battlefield=[perm])
    assert not any(a.source_card == "Island" for a in _mana_actions(state))


def test_island_counts_as_island():
    perm = Permanent(card_name="Island")
    assert _is_island(perm)


# ── Mountain ──────────────────────────────────────────────────────────────────

def test_mountain_playable_as_land():
    state = _make_state(hand=["Mountain"])
    assert any(a.source_card == "Mountain" for a in _land_play_actions(state))


def test_mountain_taps_for_r():
    perm = Permanent(card_name="Mountain")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Mountain"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.R == 1


def test_mountain_counts_as_mountain():
    perm = Permanent(card_name="Mountain")
    state = _make_state(battlefield=[perm])
    assert _we_control_mountain(state)


# ── Steam Vents ───────────────────────────────────────────────────────────────

def test_steam_vents_playable_as_land():
    state = _make_state(hand=["Steam Vents"])
    assert any(a.source_card == "Steam Vents" for a in _land_play_actions(state))


def test_steam_vents_enters_untapped():
    state = _make_state(hand=["Steam Vents"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Steam Vents")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Steam Vents")
    assert not perm.tapped


def test_steam_vents_taps_for_u_and_r():
    perm = Permanent(card_name="Steam Vents")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Steam Vents"]
    assert any(a.effects.add_mana.U == 1 for a in actions)
    assert any(a.effects.add_mana.R == 1 for a in actions)


def test_steam_vents_counts_as_island():
    perm = Permanent(card_name="Steam Vents")
    assert _is_island(perm)


def test_steam_vents_counts_as_mountain():
    perm = Permanent(card_name="Steam Vents")
    state = _make_state(battlefield=[perm])
    assert _we_control_mountain(state)


# ── Volcanic Island ───────────────────────────────────────────────────────────

def test_volcanic_island_taps_for_u_and_r():
    perm = Permanent(card_name="Volcanic Island")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Volcanic Island"]
    assert any(a.effects.add_mana.U == 1 for a in actions)
    assert any(a.effects.add_mana.R == 1 for a in actions)


def test_volcanic_island_counts_as_island():
    perm = Permanent(card_name="Volcanic Island")
    assert _is_island(perm)


def test_volcanic_island_counts_as_mountain():
    perm = Permanent(card_name="Volcanic Island")
    state = _make_state(battlefield=[perm])
    assert _we_control_mountain(state)


# ── Thundering Falls ──────────────────────────────────────────────────────────

def test_thundering_falls_enters_tapped():
    state = _make_state(hand=["Thundering Falls"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Thundering Falls")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Thundering Falls")
    assert perm.tapped


def test_thundering_falls_taps_for_u_and_r():
    perm = Permanent(card_name="Thundering Falls")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Thundering Falls"]
    assert any(a.effects.add_mana.U == 1 for a in actions)
    assert any(a.effects.add_mana.R == 1 for a in actions)


def test_thundering_falls_counts_as_island():
    perm = Permanent(card_name="Thundering Falls")
    assert _is_island(perm)


def test_thundering_falls_counts_as_mountain():
    perm = Permanent(card_name="Thundering Falls")
    state = _make_state(battlefield=[perm])
    assert _we_control_mountain(state)


# ── Sandstone Needle ──────────────────────────────────────────────────────────

def test_sandstone_needle_enters_tapped():
    state = _make_state(hand=["Sandstone Needle"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Sandstone Needle")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Sandstone Needle")
    assert perm.tapped


def test_sandstone_needle_cannot_tap_while_tapped():
    perm = Permanent(card_name="Sandstone Needle", tapped=True, depletion_counters=2)
    state = _make_state(battlefield=[perm])
    assert not any(a.source_card == "Sandstone Needle" for a in _mana_actions(state))


def test_sandstone_needle_produces_rr_and_loses_counter():
    perm = Permanent(card_name="Sandstone Needle", depletion_counters=2)
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Sandstone Needle"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.R == 2
    resolve_action(state, actions[0])
    perm_after = next(p for p in state.battlefield if p.card_name == "Sandstone Needle")
    assert perm_after.depletion_counters == 1


def test_sandstone_needle_unusable_after_counters_gone():
    perm = Permanent(card_name="Sandstone Needle", depletion_counters=0)
    state = _make_state(battlefield=[perm])
    assert not any(a.source_card == "Sandstone Needle" for a in _mana_actions(state))


# ── Saprazzan Skerry ──────────────────────────────────────────────────────────

def test_saprazzan_skerry_enters_tapped():
    state = _make_state(hand=["Saprazzan Skerry"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Saprazzan Skerry")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Saprazzan Skerry")
    assert perm.tapped


def test_saprazzan_skerry_produces_uu_and_loses_counter():
    perm = Permanent(card_name="Saprazzan Skerry", depletion_counters=2)
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Saprazzan Skerry"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.U == 2
    resolve_action(state, actions[0])
    perm_after = next(p for p in state.battlefield if p.card_name == "Saprazzan Skerry")
    assert perm_after.depletion_counters == 1


def test_saprazzan_skerry_unusable_after_counters_gone():
    perm = Permanent(card_name="Saprazzan Skerry", depletion_counters=0)
    state = _make_state(battlefield=[perm])
    assert not any(a.source_card == "Saprazzan Skerry" for a in _mana_actions(state))


# ── Fiery Islet ───────────────────────────────────────────────────────────────

def test_fiery_islet_taps_for_u():
    perm = Permanent(card_name="Fiery Islet")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Fiery Islet" and a.action_type == ACTIVATE_MANA_ABILITY]
    assert any(a.effects.add_mana.U == 1 and a.effects.draw_cards == 0 for a in actions)


def test_fiery_islet_taps_for_r():
    perm = Permanent(card_name="Fiery Islet")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Fiery Islet" and a.action_type == ACTIVATE_MANA_ABILITY]
    assert any(a.effects.add_mana.R == 1 for a in actions)


def test_fiery_islet_draw_ability_requires_one_mana():
    perm = Permanent(card_name="Fiery Islet")
    state = _make_state(battlefield=[perm])
    sac_actions = [a for a in generate_actions(state) if a.action_type == SACRIFICE_FOR_MANA and a.source_card == "Fiery Islet"]
    assert not sac_actions  # no floating mana to pay cost


def test_fiery_islet_draw_ability_available_with_mana():
    from mtg_sim.sim.mana import ManaPool
    perm = Permanent(card_name="Fiery Islet")
    state = _make_state(battlefield=[perm], floating_mana=ManaPool(C=1))
    sac_actions = [a for a in generate_actions(state) if a.action_type == SACRIFICE_FOR_MANA and a.source_card == "Fiery Islet"]
    assert len(sac_actions) == 1


def test_fiery_islet_sacrifice_draws_one_and_prevents_reuse():
    from mtg_sim.sim.mana import ManaPool
    perm = Permanent(card_name="Fiery Islet")
    state = _make_state(
        battlefield=[perm],
        floating_mana=ManaPool(C=1),
        library=["Gitaxian Probe"],
    )
    action = next(a for a in generate_actions(state) if a.action_type == SACRIFICE_FOR_MANA and a.source_card == "Fiery Islet")
    resolve_action(state, action)
    assert "Gitaxian Probe" in state.hand
    assert not any(p.card_name == "Fiery Islet" for p in state.battlefield)


def test_fiery_islet_no_abilities_when_tapped():
    perm = Permanent(card_name="Fiery Islet", tapped=True)
    state = _make_state(battlefield=[perm])
    fiery_actions = [a for a in generate_actions(state) if a.source_card == "Fiery Islet"]
    assert not fiery_actions


# ── Gemstone Caverns ──────────────────────────────────────────────────────────

def test_gemstone_caverns_no_luck_counter_produces_colorless():
    perm = Permanent(card_name="Gemstone Caverns")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Gemstone Caverns"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.C == 1
    assert actions[0].effects.add_mana.U == 0
    assert actions[0].effects.add_mana.R == 0


def test_gemstone_caverns_with_luck_counter_produces_ur_only():
    perm = Permanent(card_name="Gemstone Caverns")
    perm.counters["luck_counter"] = 1
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Gemstone Caverns"]
    assert any(a.effects.add_mana.U == 1 for a in actions)
    assert any(a.effects.add_mana.R == 1 for a in actions)
    assert not any(a.effects.add_mana.C == 1 for a in actions)


# ── Cavern of Souls ───────────────────────────────────────────────────────────

def test_cavern_of_souls_always_produces_colorless():
    perm = Permanent(card_name="Cavern of Souls")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Cavern of Souls"]
    assert any(a.effects.add_mana.C == 1 for a in actions)


def test_cavern_of_souls_colored_mana_only_with_creature_in_hand():
    from mtg_sim.sim.mana import ManaPool
    perm = Permanent(card_name="Cavern of Souls")
    # No creatures in hand
    state = _make_state(battlefield=[perm], hand=["Gitaxian Probe"])
    actions = [a for a in _mana_actions(state) if a.source_card == "Cavern of Souls"]
    assert not any(a.effects.add_mana.U == 1 or a.effects.add_mana.R == 1 for a in actions)


def test_cavern_of_souls_colored_mana_available_with_creature_in_hand():
    perm = Permanent(card_name="Cavern of Souls")
    state = _make_state(battlefield=[perm], hand=["Vivi Ornitier"])
    actions = [a for a in _mana_actions(state) if a.source_card == "Cavern of Souls"]
    assert any(a.effects.add_mana.U == 1 for a in actions)
    assert any(a.effects.add_mana.R == 1 for a in actions)


# ── Multiversal Passage ───────────────────────────────────────────────────────

def test_multiversal_passage_playable_as_land():
    state = _make_state(hand=["Multiversal Passage"])
    assert any(a.source_card == "Multiversal Passage" for a in _land_play_actions(state))


def test_multiversal_passage_generates_pending_type_choice():
    state = _make_state(hand=["Multiversal Passage"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Multiversal Passage")
    resolve_action(state, action)
    assert any(c.choice_type == "land_type" for c in state.pending_choices)


def test_multiversal_passage_type_choice_options():
    state = _make_state(hand=["Multiversal Passage"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Multiversal Passage")
    resolve_action(state, action)
    land_type_actions = _land_type_actions(state)
    source_cards = {a.source_card for a in land_type_actions}
    assert "Island" in source_cards
    assert "Mountain" in source_cards


def test_multiversal_passage_chosen_island_taps_for_u():
    perm = Permanent(card_name="Multiversal Passage")
    perm.counters["land_type"] = "Island"
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Multiversal Passage"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.U == 1


def test_multiversal_passage_chosen_mountain_taps_for_r():
    perm = Permanent(card_name="Multiversal Passage")
    perm.counters["land_type"] = "Mountain"
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Multiversal Passage"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.R == 1


def test_multiversal_passage_island_counts_for_island_checks():
    perm = Permanent(card_name="Multiversal Passage")
    perm.counters["land_type"] = "Island"
    assert _is_island(perm)


def test_multiversal_passage_mountain_counts_for_mountain_checks():
    perm = Permanent(card_name="Multiversal Passage")
    perm.counters["land_type"] = "Mountain"
    state = _make_state(battlefield=[perm])
    assert _we_control_mountain(state)


def test_multiversal_passage_no_mana_before_type_chosen():
    perm = Permanent(card_name="Multiversal Passage")
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Multiversal Passage"]
    assert not actions


def test_multiversal_passage_choose_land_type_stored_on_perm():
    state = _make_state(hand=["Multiversal Passage"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Multiversal Passage")
    resolve_action(state, action)
    choice_action = next(a for a in _land_type_actions(state) if a.source_card == "Island")
    resolve_action(state, choice_action)
    perm = next(p for p in state.battlefield if p.card_name == "Multiversal Passage")
    assert perm.counters.get("land_type") == "Island"


# ── Thran Portal ──────────────────────────────────────────────────────────────

def test_thran_portal_enters_untapped_with_two_or_fewer_other_lands():
    other_land = Permanent(card_name="Island")
    state = _make_state(hand=["Thran Portal"], battlefield=[other_land])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Thran Portal")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Thran Portal")
    assert not perm.tapped


def test_thran_portal_enters_tapped_with_three_or_more_other_lands():
    other_lands = [Permanent(card_name="Island"), Permanent(card_name="Mountain"), Permanent(card_name="Volcanic Island")]
    state = _make_state(hand=["Thran Portal"], battlefield=other_lands)
    action = next(a for a in _land_play_actions(state) if a.source_card == "Thran Portal")
    resolve_action(state, action)
    perm = next(p for p in state.battlefield if p.card_name == "Thran Portal")
    assert perm.tapped


def test_thran_portal_generates_land_type_choice():
    state = _make_state(hand=["Thran Portal"])
    action = next(a for a in _land_play_actions(state) if a.source_card == "Thran Portal")
    resolve_action(state, action)
    assert any(c.choice_type == "land_type" for c in state.pending_choices)


def test_thran_portal_chosen_island_taps_for_u_and_counts_as_island():
    perm = Permanent(card_name="Thran Portal")
    perm.counters["land_type"] = "Island"
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Thran Portal"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.U == 1
    assert _is_island(perm)


def test_thran_portal_chosen_mountain_taps_for_r_and_counts_as_mountain():
    perm = Permanent(card_name="Thran Portal")
    perm.counters["land_type"] = "Mountain"
    state = _make_state(battlefield=[perm])
    actions = [a for a in _mana_actions(state) if a.source_card == "Thran Portal"]
    assert len(actions) == 1
    assert actions[0].effects.add_mana.R == 1
    assert _we_control_mountain(state)
