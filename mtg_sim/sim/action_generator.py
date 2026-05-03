"""Enumerate all legal actions given the current game state."""
from __future__ import annotations
from typing import TYPE_CHECKING
from .mana import ManaCost, ManaPool, can_pay_cost
from .actions import (
    Action, CostBundle, EffectBundle,
    CAST_SPELL, RESOLVE_STACK_OBJECT, PLAY_LAND,
    ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA,
    RISK_SAFE, RISK_NORMAL, RISK_EXPENSIVE, RISK_RISKY, RISK_DESPERATE,
    EXTRA_TURN_WIN_CARDS, NONCREATURE_SPELL_WIN_THRESHOLD,
)
from .card_behaviors import CARD_BEHAVIORS

if TYPE_CHECKING:
    from .state import GameState
    from .stack import StackObject


# ── Alt cost parsing ──────────────────────────────────────────────────────────

def _parse_alt_costs(alt_costs_str: str) -> list[str]:
    """Return list of alt cost tokens from the CSV field."""
    if not alt_costs_str or alt_costs_str == "none":
        return []
    return [s.strip() for s in alt_costs_str.split(";") if s.strip()]


def _has_alt(alt_str: str, prefix: str) -> bool:
    for tok in _parse_alt_costs(alt_str):
        if tok.startswith(prefix):
            return True
    return False


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_actions(state: GameState) -> list[Action]:
    actions: list[Action] = []
    actions += _gen_stack_resolution_actions(state)
    actions += _gen_cast_actions(state)
    actions += _gen_cast_from_exile_actions(state)
    actions += _gen_land_play_actions(state)
    actions += _gen_mana_actions(state)
    actions += _gen_special_hand_actions(state)
    return actions


# ── Stack resolution ──────────────────────────────────────────────────────────

def _gen_stack_resolution_actions(state: GameState) -> list[Action]:
    actions = []
    for obj in state.stack:
        actions.append(Action(
            action_type=RESOLVE_STACK_OBJECT,
            source_card=obj.card_name,
            description=f"Resolve {obj.card_name}",
            target=obj.stack_id,
            risk_level=RISK_NORMAL,
        ))
    return actions


# ── Cast from hand ────────────────────────────────────────────────────────────

def _gen_cast_actions(state: GameState) -> list[Action]:
    from .cards import get_card
    actions: list[Action] = []
    seen: set[str] = set()

    for card_name in state.hand:
        if card_name in seen:
            continue
        seen.add(card_name)

        cd = get_card(card_name)
        if cd is None:
            continue
        if cd.is_land:
            continue  # lands are handled separately

        # Creatures: only generate cast action if behavior says so
        if cd.is_creature:
            beh = CARD_BEHAVIORS.get(card_name)
            if beh:
                extra = beh.generate_actions(state, card_name)
                if extra:
                    actions += extra
                else:
                    # Behavior exists but no actions generated = not useful now
                    pass
            # Even if no behavior, generate cast action for Tandem Lookout etc.
            # But skip most creatures
            if card_name in ("Tandem Lookout",):
                cast_acts = _gen_normal_and_alt_cast_actions(state, card_name, cd)
                actions += cast_acts
            continue

        actions += _gen_normal_and_alt_cast_actions(state, card_name, cd)

    return actions


def _gen_normal_and_alt_cast_actions(state: GameState, card_name: str, cd) -> list[Action]:
    from .cards import get_card
    actions: list[Action] = []

    normal_cost = ManaCost(
        pip_u=cd.pip_u,
        pip_r=cd.pip_r,
        generic=cd.generic_mana,
        x_cost=cd.x_in_cost,
    )

    is_win_card = card_name in EXTRA_TURN_WIN_CARDS
    risk = RISK_SAFE if normal_cost.is_free() else RISK_NORMAL
    if is_win_card:
        risk = RISK_NORMAL

    # ── Normal cast ──────────────────────────────────────────────────────────
    if not cd.x_in_cost:
        if can_pay_cost(state.floating_mana, normal_cost):
            actions.append(_make_cast_action(card_name, normal_cost, risk, cd))
    else:
        # X-cost spells: generate for X=0 to X=max_affordable
        max_x = _max_x_for(state, cd)
        for x in range(0, max_x + 1):
            cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r,
                            generic=cd.generic_mana, x_cost=True, x_value=x)
            if can_pay_cost(state.floating_mana, cost):
                # For Repeal: need valid targets
                if card_name == "Repeal":
                    targets = _repeal_targets(state, x)
                    if not targets:
                        continue
                    for t_id, t_name in targets:
                        actions.append(_make_cast_action(
                            card_name, cost, risk, cd,
                            x_value=x,
                            target=t_id,
                            description=f"Cast Repeal X={x} (bounce {t_name})",
                        ))
                else:
                    actions.append(_make_cast_action(card_name, cost, risk, cd, x_value=x))

    # ── Alt costs ─────────────────────────────────────────────────────────────
    alt_str = cd.alt_costs
    if not alt_str or alt_str == "none":
        return actions

    for tok in _parse_alt_costs(alt_str):
        alt_actions = _gen_alt_cost_actions(state, card_name, cd, tok)
        actions += alt_actions

    return actions


def _make_cast_action(
    card_name: str, cost: ManaCost, risk: str, cd,
    x_value: int = 0, target: str | None = None, description: str | None = None,
    alt_cost_type: str | None = None, costs_override: CostBundle | None = None,
) -> Action:
    if description is None:
        description = f"Cast {card_name}"
        if x_value:
            description += f" (X={x_value})"
    return Action(
        action_type=CAST_SPELL,
        source_card=card_name,
        description=description,
        costs=costs_override or CostBundle(mana=cost),
        requires_target=target is not None,
        target=target,
        risk_level=risk,
        x_value=x_value,
        alt_cost_type=alt_cost_type,
    )


def _max_x_for(state: GameState, cd) -> int:
    pool = state.floating_mana
    available = pool.U + pool.R + pool.C + pool.ANY
    fixed = cd.pip_u + cd.pip_r + cd.generic_mana
    return max(0, available - fixed)


def _repeal_targets(state: GameState, x: int) -> list[tuple[str, str]]:
    from .cards import get_card
    results = []
    for perm in state.battlefield:
        cd = get_card(perm.card_name)
        if cd and not cd.is_land and cd.mv <= x:
            results.append((perm.perm_id, perm.card_name))
    return results


# ── Alt cost action generation ────────────────────────────────────────────────

def _gen_alt_cost_actions(state: GameState, card_name: str, cd, tok: str) -> list[Action]:
    from .cards import get_card
    actions: list[Action] = []

    # ── free:pay_life_ignored  (Gitaxian Probe, Gut Shot, Mental Misstep) ────
    if tok.startswith("free:pay_life_ignored"):
        # Life = 0 in sim → effectively free
        cost = ManaCost.zero()
        if card_name == "Mental Misstep":
            targets = _get_mv1_stack_targets(state)
            for t_id, t_name in targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (free/life) targeting {t_name}",
                    costs=CostBundle(),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_SAFE,
                    alt_cost_type="pay_life",
                ))
        else:
            actions.append(_make_cast_action(
                card_name, cost, RISK_SAFE, cd,
                alt_cost_type="pay_life",
            ))

    # ── free:commander_controlled  (Fierce Guardianship, Deflecting Swat) ───
    elif tok.startswith("free:commander_controlled"):
        if state.vivi_on_battlefield:
            # Need any spell on stack as target
            spell_targets = _get_any_stack_targets(state)
            for t_id, t_name in spell_targets:
                risk = RISK_SAFE if card_name == "Fierce Guardianship" else RISK_SAFE
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (free/commander) targeting {t_name}",
                    costs=CostBundle(),
                    requires_target=True,
                    target=t_id,
                    risk_level=risk,
                    alt_cost_type="commander_free",
                ))

    # ── free:pitch_blue  (Force of Will, Misdirection, Snapback) ─────────────
    elif tok.startswith("free:pitch_blue"):
        spell_targets = _get_any_stack_targets(state)
        blue_pitches = _blue_cards_in_hand_except(state, card_name)
        for pitch in blue_pitches:
            for t_id, t_name in spell_targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {pitch}) targeting {t_name}",
                    costs=CostBundle(pitched_card=pitch),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_EXPENSIVE,
                    alt_cost_type="pitch_blue",
                ))

    # ── free:pitch_blue_blue  (Commandeer) ────────────────────────────────────
    elif tok.startswith("free:pitch_blue_blue"):
        spell_targets = _get_any_stack_targets(state)
        blue_cards = _blue_cards_in_hand_except(state, card_name)
        if len(blue_cards) >= 2:
            for t_id, t_name in spell_targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch 2 blue) targeting {t_name}",
                    costs=CostBundle(pitch_blue_count=2, pitched_card=blue_cards[0]),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_DESPERATE,
                    alt_cost_type="pitch_blue_blue",
                ))

    # ── free:pitch_red  (Cave-In, Pyrokinesis) ────────────────────────────────
    elif tok.startswith("free:pitch_red"):
        red_cards = _red_cards_in_hand_except(state, card_name)
        for pitch in red_cards:
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card=card_name,
                description=f"Cast {card_name} (pitch {pitch})",
                costs=CostBundle(pitched_card=pitch),
                risk_level=RISK_RISKY,
                alt_cost_type="pitch_red",
            ))

    # ── free:return_island  (Daze) ────────────────────────────────────────────
    elif tok.startswith("free:return_island"):
        islands = _islands_on_battlefield(state)
        if islands:
            spell_targets = _get_any_stack_targets(state)
            for t_id, t_name in spell_targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card="Daze",
                    description=f"Cast Daze (return island) targeting {t_name}",
                    costs=CostBundle(return_land_to_hand=True,
                                     tap_permanent_id=islands[0].perm_id),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_EXPENSIVE,
                    alt_cost_type="return_island",
                ))

    # ── free:delayed_upkeep_cost  (Pact of Negation) ─────────────────────────
    elif tok.startswith("free:delayed_upkeep_cost"):
        spell_targets = _get_any_stack_targets(state)
        for t_id, t_name in spell_targets:
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card="Pact of Negation",
                description=f"Cast Pact of Negation (free) targeting {t_name}",
                costs=CostBundle(),
                requires_target=True,
                target=t_id,
                risk_level=RISK_NORMAL,
                alt_cost_type="delayed_upkeep",
            ))

    # ── alt_x:pitch_blue_mv  (Disrupting Shoal) ──────────────────────────────
    elif tok.startswith("alt_x:pitch_blue_mv"):
        # Pitch blue card with MV = target spell's MV
        for t_id, t_name in _get_any_stack_targets(state):
            t_mv = _stack_object_mv(state, t_id)
            if t_mv < 0:
                continue
            pitches = _blue_cards_with_mv_in_hand(state, card_name, t_mv)
            for pitch in pitches:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {pitch} MV={t_mv}) vs {t_name}",
                    costs=CostBundle(pitched_card=pitch),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_EXPENSIVE,
                    alt_cost_type="pitch_blue_x",
                    x_value=t_mv,
                ))

    # ── alt:flashback_2R  (Strike It Rich) ───────────────────────────────────
    elif tok.startswith("alt:flashback_2R"):
        if card_name in state.graveyard:
            cost = ManaCost(pip_r=1, generic=2)
            if can_pay_cost(state.floating_mana, cost):
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} via flashback",
                    costs=CostBundle(mana=cost),
                    risk_level=RISK_NORMAL,
                    alt_cost_type="flashback",
                ))

    return actions


# ── Cast from exile (permissions) ─────────────────────────────────────────────

def _gen_cast_from_exile_actions(state: GameState) -> list[Action]:
    from .cards import get_card
    actions: list[Action] = []
    seen: set[str] = set()
    for perm in state.permissions:
        if perm.action_type != CAST_SPELL or perm.zone != "exile":
            continue
        cname = perm.card_name
        if cname not in state.exile or cname in seen:
            continue
        seen.add(cname)
        cd = get_card(cname)
        if cd is None or cd.is_land or cd.is_creature:
            continue
        cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, cost):
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card=cname,
                description=f"Cast {cname} from exile",
                costs=CostBundle(mana=cost),
                risk_level=RISK_NORMAL,
                alt_cost_type="exile_permission",
            ))
    return actions


# ── Land plays ────────────────────────────────────────────────────────────────

def _gen_land_play_actions(state: GameState) -> list[Action]:
    from .cards import get_card
    if not state.land_play_available:
        return []
    actions: list[Action] = []
    seen: set[str] = set()
    for card_name in state.hand:
        if card_name in seen:
            continue
        seen.add(card_name)
        cd = get_card(card_name)
        if cd is None:
            continue
        if cd.can_play_as_land:
            tapped = cd.land_enters_tapped == "true"
            actions.append(Action(
                action_type=PLAY_LAND,
                source_card=card_name,
                description=f"Play {card_name} as land",
                costs=CostBundle(),
                risk_level=RISK_SAFE,
                alt_cost_type="as_land" if not cd.is_land else None,
            ))
    return actions


# ── Mana source activations (permanents) ─────────────────────────────────────

def _gen_mana_actions(state: GameState) -> list[Action]:
    from .cards import get_card
    actions: list[Action] = []
    for perm in state.battlefield:
        cd = get_card(perm.card_name)
        if perm.card_name == "_Treasure":
            beh = CARD_BEHAVIORS["_Treasure"]
            actions += beh.generate_mana_actions(state, perm)
            continue
        if cd is None or not cd.produces_mana:
            continue
        # Only permanents that activate for mana via tap/sacrifice belong here.
        # Skip creature abilities (Vivi), spells, and exile-from-hand effects —
        # those are handled by cast triggers or special actions, not activated abilities.
        if cd.mana_source_type not in ("land", "artifact"):
            continue
        beh = CARD_BEHAVIORS.get(perm.card_name)
        if beh:
            actions += beh.generate_mana_actions(state, perm)
        else:
            actions += _default_mana_actions(state, perm, cd)
    return actions


def _default_mana_actions(state: GameState, perm, cd) -> list[Action]:
    """Generate mana activation for lands and simple artifacts without special behavior."""
    if cd.mana_timing == "one_shot" or cd.requires_sacrifice:
        return []  # handled by behaviors
    if cd.requires_tap and perm.tapped:
        return []

    colors = cd.mana_colors
    try:
        amount = int(cd.mana_amount)
    except (ValueError, TypeError):
        amount = 1

    pool = _colors_to_pool(colors, amount)

    if cd.land_mana_mode == "limited":
        if perm.depletion_counters <= 0:
            return []
        # Limited use lands (Sandstone Needle etc.) use depletion counters
        pool = _colors_to_pool(colors, amount)

    return [Action(
        action_type=ACTIVATE_MANA_ABILITY,
        source_card=perm.card_name,
        description=f"Tap {perm.card_name} for {pool}",
        costs=CostBundle(tap_permanent_id=perm.perm_id if cd.requires_tap else None),
        effects=EffectBundle(add_mana=pool),
        risk_level=RISK_SAFE,
    )]


def _colors_to_pool(colors: str, amount: int) -> ManaPool:
    if colors == "C":
        return ManaPool(C=amount)
    elif colors == "U":
        return ManaPool(U=amount)
    elif colors == "R":
        return ManaPool(R=amount)
    elif colors in ("UR", "any", "any_or_C", "any_one_color", "any_creature_or_C",
                    "legendary_permanent_colors", "stored_color", "imprinted_card_color"):
        return ManaPool(ANY=amount)
    return ManaPool(C=amount)


# ── Special hand actions ──────────────────────────────────────────────────────

def _gen_special_hand_actions(state: GameState) -> list[Action]:
    actions: list[Action] = []
    for card_name in set(state.hand):
        beh = CARD_BEHAVIORS.get(card_name)
        if beh and not isinstance(beh, type) and hasattr(beh, "generate_actions"):
            from .card_behaviors import SimianSpiritGuideBehavior
            if isinstance(beh, SimianSpiritGuideBehavior):
                actions += beh.generate_actions(state, card_name)
    return actions


# ── Stack target helpers ──────────────────────────────────────────────────────

def _get_any_stack_targets(state: GameState) -> list[tuple[str, str]]:
    return [(obj.stack_id, obj.card_name) for obj in state.stack]


def _get_mv1_stack_targets(state: GameState) -> list[tuple[str, str]]:
    from .cards import get_card
    return [
        (obj.stack_id, obj.card_name)
        for obj in state.stack
        if (cd := get_card(obj.card_name)) and cd.mv == 1
    ]


def _stack_object_mv(state: GameState, stack_id: str) -> int:
    from .cards import get_card
    obj = state.get_stack_object(stack_id)
    if obj is None:
        return -1
    cd = get_card(obj.card_name)
    return cd.mv if cd else -1


def _blue_cards_in_hand_except(state: GameState, exclude: str) -> list[str]:
    from .cards import get_card
    return [
        c for c in state.hand
        if c != exclude and (cd := get_card(c)) and cd.has_blue
    ]


def _red_cards_in_hand_except(state: GameState, exclude: str) -> list[str]:
    from .cards import get_card
    return [
        c for c in state.hand
        if c != exclude and (cd := get_card(c)) and cd.has_red
    ]


def _blue_cards_with_mv_in_hand(state: GameState, exclude: str, mv: int) -> list[str]:
    from .cards import get_card
    return [
        c for c in state.hand
        if c != exclude and (cd := get_card(c)) and cd.has_blue and cd.mv == mv
    ]


def _islands_on_battlefield(state: GameState) -> list:
    from .cards import get_card
    return [
        p for p in state.battlefield
        if (cd := get_card(p.card_name)) and cd.is_land
        and ("U" in (cd.mana_colors or "") or cd.name in ("Island", "Volcanic Island", "Steam Vents", "Fiery Islet"))
        and not p.tapped
    ]
