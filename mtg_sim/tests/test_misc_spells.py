"""Tests for Misc Spells bucket behaviors."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.actions import CAST_SPELL, SACRIFICE_FOR_MANA
from mtg_sim.sim.state import GameState, Permanent
from random import Random


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def _drain_stack(state):
    """Resolve all stack objects in order."""
    from mtg_sim.sim.actions import RESOLVE_STACK_OBJECT
    while state.stack:
        acts = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
        if not acts:
            break
        resolve_action(state, acts[0])


def _state(hand, mana=None, battlefield=None, library=None):
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=hand,
                    starting_floating_mana=mana or ManaPool())
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    if battlefield:
        for perm in battlefield:
            state.battlefield.append(perm)
    if library is not None:
        state.library = library
    return state


# ── Snapback ──────────────────────────────────────────────────────────────────

def test_snapback_generates_normal_cast_with_creature_target():
    state = _state(["Snapback"], ManaPool(U=1, ANY=1))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Snapback" and not a.alt_cost_type]
    assert len(acts) >= 1, "Snapback should generate normal cast targeting a creature"


def test_snapback_requires_creature_target_not_counterspell():
    # No stack object → no counterspell targets; creature (Vivi) is on battlefield
    state = _state(["Snapback"], ManaPool(U=1, ANY=1))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Snapback"]
    assert all(a.requires_target and a.target is not None for a in acts), \
        "Snapback actions must target a creature, not a stack object"


def test_snapback_generates_pitch_blue_with_creature_target():
    state = _state(["Snapback", "Gitaxian Probe"], ManaPool())
    actions = generate_actions(state)
    pitch_acts = [a for a in actions if a.source_card == "Snapback"
                  and a.alt_cost_type == "pitch_blue"]
    assert len(pitch_acts) >= 1, "Snapback should generate pitch-blue actions"


def test_snapback_prunes_own_vivi_when_dummy_target_exists():
    state = _state(["Snapback"], ManaPool(U=1, ANY=1))
    vivi_perm = next(p for p in state.battlefield if p.card_name == "Vivi Ornitier")
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Snapback"]
    assert acts
    assert all(a.target != vivi_perm.perm_id for a in acts)
    assert all(a.target == state._opponent_creature_perm.perm_id for a in acts)


def test_snapback_can_target_own_creature_without_dummy_target():
    state = _state(["Snapback"], ManaPool(U=1, ANY=1))
    state._opponent_creature_perm = None
    vivi_perm = next(p for p in state.battlefield if p.card_name == "Vivi Ornitier")
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Snapback" and a.target == vivi_perm.perm_id)
    resolve_action(state, act)
    from mtg_sim.sim.actions import RESOLVE_STACK_OBJECT
    res_acts = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
    if res_acts:
        resolve_action(state, res_acts[0])  # draw trigger
    res_acts = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
    if res_acts:
        resolve_action(state, res_acts[0])  # Snapback itself
    assert "Vivi Ornitier" in state.hand, "Snapback should bounce own creature to hand"


def test_snapback_dummy_target_resolves_safely():
    state = _state(["Snapback"], ManaPool(U=1, ANY=1))
    opp = state._opponent_creature_perm
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Snapback"
               and a.target == opp.perm_id)
    resolve_action(state, act)
    # Should not raise; dummy target just gets noted
    _drain_stack(state)


def test_snapback_pitch_exiles_card():
    state = _state(["Snapback", "Gitaxian Probe"], ManaPool())
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Snapback"
               and a.alt_cost_type == "pitch_blue")
    pitched = act.costs.pitched_card
    resolve_action(state, act)
    assert pitched not in state.hand
    assert pitched in state.exile


# ── Blazing Shoal ─────────────────────────────────────────────────────────────

def test_blazing_shoal_requires_creature_target():
    # With Vivi on battlefield, should generate targets
    state = _state(["Blazing Shoal", "Rite of Flame"], ManaPool())
    actions = generate_actions(state)
    shoal_acts = [a for a in actions if a.source_card == "Blazing Shoal"]
    assert all(a.target is not None for a in shoal_acts), \
        "Blazing Shoal requires a creature target"


def test_blazing_shoal_no_actions_without_creature_target():
    # Remove Vivi from battlefield; no dummy creature available either
    state = _state(["Blazing Shoal", "Rite of Flame"], ManaPool())
    state.battlefield = [p for p in state.battlefield
                         if p.card_name != "Vivi Ornitier"]
    state._opponent_creature_perm = None
    state.vivi_on_battlefield = False
    actions = generate_actions(state)
    shoal_acts = [a for a in actions if a.source_card == "Blazing Shoal"]
    assert len(shoal_acts) == 0, "Blazing Shoal needs a creature target"


# -- Strike It Rich --

def test_strike_it_rich_no_action_with_only_R_in_graveyard():
    state = _state([], ManaPool(R=1))
    state.graveyard = ["Strike It Rich"]

    actions = generate_actions(state)
    acts = [a for a in actions
            if a.action_type == CAST_SPELL and a.source_card == "Strike It Rich"]

    assert not acts


def test_strike_it_rich_flashback_requires_2R():
    state = _state([], ManaPool(R=1, ANY=2))
    state.graveyard = ["Strike It Rich"]

    actions = generate_actions(state)
    flashback_acts = [a for a in actions
                      if a.action_type == CAST_SPELL
                      and a.source_card == "Strike It Rich"
                      and a.alt_cost_type == "flashback"]
    non_flashback_acts = [a for a in actions
                          if a.action_type == CAST_SPELL
                          and a.source_card == "Strike It Rich"
                          and a.alt_cost_type != "flashback"]

    assert len(flashback_acts) == 1
    assert not non_flashback_acts


def test_strike_it_rich_flashback_resolves_to_exile():
    state = _state([], ManaPool(R=1, ANY=2))
    state.graveyard = ["Strike It Rich"]

    actions = generate_actions(state)
    act = next(a for a in actions
               if a.action_type == CAST_SPELL
               and a.source_card == "Strike It Rich"
               and a.alt_cost_type == "flashback")

    resolve_action(state, act)
    _drain_stack(state)

    assert "Strike It Rich" in state.exile
    assert "Strike It Rich" not in state.graveyard


# ── Baubles ───────────────────────────────────────────────────────────────────

def test_mishra_bauble_resolves_to_battlefield():
    state = _state(["Mishra's Bauble"], ManaPool())
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Mishra's Bauble")
    resolve_action(state, act)
    _drain_stack(state)
    assert any(p.card_name == "Mishra's Bauble" for p in state.battlefield)


def test_mishra_bauble_generates_sac_ability():
    state = _state([], ManaPool())
    state.battlefield.append(Permanent(card_name="Mishra's Bauble"))
    actions = generate_actions(state)
    sac_acts = [a for a in actions if a.source_card == "Mishra's Bauble"
                and a.action_type == SACRIFICE_FOR_MANA]
    assert len(sac_acts) == 1, "Mishra's Bauble should generate a sac ability"


def test_mishra_bauble_sac_moves_to_graveyard():
    state = _state([], ManaPool())
    perm = Permanent(card_name="Mishra's Bauble")
    state.battlefield.append(perm)
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Mishra's Bauble"
               and a.action_type == SACRIFICE_FOR_MANA)
    resolve_action(state, act)
    assert not any(p.card_name == "Mishra's Bauble" for p in state.battlefield)
    assert "Mishra's Bauble" in state.graveyard


def test_mishra_bauble_no_sac_if_tapped():
    state = _state([], ManaPool())
    perm = Permanent(card_name="Mishra's Bauble", tapped=True)
    state.battlefield.append(perm)
    actions = generate_actions(state)
    sac_acts = [a for a in actions if a.source_card == "Mishra's Bauble"
                and a.action_type == SACRIFICE_FOR_MANA]
    assert len(sac_acts) == 0, "Tapped Mishra's Bauble should not generate sac ability"


def test_urza_bauble_generates_sac_ability():
    state = _state([], ManaPool())
    state.battlefield.append(Permanent(card_name="Urza's Bauble"))
    actions = generate_actions(state)
    sac_acts = [a for a in actions if a.source_card == "Urza's Bauble"
                and a.action_type == SACRIFICE_FOR_MANA]
    assert len(sac_acts) == 1


def test_lodestone_bauble_generates_sac_ability():
    state = _state([], ManaPool())
    state.battlefield.append(Permanent(card_name="Lodestone Bauble"))
    actions = generate_actions(state)
    sac_acts = [a for a in actions if a.source_card == "Lodestone Bauble"
                and a.action_type == SACRIFICE_FOR_MANA]
    assert len(sac_acts) == 1


def test_vexing_bauble_generates_sac_ability():
    state = _state([], ManaPool())
    state.battlefield.append(Permanent(card_name="Vexing Bauble"))
    actions = generate_actions(state)
    sac_acts = [a for a in actions if a.source_card == "Vexing Bauble"
                and a.action_type == SACRIFICE_FOR_MANA]
    assert len(sac_acts) == 1


# ── Boomerang Basics ──────────────────────────────────────────────────────────

def test_boomerang_basics_sorcery_speed_only():
    from mtg_sim.sim.stack import StackObject
    state = _state(["Boomerang Basics"], ManaPool(U=1))
    state.stack.append(StackObject(card_name="Dummy Spell"))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Boomerang Basics"]
    assert len(acts) == 0, "Boomerang Basics should not be castable while stack is nonempty"


def test_wild_ride_not_castable_with_stack_nonempty():
    from mtg_sim.sim.stack import StackObject
    state = _state(["Wild Ride"], ManaPool(R=1))
    state.stack.append(StackObject(card_name="Mishra's Bauble"))
    actions = generate_actions(state)
    acts = [
        a for a in actions
        if a.source_card == "Wild Ride" and a.action_type == CAST_SPELL
    ]
    assert len(acts) == 0, "Wild Ride should not be castable while stack is nonempty"


def test_wild_ride_castable_with_empty_stack():
    state = _state(["Wild Ride"], ManaPool(R=1))
    actions = generate_actions(state)
    acts = [
        a for a in actions
        if a.source_card == "Wild Ride" and a.action_type == CAST_SPELL
    ]
    assert len(acts) >= 1, "Wild Ride should be castable with an empty stack"


def test_boomerang_basics_bounces_own_permanent():
    state = _state(["Boomerang Basics"], ManaPool(U=1))
    perm = Permanent(card_name="Mishra's Bauble")
    state.battlefield.append(perm)
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Boomerang Basics"
            and a.target == perm.perm_id]
    assert len(acts) == 1
    resolve_action(state, acts[0])
    _drain_stack(state)
    assert "Mishra's Bauble" in state.hand


def test_boomerang_basics_own_bounce_draws_one():
    state = _state(["Boomerang Basics"], ManaPool(U=1))
    perm = Permanent(card_name="Mishra's Bauble")
    state.battlefield.append(perm)
    state.library = ["Test Card"] * 5
    drawn_before = state.total_cards_drawn
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Boomerang Basics"
               and a.target == perm.perm_id)
    resolve_action(state, act)
    _drain_stack(state)
    assert state.total_cards_drawn > drawn_before, "Boomerang Basics should draw 1 when bouncing own permanent"


def test_boomerang_basics_no_land_targets():
    state = _state(["Boomerang Basics"], ManaPool(U=1))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Boomerang Basics"]
    for act in acts:
        perm = state.get_perm_by_id(act.target) if act.target else None
        if perm:
            from mtg_sim.sim.cards import get_card
            cd = get_card(perm.card_name)
            assert cd is None or not cd.is_land, "Boomerang Basics should not target lands"


def test_boomerang_basics_dummy_target_no_draw():
    state = _state(["Boomerang Basics"], ManaPool(U=1))
    state.library = ["Test Card"] * 5
    drawn_before = state.total_cards_drawn
    actions = generate_actions(state)
    act = next((a for a in actions if a.source_card == "Boomerang Basics"
                and a.target == state._opponent_creature_perm.perm_id), None)
    if act is None:
        return  # No dummy target available
    resolve_action(state, act)
    _drain_stack(state)
    # Only Curiosity draws; no extra draw from Boomerang Basics resolution
    curiosity_draws = state.cards_drawn_per_noncreature_spell
    assert state.total_cards_drawn <= drawn_before + curiosity_draws


# ── Cave-In ───────────────────────────────────────────────────────────────────

def test_cave_in_generates_pitch_red():
    state = _state(["Cave-In", "Rite of Flame"], ManaPool())
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Cave-In"
            and a.alt_cost_type == "pitch_red"]
    assert len(acts) >= 1


def test_cave_in_pitch_exiles_red_card():
    state = _state(["Cave-In", "Rite of Flame"], ManaPool())
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Cave-In"
               and a.alt_cost_type == "pitch_red")
    resolve_action(state, act)
    assert "Rite of Flame" not in state.hand
    assert "Rite of Flame" in state.exile


def test_cave_in_cast_triggers_curiosity():
    state = _state(["Cave-In", "Rite of Flame"], ManaPool())
    spells_before = state.noncreature_spells_cast
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Cave-In"
               and a.alt_cost_type == "pitch_red")
    resolve_action(state, act)
    assert state.noncreature_spells_cast == spells_before + 1


def test_cave_in_kills_ragavan_on_resolve():
    state = _state(["Cave-In", "Rite of Flame"], ManaPool())
    state.battlefield.append(Permanent(card_name="Ragavan, Nimble Pilferer"))
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Cave-In"
               and a.alt_cost_type == "pitch_red")
    resolve_action(state, act)
    _drain_stack(state)
    assert not any(p.card_name == "Ragavan, Nimble Pilferer" for p in state.battlefield)


# ── Chain of Vapor ────────────────────────────────────────────────────────────

def test_chain_of_vapor_bounces_own_nonland():
    state = _state(["Chain of Vapor"], ManaPool(U=1))
    perm = Permanent(card_name="Mishra's Bauble")
    state.battlefield.append(perm)
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Chain of Vapor"
               and a.target == perm.perm_id)
    resolve_action(state, act)
    _drain_stack(state)
    assert "Mishra's Bauble" in state.hand


def test_chain_of_vapor_no_land_targets():
    state = _state(["Chain of Vapor"], ManaPool(U=1))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Chain of Vapor"]
    for act in acts:
        perm = state.get_perm_by_id(act.target) if act.target else None
        if perm:
            from mtg_sim.sim.cards import get_card
            cd = get_card(perm.card_name)
            assert cd is None or not cd.is_land


# ── Crowd's Favor ─────────────────────────────────────────────────────────────

def test_crowds_favor_requires_creature_target():
    state = _state(["Crowd's Favor"], ManaPool(R=1))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Crowd's Favor"]
    assert len(acts) >= 1
    assert all(a.requires_target and a.target is not None for a in acts)


def test_crowds_favor_convoke_taps_creature():
    state = _state(["Crowd's Favor"], ManaPool())
    # Vivi on battlefield untapped → should generate convoke action
    actions = generate_actions(state)
    convoke_acts = [a for a in actions if a.source_card == "Crowd's Favor"
                    and a.alt_cost_type and a.alt_cost_type.startswith("convoke:")]
    assert len(convoke_acts) >= 1
    act = convoke_acts[0]
    creature_id = act.alt_cost_type.split(":")[1]
    resolve_action(state, act)
    creature = state.get_perm_by_id(creature_id)
    if creature:
        assert creature.tapped, "Convoked creature should be tapped"


def test_crowds_favor_no_convoke_without_untapped_creature():
    state = _state(["Crowd's Favor"], ManaPool())
    # Tap Vivi
    for p in state.battlefield:
        if p.card_name == "Vivi Ornitier":
            p.tapped = True
    state._opponent_creature_perm = None  # no dummy either
    actions = generate_actions(state)
    convoke_acts = [a for a in actions if a.source_card == "Crowd's Favor"
                    and a.alt_cost_type and a.alt_cost_type.startswith("convoke:")]
    assert len(convoke_acts) == 0


# ── Gut Shot ──────────────────────────────────────────────────────────────────

def test_gut_shot_generates_free_life_cost():
    state = _state(["Gut Shot"], ManaPool())
    actions = generate_actions(state)
    free_acts = [a for a in actions if a.source_card == "Gut Shot"
                 and a.alt_cost_type == "pay_life"]
    assert len(free_acts) >= 1


def test_gut_shot_requires_target():
    state = _state(["Gut Shot"], ManaPool())
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Gut Shot"]
    assert len(acts) >= 1
    assert all(a.requires_target for a in acts)


def test_gut_shot_triggers_curiosity():
    state = _state(["Gut Shot"], ManaPool())
    spells_before = state.noncreature_spells_cast
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Gut Shot"
               and a.alt_cost_type == "pay_life")
    resolve_action(state, act)
    assert state.noncreature_spells_cast == spells_before + 1


# ── Pyrokinesis ───────────────────────────────────────────────────────────────

def test_pyrokinesis_requires_creature_target():
    state = _state(["Pyrokinesis", "Rite of Flame"], ManaPool())
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Pyrokinesis"]
    assert len(acts) >= 1
    assert all(a.requires_target and a.target is not None for a in acts)


def test_harmful_creature_spells_prune_own_vivi_when_dummy_target_exists():
    for card_name in ("Gut Shot", "Pyrokinesis", "Thunderclap"):
        mana = ManaPool(R=1, ANY=2) if card_name == "Thunderclap" else ManaPool()
        hand = [card_name, "Rite of Flame"] if card_name == "Pyrokinesis" else [card_name]
        state = _state(hand, mana)
        vivi_perm = next(p for p in state.battlefield if p.card_name == "Vivi Ornitier")
        actions = generate_actions(state)
        acts = [a for a in actions if a.source_card == card_name]
        assert acts
        assert all(a.target != vivi_perm.perm_id for a in acts)
        assert all(a.target == state._opponent_creature_perm.perm_id for a in acts)


def test_pyrokinesis_pitch_requires_red_card():
    state = _state(["Pyrokinesis"], ManaPool())
    actions = generate_actions(state)
    pitch_acts = [a for a in actions if a.source_card == "Pyrokinesis"
                  and a.alt_cost_type == "pitch_red"]
    assert len(pitch_acts) == 0, "No pitch actions without a red card in hand"


def test_pyrokinesis_pitch_exiles_red_card():
    state = _state(["Pyrokinesis", "Rite of Flame"], ManaPool())
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Pyrokinesis"
               and a.alt_cost_type == "pitch_red")
    resolve_action(state, act)
    assert "Rite of Flame" not in state.hand
    assert "Rite of Flame" in state.exile


# ── Redirect Lightning ────────────────────────────────────────────────────────

def test_redirect_lightning_no_actions_without_stack_target():
    state = _state(["Redirect Lightning"], ManaPool())
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Redirect Lightning"]
    assert len(acts) == 0, "Redirect Lightning needs a single-target stack object"


def test_redirect_lightning_generates_with_valid_stack_object():
    from mtg_sim.sim.stack import StackObject
    state = _state(["Redirect Lightning"], ManaPool(R=1))
    # Add a single-target spell to stack
    so = StackObject(card_name="Twisted Image", targets=["some_target"])
    state.stack.append(so)
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Redirect Lightning"]
    assert len(acts) >= 1
    assert acts[0].alt_cost_type == "pay_life"
    assert acts[0].costs.mana.pip_r == 1
    assert acts[0].costs.pay_life == 5


def test_redirect_lightning_requires_red_mana_with_valid_stack_object():
    from mtg_sim.sim.stack import StackObject
    state = _state(["Redirect Lightning"], ManaPool())
    state.stack.append(StackObject(card_name="Twisted Image", targets=["some_target"]))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Redirect Lightning"]
    assert len(acts) == 0


# ── Secret Identity ───────────────────────────────────────────────────────────

def test_secret_identity_requires_creature_target():
    state = _state(["Secret Identity"], ManaPool(U=1))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Secret Identity"]
    assert len(acts) >= 1
    assert all(a.requires_target for a in acts)


def test_secret_identity_sorcery_speed():
    from mtg_sim.sim.stack import StackObject
    state = _state(["Secret Identity"], ManaPool(U=1))
    state.stack.append(StackObject(card_name="Dummy"))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Secret Identity"]
    assert len(acts) == 0, "Secret Identity is sorcery speed"


def test_secret_identity_resolves_safely():
    state = _state(["Secret Identity"], ManaPool(U=1))
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Secret Identity")
    resolve_action(state, act)
    _drain_stack(state)


# ── Thunderclap ───────────────────────────────────────────────────────────────

def test_thunderclap_requires_creature_target():
    state = _state(["Thunderclap"], ManaPool(R=1, ANY=2))
    actions = generate_actions(state)
    acts = [a for a in actions if a.source_card == "Thunderclap"]
    assert len(acts) >= 1
    assert all(a.requires_target for a in acts)


def test_thunderclap_sac_mountain_cost():
    state = _state(["Thunderclap"], ManaPool())
    state.battlefield.append(Permanent(card_name="Mountain"))
    actions = generate_actions(state)
    sac_acts = [a for a in actions if a.source_card == "Thunderclap"
                and a.alt_cost_type == "sacrifice_mountain"]
    assert len(sac_acts) >= 1


def test_thunderclap_sac_mountain_moves_to_graveyard():
    state = _state(["Thunderclap"], ManaPool())
    # Count mountain-type lands before
    _MOUNTAIN_NAMES = {"Mountain", "Volcanic Island", "Steam Vents", "Thundering Falls"}
    before = sum(1 for p in state.battlefield if p.card_name in _MOUNTAIN_NAMES)
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Thunderclap"
               and a.alt_cost_type == "sacrifice_mountain")
    resolve_action(state, act)
    after = sum(1 for p in state.battlefield if p.card_name in _MOUNTAIN_NAMES)
    assert after == before - 1, "One Mountain-type land should be sacrificed as cast cost"


def test_thunderclap_kills_ragavan():
    state = _state(["Thunderclap"], ManaPool(R=1, ANY=2))
    ragavan = Permanent(card_name="Ragavan, Nimble Pilferer")
    state.battlefield.append(ragavan)
    actions = generate_actions(state)
    act = next(a for a in actions if a.source_card == "Thunderclap"
               and a.target == ragavan.perm_id)
    resolve_action(state, act)
    _drain_stack(state)
    assert not any(p.card_name == "Ragavan, Nimble Pilferer" for p in state.battlefield)
