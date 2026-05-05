"""Enumerate all legal actions given the current game state."""
from __future__ import annotations
from typing import TYPE_CHECKING
from .mana import ManaCost, ManaPool, can_pay_cost
from .actions import (
    Action, CostBundle, EffectBundle,
    CAST_SPELL, RESOLVE_STACK_OBJECT, PLAY_LAND,
    ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA,
    CHOOSE_TUTOR,
    RISK_SAFE, RISK_NORMAL, RISK_EXPENSIVE, RISK_RISKY, RISK_DESPERATE,
    EXTRA_TURN_WIN_CARDS, NONCREATURE_SPELL_WIN_THRESHOLD,
)
from .card_behaviors import CARD_BEHAVIORS, CounterspellBehavior

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
    # Pending choices (imprint, land discard, tutor) block all other actions.
    if state.pending_choices:
        return _gen_pending_choice_actions(state)

    actions: list[Action] = []
    actions += _gen_stack_resolution_actions(state)
    actions += _gen_cast_actions(state)
    actions += _gen_cast_from_exile_actions(state)
    actions += _gen_land_play_actions(state)
    actions += _gen_mana_actions(state)
    actions += _gen_special_hand_actions(state)
    return actions


# ── Pending choice resolution ─────────────────────────────────────────────────

def _gen_pending_choice_actions(state: GameState) -> list[Action]:
    """Generate actions for the first pending choice; blocks all other actions."""
    from .cards import get_card
    choice = state.pending_choices[0]

    # Card-specific pending choices delegate to their behavior.
    if choice.choice_type in ("imprint", "discard"):
        beh = CARD_BEHAVIORS.get(choice.source_card)
        if beh:
            return beh.generate_pending_actions(state, choice)
        return []

    actions: list[Action] = []
    if choice.choice_type == "tutor":
        in_hand = set(state.hand)
        seen: set[str] = set()
        for card in state.library:
            if card in seen or card in in_hand:
                continue
            cd = get_card(card)
            if cd and _tutor_filter_matches(cd, choice.tutor_filter):
                seen.add(card)
                actions.append(Action(
                    action_type=CHOOSE_TUTOR,
                    source_card=card,
                    description=f"{choice.source_card}: tutor {card}",
                    alt_cost_type=choice.tutor_destination,
                    risk_level=RISK_NORMAL,
                ))

    return actions


def _tutor_filter_matches(cd, tutor_filter: str) -> bool:
    if tutor_filter == "instant_sorcery":
        return cd.is_instant or cd.is_sorcery
    if tutor_filter == "blue_instant":
        return cd.is_instant and cd.has_blue
    if tutor_filter == "instant":
        return cd.is_instant
    if tutor_filter == "sorcery":
        return cd.is_sorcery
    return cd.is_noncreature_spell or cd.can_play_as_land


# ── Stack resolution ──────────────────────────────────────────────────────────

def _gen_stack_resolution_actions(state: GameState) -> list[Action]:
    if not state.stack:
        return []
    # LIFO: only the top-of-stack object may be resolved.
    # Draw triggers are naturally above the spells that created them, so they
    # resolve first without any extra blocking check.
    obj = state.stack[-1]
    if obj.is_draw_trigger:
        desc = f"Resolve Curiosity draws ({obj.draw_count})"
        risk = RISK_SAFE
    else:
        desc = f"Resolve {obj.card_name}"
        risk = RISK_NORMAL
    return [Action(
        action_type=RESOLVE_STACK_OBJECT,
        source_card=obj.card_name,
        description=desc,
        target=obj.stack_id,
        risk_level=risk,
    )]


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

        beh = CARD_BEHAVIORS.get(card_name)
        beh_actions = beh.generate_actions(state, card_name) if beh else None
        if beh_actions is not None:
            actions += beh_actions
        else:
            actions += _gen_normal_and_alt_cast_actions(state, card_name, cd)

    return actions


def _gen_normal_and_alt_cast_actions(state: GameState, card_name: str, cd) -> list[Action]:
    from .cards import get_card
    actions: list[Action] = []

    # Sorcery-speed cards can only be cast when the stack is empty
    can_cast_sorcery_speed = not state.stack
    is_instant_speed = cd.is_instant or cd.has_flash
    if state.stack and not is_instant_speed:
        return actions

    normal_cost = ManaCost(
        pip_u=cd.pip_u,
        pip_r=cd.pip_r,
        generic=cd.generic_mana,
        pip_ur_hybrid=cd.pip_ur_hybrid,
        x_cost=cd.x_in_cost,
    )

    is_win_card = card_name in EXTRA_TURN_WIN_CARDS
    risk = RISK_SAFE if normal_cost.is_free() else RISK_NORMAL
    if is_win_card:
        risk = RISK_NORMAL

    # ── Normal cast ──────────────────────────────────────────────────────────
    # Counterspells cast for their normal mana cost require a stack target.
    is_counterspell = isinstance(CARD_BEHAVIORS.get(card_name), CounterspellBehavior)
    if is_counterspell:
        # Generate one action per stack target; fall through to alt costs below
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in _get_any_stack_targets(state):
                actions.append(_make_cast_action(
                    card_name, normal_cost, risk, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
    elif not cd.x_in_cost:
        if can_pay_cost(state.floating_mana, normal_cost):
            actions.append(_make_cast_action(card_name, normal_cost, risk, cd))
    else:
        # X-cost spells: generate for X=0 to X=max_affordable
        max_x = _max_x_for(state, cd)
        for x in range(0, max_x + 1):
            cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r,
                            generic=cd.generic_mana, pip_ur_hybrid=cd.pip_ur_hybrid,
                            x_cost=True, x_value=x)
            if can_pay_cost(state.floating_mana, cost):
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
    fixed = cd.pip_u + cd.pip_r + cd.generic_mana + cd.pip_ur_hybrid
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
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (free/commander) targeting {t_name}",
                    costs=CostBundle(),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_SAFE,
                    alt_cost_type="commander_free",
                ))

    # ── free:pitch_blue  (Force of Will, Snapback) ────────────────────────────
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
        from itertools import combinations
        spell_targets = _get_any_stack_targets(state)
        blue_cards = _blue_cards_in_hand_except(state, card_name)
        for card1, card2 in combinations(blue_cards, 2):
            for t_id, t_name in spell_targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {card1}, {card2}) targeting {t_name}",
                    costs=CostBundle(pitch_blue_count=2, pitched_card=card1,
                                     pitched_card_2=card2),
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
        # Pitch any blue card; X = pitch card's MV. Counter succeeds only if X == target MV
        # (the MV check is enforced at resolution in CounterspellBehavior, not here)
        pitches = _blue_cards_in_hand_except(state, card_name)
        for pitch in pitches:
            pitch_mv = _stack_object_mv_by_name(pitch)
            for t_id, t_name in _get_any_stack_targets(state):
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {pitch}) targeting {t_name}",
                    costs=CostBundle(pitched_card=pitch),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_EXPENSIVE,
                    alt_cost_type="pitch_blue_x",
                    x_value=pitch_mv,
                ))

    # ── alt_x:pitch_red_mv  (Blazing Shoal) ──────────────────────────────────
    elif tok.startswith("alt_x:pitch_red_mv"):
        # Pitch any red card; X = pitched card's MV; no MV restriction on which card to pitch
        red_pitches = _red_cards_in_hand_except(state, card_name)
        for pitch in red_pitches:
            pitch_mv = _stack_object_mv_by_name(pitch)
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card=card_name,
                description=f"Cast {card_name} (pitch {pitch}, X={pitch_mv})",
                costs=CostBundle(pitched_card=pitch),
                risk_level=RISK_RISKY,
                alt_cost_type="pitch_red_x",
                x_value=pitch_mv,
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

    # ── split_face:LABEL_COSTPART...  (e.g. Invert // Invent's Invent face) ──
    elif tok.startswith("split_face:"):
        # Token encodes the alternate face cost: split_face:LABEL_PART1_PART2...
        # Parts: integers = generic mana, "hybridUR" = one {U/R} pip
        # All split-face second halves are treated as sorcery-speed.
        rest = tok[len("split_face:"):]
        parts = rest.split("_")
        face_label = parts[0] if parts else ""
        generic = 0
        pip_ur_hybrid = 0
        for part in parts[1:]:
            try:
                generic += int(part)
            except ValueError:
                if part == "hybridUR":
                    pip_ur_hybrid += 1

        cost = ManaCost(generic=generic, pip_ur_hybrid=pip_ur_hybrid)
        # Sorcery-speed: only legal when stack is empty
        if not state.stack and can_pay_cost(state.floating_mana, cost):
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card=card_name,
                description=f"Cast {card_name} ({face_label} face)",
                costs=CostBundle(mana=cost),
                risk_level=RISK_NORMAL,
                alt_cost_type=f"{face_label}_face",
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
        cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r, generic=cd.generic_mana,
                        pip_ur_hybrid=cd.pip_ur_hybrid)
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

    if cd.land_mana_mode == "limited":
        if perm.depletion_counters <= 0:
            return []

    tap_id = perm.perm_id if cd.requires_tap else None

    # Fixed single-color sources → one action
    if colors in ("U", "R", "C"):
        pool = ManaPool(**{colors: amount})
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card=perm.card_name,
            description=f"Tap {perm.card_name} for {pool}",
            costs=CostBundle(tap_permanent_id=tap_id),
            effects=EffectBundle(add_mana=pool),
            risk_level=RISK_SAFE,
        )]

    # "UR" dual lands → U or R only (no colorless)
    if colors == "UR":
        return [
            Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card=perm.card_name,
                description=f"Tap {perm.card_name} for {{{color}}}",
                costs=CostBundle(tap_permanent_id=tap_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: amount})),
                risk_level=RISK_SAFE,
            )
            for color in ("U", "R")
        ]

    # All other flexible sources ("any", "any_or_C", etc.) → U, R, or C
    return [
        Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card=perm.card_name,
            description=f"Tap {perm.card_name} for {{{color}}}",
            costs=CostBundle(tap_permanent_id=tap_id),
            effects=EffectBundle(add_mana=ManaPool(**{color: amount})),
            risk_level=RISK_SAFE,
        )
        for color in ("U", "R", "C")
    ]


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
    return [(obj.stack_id, obj.card_name) for obj in state.stack if not obj.is_draw_trigger]


def _get_single_target_stack_objects(state: GameState) -> list[tuple[str, str]]:
    """Stack spells that themselves have exactly one target (required for Misdirection)."""
    return [
        (obj.stack_id, obj.card_name)
        for obj in state.stack
        if not obj.is_draw_trigger and len(obj.targets) == 1
    ]


def _get_creature_targets(state: GameState) -> list[tuple[str, str]]:
    """Own creatures on battlefield plus the dummy opponent creature."""
    from .cards import get_card
    targets = []
    for perm in state.battlefield:
        cd = get_card(perm.card_name)
        if cd and cd.is_creature:
            targets.append((perm.perm_id, perm.card_name))
    opp = state._opponent_creature_perm
    if opp:
        targets.append((opp.perm_id, "[opponent dummy creature]"))
    return targets


def _get_artifact_targets(state: GameState) -> list[tuple[str, str]]:
    """Dummy opponent artifact target (used for spells like Mogg Salvage)."""
    opp = state._opponent_artifact_perm
    if opp:
        return [(opp.perm_id, "[opponent dummy artifact]")]
    return []


def _get_mv1_stack_targets(state: GameState) -> list[tuple[str, str]]:
    from .cards import get_card
    return [
        (obj.stack_id, obj.card_name)
        for obj in state.stack
        if not obj.is_draw_trigger and (cd := get_card(obj.card_name)) and cd.mv == 1
    ]


def _stack_object_mv(state: GameState, stack_id: str) -> int:
    from .cards import get_card
    obj = state.get_stack_object(stack_id)
    if obj is None:
        return -1
    cd = get_card(obj.card_name)
    return cd.mv if cd else -1


def _stack_object_mv_by_name(card_name: str) -> int:
    from .cards import get_card
    cd = get_card(card_name)
    return cd.mv if cd else 0


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


# Known Mountain-subtype lands (dual lands that are also Mountains).
_MOUNTAIN_LANDS = frozenset({
    "Mountain",
    "Volcanic Island",
    "Steam Vents",
    "Stomping Ground",
    "Sacred Foundry",
    "Blood Crypt",
    "Badlands",
    "Taiga",
})


def _we_control_mountain(state: GameState) -> bool:
    """True if we have a Mountain (or Mountain-subtype dual) on the battlefield."""
    return any(p.card_name in _MOUNTAIN_LANDS for p in state.battlefield)
