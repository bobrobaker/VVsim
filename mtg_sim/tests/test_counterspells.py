"""Tests for counterspell mechanics: target removal from stack and Disrupting Shoal MV check."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool, ManaCost
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.actions import CAST_SPELL, RESOLVE_STACK_OBJECT
from mtg_sim.sim.stack import StackObject
from mtg_sim.sim.stack import StackObject
from random import Random


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def _state_with_hand(hand, mana, cards=None):
    if cards is None:
        cards = _load()
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=mana)
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    draw_cards(state, 3)
    return state


def _push_spell(state, card_name):
    """Put a spell on the stack without running through the full cast path."""
    obj = StackObject(card_name=card_name)
    state.stack.append(obj)
    return obj


# ── Counterspell removes target from stack ────────────────────────────────────

def test_force_of_will_counters_target():
    cards = _load()
    # Force of Will: free by pitching a blue card
    state = _state_with_hand(["Force of Will", "Pact of Negation"], ManaPool(U=1), cards)

    # Put something on the stack to target
    target_obj = _push_spell(state, "Gamble")
    target_id = target_obj.stack_id

    # Cast Force of Will targeting Gamble (find action)
    actions = generate_actions(state)
    fow_actions = [a for a in actions if a.source_card == "Force of Will"
                   and a.action_type == CAST_SPELL and a.target == target_id]
    assert len(fow_actions) >= 1, "Force of Will should be castable targeting Gamble on stack"

    fow_action = fow_actions[0]
    resolve_action(state, fow_action)

    # Stack: [Gamble, FoW, draw_trigger]; draw trigger resolves first
    assert any(o.card_name == "Force of Will" for o in state.stack)
    assert any(o.card_name == "Gamble" for o in state.stack)
    assert state.stack[-1].is_draw_trigger

    # Resolve the draw trigger (top of stack)
    dt_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, dt_act)

    # Now Force of Will is on top — resolve it
    resolve_actions = generate_actions(state)
    resolve_act = next(a for a in resolve_actions if a.action_type == RESOLVE_STACK_OBJECT
                       and a.source_card == "Force of Will")
    resolve_action(state, resolve_act)

    # Gamble should now be in the graveyard, not on the stack
    assert not any(o.card_name == "Gamble" for o in state.stack), \
        "Gamble should be removed from stack after being countered"
    assert "Gamble" in state.graveyard, "Countered spell should go to graveyard"


def test_countered_spell_goes_to_graveyard():
    cards = _load()
    state = _state_with_hand(["Swan Song"], ManaPool(U=1), cards)
    target_obj = _push_spell(state, "Rite of Flame")

    actions = generate_actions(state)
    cast_act = next(
        (a for a in actions if a.source_card == "Swan Song"
         and a.action_type == CAST_SPELL and a.target == target_obj.stack_id),
        None
    )
    assert cast_act is not None, "Swan Song should target Rite of Flame on stack"

    resolve_action(state, cast_act)

    # Resolve draw trigger (top of stack) before Swan Song
    dt_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, dt_act)

    # Now Swan Song is on top
    resolve_acts = generate_actions(state)
    resolve_act = next(a for a in resolve_acts if a.action_type == RESOLVE_STACK_OBJECT
                       and a.source_card == "Swan Song")
    resolve_action(state, resolve_act)

    assert "Rite of Flame" in state.graveyard
    assert not any(o.card_name == "Rite of Flame" for o in state.stack)


# ── Disrupting Shoal MV check ────────────────────────────────────────────────

def test_disrupting_shoal_counters_matching_mv():
    cards = _load()
    # Disrupting Shoal: pitch a blue card with MV=1 to counter a MV=1 spell
    # Need a blue MV=1 card — Mystical Tutor costs {U}, MV=1
    state = _state_with_hand(["Disrupting Shoal", "Mystical Tutor"], ManaPool(), cards)
    target_obj = _push_spell(state, "Lotus Petal")  # MV=0; won't match
    target_obj2 = _push_spell(state, "Twisted Image")  # MV=1; should match Mystical Tutor MV=1

    actions = generate_actions(state)
    shoal_acts = [a for a in actions if a.source_card == "Disrupting Shoal"
                  and a.action_type == CAST_SPELL]
    assert len(shoal_acts) >= 1, "Disrupting Shoal should generate actions"

    # Find action targeting Twisted Image with Mystical Tutor as pitch (MV=1 both)
    match_act = next(
        (a for a in shoal_acts
         if a.target == target_obj2.stack_id and a.costs.pitched_card == "Mystical Tutor"),
        None
    )
    assert match_act is not None, "Should generate Shoal action targeting MV=1 spell with MV=1 pitch"

    resolve_action(state, match_act)

    # Resolve draw trigger before Disrupting Shoal
    dt_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, dt_act)

    # Now resolve Disrupting Shoal
    resolve_acts = generate_actions(state)
    resolve_act = next(a for a in resolve_acts if a.action_type == RESOLVE_STACK_OBJECT
                       and a.source_card == "Disrupting Shoal")
    resolve_action(state, resolve_act)

    # Twisted Image should be countered
    assert "Twisted Image" in state.graveyard
    assert not any(o.card_name == "Twisted Image" for o in state.stack)


def test_disrupting_shoal_fails_mismatched_mv():
    cards = _load()
    # Pitch Mystical Tutor (MV=1) targeting Rite of Flame (MV=1) — should counter
    # Pitch Mystical Tutor (MV=1) targeting Gamble (MV=1) — should counter
    # But pitch Mystical Tutor (MV=1) vs Jeska's Will (MV=3) — should NOT counter
    state = _state_with_hand(["Disrupting Shoal", "Mystical Tutor"], ManaPool(), cards)
    target_obj = _push_spell(state, "Jeska's Will")  # MV=3

    actions = generate_actions(state)
    shoal_acts = [a for a in actions if a.source_card == "Disrupting Shoal"
                  and a.action_type == CAST_SPELL
                  and a.target == target_obj.stack_id
                  and a.costs.pitched_card == "Mystical Tutor"]
    # Actions should be generated (we generate regardless of MV match now)
    assert len(shoal_acts) >= 1, "Shoal should generate actions for any target"

    shoal_act = shoal_acts[0]
    resolve_action(state, shoal_act)

    # Resolve draw trigger before Disrupting Shoal
    dt_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, dt_act)

    # Now resolve Disrupting Shoal
    resolve_acts = generate_actions(state)
    resolve_act = next(a for a in resolve_acts if a.action_type == RESOLVE_STACK_OBJECT
                       and a.source_card == "Disrupting Shoal")
    resolve_action(state, resolve_act)

    # Jeska's Will should NOT be countered (MV mismatch: pitch=1, target=3)
    assert "Jeska's Will" in [o.card_name for o in state.stack], \
        "Jeska's Will should remain on stack when Shoal MV doesn't match"


def test_disrupting_shoal_targets_all_spells_not_just_mv_match():
    """Action generator should produce Shoal actions for all stack targets."""
    cards = _load()
    state = _state_with_hand(["Disrupting Shoal", "Mystical Tutor"], ManaPool(), cards)
    mv1_obj = _push_spell(state, "Lotus Petal")   # MV=0
    mv3_obj = _push_spell(state, "Jeska's Will")  # MV=3

    actions = generate_actions(state)
    shoal_acts = [a for a in actions if a.source_card == "Disrupting Shoal"
                  and a.action_type == CAST_SPELL]

    targeted_ids = {a.target for a in shoal_acts}
    # With LIFO, only top of stack (Jeska's Will) can be targeted via _get_any_stack_targets
    # Actually _get_any_stack_targets returns all stack objects; Shoal can target any
    assert mv3_obj.stack_id in targeted_ids, "Shoal should be able to target MV=3 spell"


# ── Curiosity draw trigger is not a counterspell target ───────────────────────

def test_draw_trigger_not_a_counterspell_target():
    cards = _load()
    state = _state_with_hand(["Force of Will", "Pact of Negation"], ManaPool(U=1), cards)
    from mtg_sim.sim.stack import StackObject
    # Push a draw trigger onto the stack
    draw_trig = StackObject(card_name="_draw_trigger", is_draw_trigger=True, draw_count=1)
    state.stack.append(draw_trig)
    actions = generate_actions(state)
    fow_acts = [a for a in actions if a.source_card == "Force of Will" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in fow_acts}
    assert draw_trig.stack_id not in targeted_ids, "Draw trigger should not be a legal counterspell target"


# ── LIFO: only top stack object gets RESOLVE_STACK_OBJECT action ──────────────

def test_lifo_only_top_resolves():
    cards = _load()
    state = _state_with_hand([], ManaPool(), cards)
    bottom = _push_spell(state, "Gamble")
    top = _push_spell(state, "Rite of Flame")
    actions = generate_actions(state)
    resolve_acts = [a for a in actions if a.action_type == RESOLVE_STACK_OBJECT]
    assert len(resolve_acts) == 1
    assert resolve_acts[0].target == top.stack_id, "Only top stack object should be resolvable"


# ── Instants can be cast while stack is nonempty ──────────────────────────────

def test_instant_castable_with_stack():
    cards = _load()
    state = _state_with_hand(["Pact of Negation"], ManaPool(), cards)
    _push_spell(state, "Gamble")  # stack is nonempty
    actions = generate_actions(state)
    pact_acts = [a for a in actions if a.source_card == "Pact of Negation" and a.action_type == CAST_SPELL]
    assert len(pact_acts) >= 1, "Instant should be castable while stack is nonempty"


# ── An Offer You Can't Refuse ─────────────────────────────────────────────────

def _resolve_top(state):
    """Helper: resolve the top stack object."""
    acts = generate_actions(state)
    act = next(a for a in acts if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, act)


def test_an_offer_only_targets_noncreature():
    cards = _load()
    state = _state_with_hand(["An Offer You Can't Refuse"], ManaPool(U=1), cards)
    inst = _push_spell(state, "Rite of Flame")   # sorcery, noncreature ✓
    # Vivi is a creature but not on stack; push a creature spell to stack to test filter
    from mtg_sim.sim.stack import StackObject
    from mtg_sim.sim.cards import get_card
    # Use Hullbreaker Horror as a creature spell placeholder on stack
    creature_obj = StackObject(card_name="Hullbreaker Horror")
    state.stack.append(creature_obj)
    actions = generate_actions(state)
    offer_acts = [a for a in actions if a.source_card == "An Offer You Can't Refuse" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in offer_acts}
    assert inst.stack_id in targeted_ids, "Should target noncreature spell"
    assert creature_obj.stack_id not in targeted_ids, "Should not target creature spell"


def test_an_offer_creates_treasures():
    cards = _load()
    state = _state_with_hand(["An Offer You Can't Refuse"], ManaPool(U=1), cards)
    target = _push_spell(state, "Rite of Flame")
    resolve_action(state, next(a for a in generate_actions(state)
                               if a.source_card == "An Offer You Can't Refuse" and a.action_type == CAST_SPELL))
    # Resolve draw trigger then the counterspell
    _resolve_top(state)  # draw trigger
    _resolve_top(state)  # An Offer You Can't Refuse
    assert "Rite of Flame" in state.graveyard, "Target should be countered"
    treasures = [p for p in state.battlefield if p.card_name == "_Treasure"]
    assert len(treasures) == 2, "Should create 2 Treasure tokens"


# ── Commandeer ────────────────────────────────────────────────────────────────

def test_commandeer_only_targets_noncreature():
    cards = _load()
    # Commandeer pitch requires two blue cards
    state = _state_with_hand(["Commandeer", "Force of Will", "Pact of Negation"], ManaPool(), cards)
    inst = _push_spell(state, "Rite of Flame")
    creature_obj = StackObject(card_name="Hullbreaker Horror")
    state.stack.append(creature_obj)
    actions = generate_actions(state)
    cmd_acts = [a for a in actions if a.source_card == "Commandeer" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in cmd_acts}
    assert inst.stack_id in targeted_ids, "Commandeer should target noncreature spells"
    assert creature_obj.stack_id not in targeted_ids, "Commandeer should not target creature spells"


def test_commandeer_does_not_counter_target():
    cards = _load()
    state = _state_with_hand(["Commandeer", "Force of Will", "Pact of Negation"], ManaPool(), cards)
    target = _push_spell(state, "Rite of Flame")
    acts = generate_actions(state)
    cmd_act = next((a for a in acts if a.source_card == "Commandeer" and a.action_type == CAST_SPELL
                    and a.target == target.stack_id), None)
    assert cmd_act is not None, "Commandeer should generate an action"
    resolve_action(state, cmd_act)
    _resolve_top(state)  # draw trigger
    _resolve_top(state)  # Commandeer
    assert any(o.card_name == "Rite of Flame" for o in state.stack), \
        "Target should remain on stack (not countered)"


def test_commandeer_pitch_exiles_pitched_cards():
    cards = _load()
    state = _state_with_hand(["Commandeer", "Force of Will", "Pact of Negation"], ManaPool(), cards)
    target = _push_spell(state, "Rite of Flame")
    acts = generate_actions(state)
    pitch_acts = [a for a in acts if a.source_card == "Commandeer"
                  and a.action_type == CAST_SPELL and a.alt_cost_type == "pitch_blue_blue"]
    assert len(pitch_acts) >= 1, "Commandeer should generate pitch-two-blue actions"
    act = pitch_acts[0]
    resolve_action(state, act)
    assert act.costs.pitched_card in state.exile, "First pitched card should go to exile"
    assert act.costs.pitched_card_2 in state.exile, "Second pitched card should go to exile"


# ── Deflecting Swat ───────────────────────────────────────────────────────────

def test_deflecting_swat_free_with_vivi():
    cards = _load()
    state = _state_with_hand(["Deflecting Swat"], ManaPool(), cards)
    # Put a spell with a target on the stack (use a counterspell targeting something)
    from mtg_sim.sim.stack import StackObject
    target_of_spell = _push_spell(state, "Gamble")
    spell_with_target = StackObject(card_name="Force of Will", targets=[target_of_spell.stack_id])
    state.stack.append(spell_with_target)
    state.vivi_on_battlefield = True
    actions = generate_actions(state)
    swat_acts = [a for a in actions if a.source_card == "Deflecting Swat" and a.action_type == CAST_SPELL]
    assert any(a.alt_cost_type == "commander_free" for a in swat_acts), \
        "Deflecting Swat should be free with Vivi"


def test_deflecting_swat_no_action_without_target():
    cards = _load()
    state = _state_with_hand(["Deflecting Swat"], ManaPool(), cards)
    # Stack is empty: no targets
    actions = generate_actions(state)
    swat_acts = [a for a in actions if a.source_card == "Deflecting Swat" and a.action_type == CAST_SPELL]
    assert len(swat_acts) == 0, "No Deflecting Swat action without a legal target"


def test_deflecting_swat_does_not_counter_target():
    cards = _load()
    state = _state_with_hand(["Deflecting Swat"], ManaPool(R=3))
    from mtg_sim.sim.stack import StackObject
    inner = _push_spell(state, "Gamble")
    outer = StackObject(card_name="Force of Will", targets=[inner.stack_id])
    state.stack.append(outer)
    state.vivi_on_battlefield = True
    acts = generate_actions(state)
    swat_act = next((a for a in acts if a.source_card == "Deflecting Swat"), None)
    assert swat_act is not None
    resolve_action(state, swat_act)
    _resolve_top(state)  # draw trigger
    _resolve_top(state)  # Deflecting Swat
    assert any(o.card_name == "Force of Will" for o in state.stack), \
        "Target should remain on stack (not countered)"


# ── Fierce Guardianship ───────────────────────────────────────────────────────

def test_fierce_guardianship_only_targets_noncreature():
    cards = _load()
    state = _state_with_hand(["Fierce Guardianship"], ManaPool())
    creature_obj = StackObject(card_name="Hullbreaker Horror")
    state.stack.append(creature_obj)
    state.vivi_on_battlefield = True
    actions = generate_actions(state)
    fg_acts = [a for a in actions if a.source_card == "Fierce Guardianship" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in fg_acts}
    assert creature_obj.stack_id not in targeted_ids, "Fierce Guardianship should not target creature spells"


def test_fierce_guardianship_free_with_vivi():
    cards = _load()
    state = _state_with_hand(["Fierce Guardianship"], ManaPool())
    target = _push_spell(state, "Rite of Flame")
    state.vivi_on_battlefield = True
    actions = generate_actions(state)
    fg_acts = [a for a in actions if a.source_card == "Fierce Guardianship" and a.action_type == CAST_SPELL]
    assert any(a.alt_cost_type == "commander_free" for a in fg_acts), \
        "Fierce Guardianship should be free with Vivi"


def test_fierce_guardianship_counters_target():
    cards = _load()
    state = _state_with_hand(["Fierce Guardianship"], ManaPool())
    target = _push_spell(state, "Rite of Flame")
    state.vivi_on_battlefield = True
    act = next(a for a in generate_actions(state) if a.source_card == "Fierce Guardianship" and a.action_type == CAST_SPELL)
    resolve_action(state, act)
    _resolve_top(state)  # draw trigger
    _resolve_top(state)  # Fierce Guardianship
    assert "Rite of Flame" in state.graveyard
    assert not any(o.card_name == "Rite of Flame" for o in state.stack)


# ── Misdirection ──────────────────────────────────────────────────────────────

def test_misdirection_does_not_counter_target():
    cards = _load()
    state = _state_with_hand(["Misdirection", "Force of Will"], ManaPool())
    inner = _push_spell(state, "Gamble")
    outer = StackObject(card_name="Pact of Negation", targets=[inner.stack_id])
    state.stack.append(outer)
    # Misdirection via pitch-blue targeting outer (which has one target)
    acts = generate_actions(state)
    misd_acts = [a for a in acts if a.source_card == "Misdirection" and a.action_type == CAST_SPELL]
    assert len(misd_acts) >= 1, "Misdirection should generate actions"
    resolve_action(state, misd_acts[0])
    _resolve_top(state)  # draw trigger
    _resolve_top(state)  # Misdirection
    assert any(o.card_name == "Pact of Negation" for o in state.stack), \
        "Misdirection should not counter its target"


def test_misdirection_only_targets_single_target_spells():
    cards = _load()
    state = _state_with_hand(["Misdirection", "Force of Will"], ManaPool())
    no_target_spell = _push_spell(state, "Rite of Flame")  # has no targets
    acts = generate_actions(state)
    misd_acts = [a for a in acts if a.source_card == "Misdirection" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in misd_acts}
    assert no_target_spell.stack_id not in targeted_ids, \
        "Misdirection should not target spells without targets"


# ── Pyroblast ─────────────────────────────────────────────────────────────────

def test_pyroblast_targets_blue_spell():
    cards = _load()
    state = _state_with_hand(["Pyroblast"], ManaPool(R=1))
    blue_spell = _push_spell(state, "Force of Will")  # blue spell
    red_spell = _push_spell(state, "Rite of Flame")   # red, not blue
    acts = generate_actions(state)
    pyro_acts = [a for a in acts if a.source_card == "Pyroblast" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in pyro_acts}
    assert blue_spell.stack_id in targeted_ids, "Pyroblast should target blue spells"
    assert red_spell.stack_id not in targeted_ids, "Pyroblast should not target non-blue spells"


def test_pyroblast_counters_blue_spell():
    cards = _load()
    state = _state_with_hand(["Pyroblast"], ManaPool(R=1))
    target = _push_spell(state, "Force of Will")
    act = next(a for a in generate_actions(state) if a.source_card == "Pyroblast" and a.action_type == CAST_SPELL)
    resolve_action(state, act)
    _resolve_top(state)  # draw trigger
    _resolve_top(state)  # Pyroblast
    assert "Force of Will" in state.graveyard
    assert not any(o.card_name == "Force of Will" for o in state.stack)


# ── Mental Misstep targets only MV=1 ─────────────────────────────────────────

def test_mental_misstep_only_mv1():
    cards = _load()
    state = _state_with_hand(["Mental Misstep"], ManaPool())
    mv1 = _push_spell(state, "Twisted Image")   # MV=1
    mv3 = _push_spell(state, "Jeska's Will")    # MV=3
    acts = generate_actions(state)
    mm_acts = [a for a in acts if a.source_card == "Mental Misstep" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in mm_acts}
    assert mv1.stack_id in targeted_ids, "Mental Misstep should target MV=1 spells"
    assert mv3.stack_id not in targeted_ids, "Mental Misstep should not target MV=3 spells"


# ── Swan Song targets only enchantment/instant/sorcery ───────────────────────

def test_swan_song_filter():
    cards = _load()
    state = _state_with_hand(["Swan Song"], ManaPool(U=1))
    inst = _push_spell(state, "Rite of Flame")   # sorcery ✓
    creature_obj = StackObject(card_name="Hullbreaker Horror")
    state.stack.append(creature_obj)
    acts = generate_actions(state)
    ss_acts = [a for a in acts if a.source_card == "Swan Song" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in ss_acts}
    assert inst.stack_id in targeted_ids, "Swan Song should target sorceries"
    assert creature_obj.stack_id not in targeted_ids, "Swan Song should not target creature spells"


# ── Flusterstorm targets only instant/sorcery ────────────────────────────────

def test_flusterstorm_filter():
    cards = _load()
    state = _state_with_hand(["Flusterstorm"], ManaPool(U=1))
    inst = _push_spell(state, "Rite of Flame")   # sorcery ✓
    # Curiosity is an enchantment — should be excluded
    from mtg_sim.sim.stack import StackObject
    ench_obj = StackObject(card_name="Curiosity")
    state.stack.append(ench_obj)
    acts = generate_actions(state)
    fl_acts = [a for a in acts if a.source_card == "Flusterstorm" and a.action_type == CAST_SPELL]
    targeted_ids = {a.target for a in fl_acts}
    assert inst.stack_id in targeted_ids, "Flusterstorm should target sorceries"
    assert ench_obj.stack_id not in targeted_ids, "Flusterstorm should not target enchantments"


# ── Daze alt cost returns island ──────────────────────────────────────────────

def test_daze_alt_cost_returns_island():
    cards = _load()
    from mtg_sim.sim.state import Permanent
    state = _state_with_hand(["Daze"], ManaPool())
    # Put an untapped Island on battlefield
    island = Permanent(card_name="Island", tapped=False)
    state.battlefield.append(island)
    target = _push_spell(state, "Rite of Flame")
    acts = generate_actions(state)
    daze_acts = [a for a in acts if a.source_card == "Daze" and a.action_type == CAST_SPELL]
    alt_acts = [a for a in daze_acts if a.alt_cost_type == "return_island"]
    assert len(alt_acts) >= 1, "Daze should generate return-island alt cost action"


def test_daze_alt_cost_tapped_island_eligible():
    # manual_observations.jsonl:51 — Volcanic Island tapped, Daze in hand, spell on stack
    # Returning an island for Daze does not require the island to be untapped.
    _load()
    state = _state_with_hand(["Daze"], ManaPool(R=1))
    # Default battlefield has a tapped Volcanic Island; confirm Daze sees it.
    island_ids = {p.perm_id for p in state.battlefield if p.card_name == "Volcanic Island" and p.tapped}
    assert island_ids, "Precondition: tapped Volcanic Island must be on battlefield"
    _push_spell(state, "Mishra's Bauble")
    acts = generate_actions(state)
    alt_acts = [a for a in acts if a.source_card == "Daze" and a.alt_cost_type == "return_island"]
    assert len(alt_acts) >= 1, "Daze should allow returning a tapped Volcanic Island"
    assert alt_acts[0].costs.tap_permanent_id in island_ids


# ── Countered flashback spell goes to exile ───────────────────────────────────

def test_countered_flashback_goes_to_exile():
    cards = _load()
    state = _state_with_hand(["Force of Will", "Pact of Negation"], ManaPool(U=1))
    # Simulate a flashback spell on stack
    flash_obj = StackObject(card_name="Gamble", alt_cost_used="flashback")
    state.stack.append(flash_obj)
    act = next(a for a in generate_actions(state) if a.source_card == "Force of Will"
               and a.action_type == CAST_SPELL and a.target == flash_obj.stack_id)
    resolve_action(state, act)
    _resolve_top(state)  # draw trigger
    _resolve_top(state)  # Force of Will
    assert "Gamble" in state.exile, "Countered flashback spell should go to exile"
    assert "Gamble" not in state.graveyard


# ── Countering a spell preserves already-created Curiosity draw trigger ───────

def test_countering_preserves_draw_trigger():
    cards = _load()
    state = _state_with_hand(["Pact of Negation"], ManaPool())
    target = _push_spell(state, "Rite of Flame")
    # Manually add a draw trigger as if Curiosity fired for target
    draw_trig = StackObject(card_name="_draw_trigger", is_draw_trigger=True, draw_count=1)
    state.stack.append(draw_trig)
    # Cast Pact of Negation targeting Rite of Flame
    act = next(a for a in generate_actions(state) if a.source_card == "Pact of Negation"
               and a.action_type == CAST_SPELL and a.target == target.stack_id)
    resolve_action(state, act)
    # Resolve Pact (on top)
    _resolve_top(state)  # Pact draw trigger
    _resolve_top(state)  # Pact of Negation
    # Draw trigger for Rite should still be on stack
    assert any(o.is_draw_trigger for o in state.stack), \
        "Curiosity draw trigger should survive after target is countered"
