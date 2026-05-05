"""
LED pre-draw timing tests — stack-based Curiosity trigger model.

MTG rules modelled:
  1. Casting a noncreature spell → Vivi deals 1 damage to each opponent →
     each active Curiosity-like effect triggers once per opponent damaged →
     one "_DrawTrigger" stack object (draw_count = curiosity_count * OPPONENT_COUNT)
     is placed above the spell on the stack (LIFO).
  2. The draw trigger on top resolves before the spell below it; this is automatic
     because RESOLVE_STACK_OBJECT only ever offers the top-of-stack object.
  3. Mana abilities (LED crack) are legal any time you hold priority,
     including while draw triggers are on the stack.
  4. Instants can be cast while draw triggers are on the stack, adding more triggers.
     Sorceries cannot be cast while the stack is non-empty.
  5. LED payoff: cast spells to accumulate draw triggers, crack LED to discard
     a near-empty hand, then resolve draw triggers into fresh cards.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.policies import choose_action, score_action
from mtg_sim.sim.stack import StackObject
from mtg_sim.sim.actions import (
    Action, CostBundle,
    CAST_SPELL, RESOLVE_STACK_OBJECT, SACRIFICE_FOR_MANA,
    RISK_SAFE, RISK_NORMAL,
)
from random import Random

_LIBRARY = [
    "Sol Ring", "Mana Vault", "Grim Monolith", "Lotus Petal",
    "Mox Amber", "Swan Song", "Daze", "Force of Will",
    "Flusterstorm", "Rite of Flame", "Strike It Rich", "Gamble",
    "Mystical Tutor", "Merchant Scroll", "Solve the Equation",
    "Twisted Image", "Mox Diamond", "Mox Opal",
    "Springleaf Drum", "Chrome Mox",
]


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def _cast(card_name: str, *, alt_cost_type=None, target=None) -> Action:
    return Action(
        action_type=CAST_SPELL,
        source_card=card_name,
        description=f"Cast {card_name}",
        costs=CostBundle(),
        risk_level=RISK_SAFE,
        alt_cost_type=alt_cost_type,
        target=target,
    )


def _make_state(starting_hand, starting_battlefield=None, floating_mana=None):
    cards = _load()
    bf = starting_battlefield or ["Volcanic Island"]
    mana = floating_mana or ManaPool(U=1)
    cfg = RunConfig(
        seed=1,
        starting_hand=starting_hand,
        starting_battlefield=bf,
        starting_floating_mana=mana,
        library_order=_LIBRARY,
    )
    return _build_initial_state(cfg, cards, Random(1))


# ── Draw trigger placement ────────────────────────────────────────────────────

def test_draw_trigger_placed_above_spell():
    """Casting a noncreature spell adds a draw trigger above it on the stack."""
    state = _make_state(["Mishra's Bauble"])

    resolve_action(state, _cast("Mishra's Bauble"))

    # Stack order (bottom to top): Bauble, draw_trigger
    assert len(state.stack) == 2
    assert state.stack[0].card_name == "Mishra's Bauble"
    top = state.stack[-1]
    assert top.is_draw_trigger
    assert top.draw_count == 3
    assert state.pending_curiosity_draws == 3

    # Only the draw trigger (top) can be resolved now
    acts = generate_actions(state)
    resolve_acts = [a for a in acts if a.action_type == RESOLVE_STACK_OBJECT]
    assert len(resolve_acts) == 1
    assert resolve_acts[0].target == top.stack_id


def test_spell_resolves_after_draw_trigger():
    """Once the draw trigger resolves, the spell below becomes the top and is resolvable."""
    state = _make_state(["Mishra's Bauble"])

    resolve_action(state, _cast("Mishra's Bauble"))
    assert state.stack[-1].is_draw_trigger

    # Resolve the draw trigger
    dt_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, dt_act)
    assert state.pending_curiosity_draws == 0

    # Now Bauble is on top and resolvable
    acts = generate_actions(state)
    resolve_acts = [a for a in acts if a.action_type == RESOLVE_STACK_OBJECT]
    assert len(resolve_acts) == 1
    assert resolve_acts[0].source_card == "Mishra's Bauble"


# ── Instant stacks an additional draw trigger ─────────────────────────────────

def test_instant_adds_draw_trigger_above_existing():
    """
    Casting an instant while a draw trigger is on the stack adds another trigger above it.
    Stack order: [Bauble, DT_Bauble, Pact, DT_Pact]
    """
    state = _make_state(["Mishra's Bauble", "Pact of Negation"])

    resolve_action(state, _cast("Mishra's Bauble"))
    assert len(state.stack) == 2  # [Bauble, DT_Bauble]

    bauble_id = state.stack[0].stack_id
    resolve_action(state, _cast("Pact of Negation",
                                alt_cost_type="delayed_upkeep",
                                target=bauble_id))

    # Stack: [Bauble, DT_Bauble, Pact, DT_Pact]
    assert len(state.stack) == 4
    assert state.stack[0].card_name == "Mishra's Bauble"
    assert state.stack[1].is_draw_trigger
    assert state.stack[2].card_name == "Pact of Negation"
    assert state.stack[3].is_draw_trigger
    assert state.pending_curiosity_draws == 6  # two spells × 3


def test_sorcery_cannot_be_cast_while_stack_nonempty():
    """Sorceries (and sorcery-speed spells) cannot be cast while anything is on the stack."""
    state = _make_state(["Mishra's Bauble", "Vexing Bauble"])

    resolve_action(state, _cast("Mishra's Bauble"))
    assert state.stack  # Bauble + draw trigger

    acts = generate_actions(state)
    cast_names = {a.source_card for a in acts if a.action_type == CAST_SPELL}
    assert "Vexing Bauble" not in cast_names, (
        "Vexing Bauble (sorcery-speed) must not be castable while stack is non-empty"
    )


# ── Full LED pre-draw sequence ────────────────────────────────────────────────

def test_led_crack_then_draw_full_sequence():
    """
    Full LED pre-draw sequence:
      1. Cast Mishra's Bauble  → stack: [Bauble, DT(3)]
      2. Cast Pact of Negation → stack: [Bauble, DT(3), Pact, DT(3)]; hand now empty
      3. Crack LED (hand=[] → discard nothing, gain 3R)
      4. Resolve DT_Pact (top) → draw 3 cards
      5. Resolve Pact → counters Bauble; stack: [DT_Bauble]
      6. Resolve DT_Bauble → draw 3 more cards
    Total: 6 cards drawn into a fresh hand.
    """
    cards = _load()
    cfg = RunConfig(
        seed=1,
        starting_hand=["Mishra's Bauble", "Pact of Negation"],
        starting_battlefield=["Volcanic Island", "Lion's Eye Diamond"],
        starting_floating_mana=ManaPool(U=1),
        library_order=_LIBRARY,
    )
    state = _build_initial_state(cfg, cards, Random(1))

    # Step 1
    resolve_action(state, _cast("Mishra's Bauble"))
    assert state.pending_curiosity_draws == 3

    # Step 2
    bauble_id = state.stack[0].stack_id
    resolve_action(state, _cast("Pact of Negation",
                                alt_cost_type="delayed_upkeep",
                                target=bauble_id))
    assert state.pending_curiosity_draws == 6
    assert state.hand == [], f"Both spells cast; hand should be empty, got {state.hand}"

    # Verify: LED crack is available while draw triggers are on the stack
    actions = generate_actions(state)
    types = {a.action_type for a in actions}
    assert SACRIFICE_FOR_MANA in types, "LED crack must be legal while draw triggers are on stack"
    assert RESOLVE_STACK_OBJECT in types, "Draw trigger resolution must be available"

    # Step 3: crack LED (discard empty hand → gain 3R)
    led_action = next(
        a for a in actions
        if a.action_type == SACRIFICE_FOR_MANA and a.source_card == "Lion's Eye Diamond"
        and "RRR" in a.description
    )
    resolve_action(state, led_action)
    assert state.hand == []
    assert state.pending_curiosity_draws == 6, "LED crack must not change pending draws"
    assert state.floating_mana.R == 3

    # Step 4: resolve DT_Pact (top of stack)
    dt_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    assert state.get_stack_object(dt_act.target).is_draw_trigger
    resolve_action(state, dt_act)
    assert len(state.hand) == 3

    # Step 5: resolve Pact (now on top) → counters Bauble
    pact_act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    assert pact_act.source_card == "Pact of Negation"
    resolve_action(state, pact_act)
    assert not any(o.card_name == "Mishra's Bauble" for o in state.stack)

    # Step 6: resolve DT_Bauble (now on top)
    remaining = [a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT]
    assert len(remaining) == 1
    resolve_action(state, remaining[0])
    assert state.pending_curiosity_draws == 0
    assert len(state.hand) == 6, f"Expected 6 cards drawn total; got {len(state.hand)}"


# ── Policy scoring ────────────────────────────────────────────────────────────

def test_policy_prefers_led_crack_over_resolve_when_hand_small():
    """With a draw trigger on stack and hand ≤1 card, LED crack (88) outscores draw-trigger resolve (30)."""
    cards = _load()
    cfg = RunConfig(
        seed=1,
        starting_hand=[],
        starting_battlefield=["Volcanic Island", "Lion's Eye Diamond"],
        starting_floating_mana=ManaPool(U=1),
        library_order=_LIBRARY,
    )
    state = _build_initial_state(cfg, cards, Random(1))
    # Manually push a draw trigger (simulates having cast two spells)
    state.stack.append(StackObject(card_name="_DrawTrigger", is_draw_trigger=True, draw_count=6))

    actions = generate_actions(state)
    led_actions = [
        a for a in actions
        if a.action_type == SACRIFICE_FOR_MANA and a.source_card == "Lion's Eye Diamond"
    ]
    resolve_draw_actions = [
        a for a in actions
        if a.action_type == RESOLVE_STACK_OBJECT
        and state.get_stack_object(a.target) is not None
        and state.get_stack_object(a.target).is_draw_trigger
    ]

    assert led_actions, "LED crack must be available"
    assert resolve_draw_actions, "Draw trigger resolution must be available"

    led_score = score_action(state, led_actions[0])
    resolve_score = score_action(state, resolve_draw_actions[0])

    assert led_score > resolve_score, (
        f"Empty hand + pending draws: LED ({led_score}) should beat "
        f"draw-trigger resolve ({resolve_score})"
    )


def test_led_crack_heuristic_only_fires_with_small_hand():
    """
    _led_crack_is_better must return False when hand has > 1 card,
    and True when hand has 0 or 1 card (with a draw trigger on stack and LED on battlefield).
    """
    from mtg_sim.sim.policies import _led_crack_is_better
    cards = _load()
    cfg = RunConfig(
        seed=1,
        starting_hand=[],
        starting_battlefield=["Volcanic Island", "Lion's Eye Diamond"],
        starting_floating_mana=ManaPool(U=1),
        library_order=_LIBRARY,
    )
    state = _build_initial_state(cfg, cards, Random(1))
    state.stack.append(StackObject(card_name="_DrawTrigger", is_draw_trigger=True, draw_count=6))

    state.hand = ["Misdirection", "Force of Will", "Swan Song", "Flusterstorm"]
    assert not _led_crack_is_better(state), "Heuristic must not fire with 4 cards in hand"

    state.hand = ["Misdirection"]
    assert _led_crack_is_better(state), "Heuristic must fire with 1 card in hand"

    state.hand = []
    assert _led_crack_is_better(state), "Heuristic must fire with empty hand"
