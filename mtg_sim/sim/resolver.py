"""Apply actions to mutate GameState."""
from __future__ import annotations
from typing import TYPE_CHECKING
from .mana import pay_cost, choose_mana_color
from .actions import (
    CAST_SPELL, RESOLVE_STACK_OBJECT, PLAY_LAND,
    ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA, SACRIFICE_FOR_MANA,
    CHOOSE_IMPRINT, CHOOSE_DISCARD, CHOOSE_TUTOR,
    EXTRA_TURN_WIN_CARDS,
)
from .stack import StackObject
from .state import ActionLog, Permanent
from .card_behaviors import CARD_BEHAVIORS

if TYPE_CHECKING:
    from .state import GameState
    from .actions import Action


# ── Public: draw cards ────────────────────────────────────────────────────────

def draw_cards(state: GameState, n: int) -> list[str]:
    drawn = []
    for _ in range(n):
        if not state.library:
            break
        card = state.library.pop(0)
        state.hand.append(card)
        drawn.append(card)
    state.total_cards_drawn += len(drawn)
    return drawn


# ── Main resolver ─────────────────────────────────────────────────────────────

def resolve_action(state: GameState, action: Action) -> None:
    step = len(state.trace) + 1
    mana_before = state.floating_mana.copy()
    hand_before = len(state.hand)
    stack_snap = [str(o) for o in state.stack]

    log = ActionLog(
        step=step,
        event_type=action.action_type,
        action_description=action.description,
        mana_before=mana_before,
        hand_size_before=hand_before,
        noncreature_spells_cast=state.noncreature_spells_cast,
        stack_snapshot=stack_snap,
    )
    state.trace.append(log)

    if action.action_type == CAST_SPELL:
        _resolve_cast_spell(state, action, log)
    elif action.action_type == RESOLVE_STACK_OBJECT:
        _resolve_stack_object(state, action, log)
    elif action.action_type == PLAY_LAND:
        _resolve_play_land(state, action, log)
    elif action.action_type == ACTIVATE_MANA_ABILITY:
        _resolve_activate_mana(state, action, log)
    elif action.action_type == EXILE_FOR_MANA:
        _resolve_exile_for_mana(state, action, log)
    elif action.action_type == SACRIFICE_FOR_MANA:
        _resolve_sacrifice_for_mana(state, action, log)
    elif action.action_type == CHOOSE_IMPRINT:
        _resolve_choose_imprint(state, action, log)
    elif action.action_type == CHOOSE_DISCARD:
        _resolve_choose_discard(state, action, log)
    elif action.action_type == CHOOSE_TUTOR:
        _resolve_choose_tutor(state, action, log)

    log.mana_after = state.floating_mana.copy()
    log.hand_size_after = len(state.hand)


# ── Cast spell ────────────────────────────────────────────────────────────────

def _resolve_cast_spell(state: GameState, action: Action, log: ActionLog) -> None:
    from .cards import get_card

    card_name = action.source_card
    cd = get_card(card_name) if card_name else None

    # Pay mana cost
    if action.costs.mana.total_mana > 0:
        state.floating_mana = pay_cost(state.floating_mana, action.costs.mana)

    # Pay pitched card cost
    pitched = action.costs.pitched_card
    if pitched:
        _remove_one(state.hand, pitched)
        state.exile.append(pitched)
        log.notes.append(f"Pitched {pitched}")

    # For pitch_blue_blue (Commandeer): both pitched cards are encoded in the action
    if action.alt_cost_type == "pitch_blue_blue" and action.costs.pitched_card_2:
        _remove_one(state.hand, action.costs.pitched_card_2)
        state.exile.append(action.costs.pitched_card_2)
        log.notes.append(f"Pitched second blue: {action.costs.pitched_card_2}")

    # Pay exile_from_hand cost (Simian Spirit Guide via CAST path - not needed for SSG which is EXILE_FOR_MANA)
    if action.costs.exile_from_hand:
        _remove_one(state.hand, action.costs.exile_from_hand)
        state.exile.append(action.costs.exile_from_hand)

    # Return island to hand (Daze alt cost)
    if action.costs.return_land_to_hand and action.costs.tap_permanent_id:
        perm = state.remove_perm_by_id(action.costs.tap_permanent_id)
        if perm:
            state.hand.append(perm.card_name)
            log.notes.append(f"Returned {perm.card_name} to hand (Daze)")

    # Remove from hand / exile (depending on source zone)
    if action.alt_cost_type == "exile_permission":
        # Cast from exile
        _remove_one(state.exile, card_name)
        _remove_permission(state, card_name)
    elif card_name and card_name in state.hand:
        _remove_one(state.hand, card_name)
    elif action.alt_cost_type == "flashback":
        _remove_one(state.graveyard, card_name)
        # Goes to exile on resolution (handled later)

    # LED: discard hand before adding mana
    if card_name == "Lion's Eye Diamond" and action.action_type == CAST_SPELL:
        pass  # LED just enters battlefield; special action is SACRIFICE_FOR_MANA

    # Put on stack
    target_name = _lookup_target_name(state, action.target)
    obj = StackObject(
        card_name=card_name or "",
        targets=[action.target] if action.target else [],
        target_names=[target_name] if target_name else [],
        x_value=action.x_value,
        alt_cost_used=action.alt_cost_type,
        pitched_card=pitched,
    )
    state.stack.append(obj)
    state.total_spells_cast += 1

    log.event_type = "CAST_SPELL"

    # Noncreature spell: Vivi deals damage → Curiosity triggers → one draw-trigger stack
    # object placed above the spell, representing draw_count draws to be taken on resolution.
    if cd and cd.is_noncreature_spell:
        state.noncreature_spells_cast += 1
        n = state.cards_drawn_per_noncreature_spell
        draw_trigger = StackObject(
            card_name="_DrawTrigger",
            is_draw_trigger=True,
            draw_count=n,
        )
        state.stack.append(draw_trigger)
        log.notes.append(
            f"Curiosity: draw trigger ({n} draws) placed above {card_name} on stack "
            f"(noncreature cast: {state.noncreature_spells_cast})"
        )


# ── Resolve stack object ──────────────────────────────────────────────────────

def _resolve_stack_object(state: GameState, action: Action, log: ActionLog) -> None:
    from .cards import get_card

    stack_id = action.target
    if stack_id is None:
        log.notes.append("RESOLVE: no stack_id provided")
        return

    obj = state.remove_stack_object(stack_id)
    if obj is None:
        log.notes.append(f"RESOLVE: object {stack_id} not found on stack")
        return

    # Curiosity draw trigger: just draw, no card lookup or zone transition.
    if obj.is_draw_trigger:
        drawn = draw_cards(state, obj.draw_count)
        log.cards_drawn = drawn
        log.event_type = "CURIOSITY_DRAW"
        log.action_description = f"Curiosity draws: {len(drawn)} cards"
        log.notes.append(f"Drew {len(drawn)} cards from Curiosity trigger")
        return

    card_name = obj.card_name
    cd = get_card(card_name)
    log.event_type = "RESOLVE_SPELL"
    log.action_description = f"Resolve {card_name}"

    # Apply card-specific behavior
    beh = CARD_BEHAVIORS.get(card_name)
    if beh:
        beh.resolve_cast(state, obj)

    # Move to final zone
    if cd and cd.is_land:
        _enter_battlefield(state, card_name, obj)
    elif cd and (cd.is_artifact or cd.is_enchantment or cd.is_creature):
        _enter_battlefield(state, card_name, obj)
    elif obj.alt_cost_used == "flashback":
        state.exile.append(card_name)
    else:
        state.graveyard.append(card_name)

    log.notes.append(f"Resolved {card_name}")


def _enter_battlefield(state: GameState, card_name: str, obj: StackObject) -> None:
    from .cards import get_card
    cd = get_card(card_name)
    tapped = cd and cd.land_enters_tapped == "true"

    perm = Permanent(card_name=card_name, tapped=tapped)

    # Initialize depletion counter lands
    if cd and cd.land_mana_mode == "limited" and cd.land_limited_uses > 0:
        perm.depletion_counters = cd.land_limited_uses

    state.battlefield.append(perm)

    # Trigger on_enter behavior
    beh = CARD_BEHAVIORS.get(card_name)
    if beh:
        beh.on_enter(state, perm)


# ── Play land ─────────────────────────────────────────────────────────────────

def _resolve_play_land(state: GameState, action: Action, log: ActionLog) -> None:
    from .cards import get_card
    card_name = action.source_card
    if card_name is None:
        return

    _remove_one(state.hand, card_name)
    state.land_play_available = False

    cd = get_card(card_name)
    tapped = cd and cd.land_enters_tapped == "true"
    perm = Permanent(card_name=card_name, tapped=tapped)

    if cd and cd.land_mana_mode == "limited" and cd.land_limited_uses > 0:
        perm.depletion_counters = cd.land_limited_uses

    state.battlefield.append(perm)
    log.event_type = "PLAY_LAND"
    log.notes.append(f"Played {card_name} as land {'(tapped)' if tapped else '(untapped)'}")

    # Fetchlands: create a one-shot sacrifice activation for U or R
    if cd and cd.land_mana_mode == "fetch":
        perm.counters["fetchable"] = 1

    # Trigger on_enter if any behavior
    beh = CARD_BEHAVIORS.get(card_name)
    if beh:
        beh.on_enter(state, perm)


# ── Mana activations ──────────────────────────────────────────────────────────

def _resolve_activate_mana(state: GameState, action: Action, log: ActionLog) -> None:
    perm_id = action.costs.tap_permanent_id
    if perm_id:
        perm = state.get_perm_by_id(perm_id)
        if perm:
            perm.tapped = True

    # Also tap creature for Springleaf Drum
    if action.alt_cost_type and action.alt_cost_type.startswith("tap_creature:"):
        creature_id = action.alt_cost_type.split(":", 1)[1]
        if creature_id == "vivi":
            state.vivi_available_as_creature_to_tap = False
        else:
            c_perm = state.get_perm_by_id(creature_id)
            if c_perm:
                c_perm.tapped = True

    # Apply mana — color was already chosen at action-generation time
    state.floating_mana.add(action.effects.add_mana)
    log.event_type = "ACTIVATE_MANA"

    # Depletion counters for limited-use lands
    if perm_id:
        perm = state.get_perm_by_id(perm_id)
        if perm and perm.depletion_counters > 0:
            perm.depletion_counters -= 1
            if perm.depletion_counters == 0:
                perm.tapped = True  # exhausted

    # Fetchland: sacrifice after producing mana
    if perm_id:
        perm = state.get_perm_by_id(perm_id)
        if perm:
            from .cards import get_card
            cd = get_card(perm.card_name)
            if cd and cd.land_mana_mode == "fetch":
                state.remove_perm_by_id(perm_id)
                state.graveyard.append(perm.card_name)
                log.notes.append(f"Fetched and sacrificed {perm.card_name}")


def _resolve_exile_for_mana(state: GameState, action: Action, log: ActionLog) -> None:
    card_name = action.costs.exile_from_hand
    if card_name and card_name in state.hand:
        _remove_one(state.hand, card_name)
        state.exile.append(card_name)
        state.floating_mana.add(action.effects.add_mana)
        log.event_type = "EXILE"
        log.notes.append(f"Exiled {card_name} for mana")


def _resolve_sacrifice_for_mana(state: GameState, action: Action, log: ActionLog) -> None:
    perm_id = action.costs.sacrifice_permanent_id
    card_name = action.source_card

    if perm_id:
        perm = state.remove_perm_by_id(perm_id)
        if perm:
            if perm.card_name == "_Treasure":
                pass  # tokens don't go to graveyard
            else:
                state.graveyard.append(perm.card_name)

    # LED: discard hand before adding mana
    if card_name == "Lion's Eye Diamond":
        discarded = state.hand.copy()
        state.hand.clear()
        state.graveyard.extend(discarded)
        log.notes.append(f"LED discarded: {discarded}")

    # Color was already chosen at action-generation time
    pool = action.effects.add_mana
    state.floating_mana.add(pool)
    log.notes.append(f"Sacrificed {card_name} for {pool}")
    log.event_type = "SACRIFICE"


# ── Pending-choice resolvers ──────────────────────────────────────────────────

def _resolve_choose_imprint(state: GameState, action: Action, log: ActionLog) -> None:
    state.pending_choices = [c for c in state.pending_choices
                              if not (c.choice_type == "imprint" and c.perm_id == action.target)]
    log.event_type = "CHOOSE_IMPRINT"

    card = action.source_card
    if card is None:
        log.action_description = "Chrome Mox enters without imprint"
        log.notes.append("No eligible card to imprint")
        return

    perm = state.get_perm_by_id(action.target or "")
    if perm is None:
        return
    _remove_one(state.hand, card)
    state.exile.append(card)
    perm.imprinted_card = card
    log.action_description = f"Imprint {card} onto Chrome Mox"
    log.notes.append(f"Imprinted {card}")


def _resolve_choose_discard(state: GameState, action: Action, log: ActionLog) -> None:
    state.pending_choices = [c for c in state.pending_choices
                              if not (c.choice_type == "discard" and c.perm_id == action.target)]
    log.event_type = "CHOOSE_DISCARD"

    land = action.source_card
    if land is None:
        # No land available → sacrifice Mox Diamond
        perm = state.remove_perm_by_id(action.target or "")
        if perm:
            state.graveyard.append("Mox Diamond")
        log.action_description = "Mox Diamond sacrificed (no land to discard)"
        log.notes.append("Sacrificed Mox Diamond")
        return

    _remove_one(state.hand, land)
    state.graveyard.append(land)
    log.action_description = f"Discard {land} for Mox Diamond"
    log.notes.append(f"Discarded {land} for Mox Diamond")


def _resolve_choose_tutor(state: GameState, action: Action, log: ActionLog) -> None:
    # Pop the first pending tutor choice and capture its post_effect
    pending = next((c for c in state.pending_choices if c.choice_type == "tutor"), None)
    post_effect = pending.post_effect if pending else ""
    state.pending_choices = [c for c in state.pending_choices
                              if c is not pending]
    log.event_type = "CHOOSE_TUTOR"

    card = action.source_card
    destination = action.alt_cost_type or "hand"

    if card and card in state.library:
        state.library.remove(card)
        if destination == "top":
            state.library.insert(0, card)
            log.action_description = f"Tutor: put {card} on top"
        else:
            state.hand.append(card)
            log.action_description = f"Tutor: {card} → hand"
        log.notes.append(f"Tutored {card} → {destination}")

    # Post-effects that fire unconditionally after the tutor choice
    if post_effect == "gamble_discard":
        if state.hand and state.rng:
            discard = state.rng.choice(state.hand)
            _remove_one(state.hand, discard)
            state.graveyard.append(discard)
            log.notes.append(f"Gamble discarded: {discard}")
    elif post_effect == "intuition_discard_two":
        for _ in range(min(2, len(state.library))):
            filler = state.library.pop(0)
            state.graveyard.append(filler)
        log.notes.append("Intuition: 2 unchosen cards to graveyard")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lookup_target_name(state: GameState, target_id: str | None) -> str | None:
    """Resolve a target ID to a human-readable name for display in stack repr."""
    if target_id is None:
        return None
    for obj in state.stack:
        if obj.stack_id == target_id and not obj.is_draw_trigger:
            return obj.card_name
    for perm in state.battlefield:
        if perm.perm_id == target_id:
            return perm.card_name
    if state._opponent_creature_perm and state._opponent_creature_perm.perm_id == target_id:
        return "[opponent dummy creature]"
    if state._opponent_artifact_perm and state._opponent_artifact_perm.perm_id == target_id:
        return "[opponent dummy artifact]"
    return None


def _remove_one(lst: list, item: str) -> None:
    assert item in lst, f"Zone error: expected {item!r} in list but not found; list={lst}"
    lst.remove(item)


def _remove_permission(state: GameState, card_name: str) -> None:
    state.permissions = [p for p in state.permissions if p.card_name != card_name]
