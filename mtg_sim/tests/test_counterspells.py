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


def _state_with_hand(hand, mana, cards):
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
