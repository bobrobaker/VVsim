"""Card-specific behavior implementations.

Each CardBehavior subclass handles:
  generate_actions  – what actions this card enables (mana, cast-from-exile, etc.)
  resolve_cast      – what happens when this card resolves from the stack
  on_enter          – called when a permanent enters the battlefield
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from .mana import ManaPool, ManaCost
from .actions import (
    Action, CostBundle, EffectBundle,
    CAST_SPELL, ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA, SACRIFICE_FOR_MANA, FETCH_LAND,
    ACTIVATE_TRANSMUTE,
    RISK_SAFE, RISK_NORMAL, RISK_EXPENSIVE, RISK_RISKY, RISK_DESPERATE,
    EXTRA_TURN_WIN_CARDS,
)
from .state import Permission

if TYPE_CHECKING:
    from .state import GameState
    from .stack import StackObject
    from .state import Permanent


# ── Base class ────────────────────────────────────────────────────────────────

class CardBehavior:
    def generate_actions(self, state: GameState, card_name: str) -> list[Action] | None:
        # Return None to delegate to generic scaffolding; return a list to own generation.
        return None

    def generate_mana_actions(self, state: GameState, perm: Permanent) -> list[Action]:
        return []

    def generate_activate_actions(self, state: GameState, perm: Permanent) -> list[Action]:
        """Non-mana activated abilities (tap/sac abilities that draw or have effects)."""
        return []

    def generate_pending_actions(self, state: GameState, choice) -> list[Action]:
        return []

    def resolve_cast(self, state: GameState, stack_obj: StackObject) -> None:
        pass

    def on_enter(self, state: GameState, perm: Permanent) -> None:
        pass


# ── Mana: simple tap artifacts ────────────────────────────────────────────────

class SolRingBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Sol Ring",
            description="Tap Sol Ring for {C}{C}",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(C=2)),
            risk_level=RISK_SAFE,
        )]


class ManaVaultBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Mana Vault",
            description="Tap Mana Vault for {C}{C}{C}",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(C=3)),
            risk_level=RISK_SAFE,
        )]


class GrimMonolithBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Grim Monolith",
            description="Tap Grim Monolith for {C}{C}{C}",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(C=3)),
            risk_level=RISK_SAFE,
        )]


# ── Mana: Lotus Petal (sacrifice for any) ────────────────────────────────────

class LotusPetalBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        return [
            Action(
                action_type=SACRIFICE_FOR_MANA,
                source_card="Lotus Petal",
                description=f"Sacrifice Lotus Petal for {{{color}}}",
                costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
            )
            for color in ("U", "R")
        ]


# ── Mana: Lion's Eye Diamond ─────────────────────────────────────────────────

class LionsEyeDiamondBehavior(CardBehavior):
    """Tap, sacrifice, discard hand → add 3 of chosen color (RRR by default)."""

    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        actions = []
        for color, label in [("R", "RRR"), ("U", "UUU")]:
            actions.append(Action(
                action_type=SACRIFICE_FOR_MANA,
                source_card="Lion's Eye Diamond",
                description=f"Activate Lion's Eye Diamond for {{{label}}} (discard hand)",
                costs=CostBundle(
                    tap_permanent_id=perm.perm_id,
                    sacrifice_permanent_id=perm.perm_id,
                ),
                effects=EffectBundle(add_mana=ManaPool(**{color: 3})),
                risk_level=RISK_DESPERATE,
                alt_cost_type=f"led_{color.lower()}",
            ))
        return actions

    def resolve_cast(self, state, stack_obj):
        pass  # just enters battlefield


# ── Mana: Chrome Mox ─────────────────────────────────────────────────────────

class ChromeMoxBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped or perm.imprinted_card is None:
            return []
        from .cards import get_card
        imp = get_card(perm.imprinted_card)
        if imp is None:
            return []
        colors = []
        if imp.has_blue:
            colors.append("U")
        if imp.has_red:
            colors.append("R")
        if not colors:
            return []
        return [
            Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card="Chrome Mox",
                description=f"Tap Chrome Mox (imprinted {perm.imprinted_card}) for {{{color}}}",
                costs=CostBundle(tap_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
            )
            for color in colors
        ]

    def generate_pending_actions(self, state, choice) -> list[Action]:
        from .cards import get_card
        from .actions import CHOOSE_IMPRINT, RISK_NORMAL, RISK_SAFE
        perm = state.get_perm_by_id(choice.perm_id)
        candidates = [
            c for c in state.hand
            if c != "Chrome Mox"
            and (cd := get_card(c)) and not cd.is_artifact and not cd.is_land
            and (cd.has_blue or cd.has_red)
        ] if perm else []
        actions = [
            Action(
                action_type=CHOOSE_IMPRINT,
                source_card=card,
                description=f"Imprint {card} onto Chrome Mox",
                target=choice.perm_id,
                risk_level=RISK_NORMAL,
            )
            for card in set(candidates)
        ]
        actions.append(Action(
            action_type=CHOOSE_IMPRINT,
            source_card=None,
            description="Chrome Mox enters without imprint (no eligible card)",
            target=choice.perm_id,
            risk_level=RISK_SAFE,
        ))
        return actions

    def on_enter(self, state, perm):
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="imprint",
            perm_id=perm.perm_id,
            source_card="Chrome Mox",
        ))

    def resolve_cast(self, state, stack_obj):
        pass


# ── Mana: Mox Diamond ────────────────────────────────────────────────────────

class MoxDiamondBehavior(CardBehavior):
    def generate_pending_actions(self, state, choice) -> list[Action]:
        from .actions import CHOOSE_DISCARD, RISK_SAFE, RISK_RISKY
        lands = state.lands_in_hand()
        if lands:
            return [
                Action(
                    action_type=CHOOSE_DISCARD,
                    source_card=land,
                    description=f"Discard {land} for Mox Diamond",
                    target=choice.perm_id,
                    risk_level=RISK_SAFE,
                )
                for land in set(lands)
            ]
        return [Action(
            action_type=CHOOSE_DISCARD,
            source_card=None,
            description="Sacrifice Mox Diamond (no land in hand)",
            target=choice.perm_id,
            risk_level=RISK_RISKY,
        )]

    def on_enter(self, state, perm):
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="discard",
            perm_id=perm.perm_id,
            source_card="Mox Diamond",
        ))

    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        return [
            Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card="Mox Diamond",
                description=f"Tap Mox Diamond for {{{color}}}",
                costs=CostBundle(tap_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
            )
            for color in ("U", "R")
        ]


# ── Mana: Mox Opal (metalcraft) ──────────────────────────────────────────────

class MoxOpalBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        if state.count_artifacts() < 3:
            return []
        return [
            Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card="Mox Opal",
                description=f"Tap Mox Opal (metalcraft) for {{{color}}}",
                costs=CostBundle(tap_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
            )
            for color in ("U", "R")
        ]


# ── Mana: Mox Amber (legendary) ──────────────────────────────────────────────

class MoxAmberBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        if not state.legendary_permanent_available:
            return []
        # Vivi is a UR legendary; produce U or R only (no colorless from Mox Amber)
        return [
            Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card="Mox Amber",
                description=f"Tap Mox Amber (Vivi legendary) for {{{color}}}",
                costs=CostBundle(tap_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
            )
            for color in ("U", "R")
        ]


# ── Mana: Springleaf Drum ────────────────────────────────────────────────────

class SpringleafDrumBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        if not state.has_untapped_creature():
            return []
        creature = state.get_untapped_creature_perm()
        cid = creature.perm_id if creature else "vivi"
        return [
            Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card="Springleaf Drum",
                description=f"Tap Springleaf Drum + creature for {{{color}}}",
                costs=CostBundle(tap_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
                alt_cost_type=f"tap_creature:{cid}",
            )
            for color in ("U", "R")
        ]


# ── Mana: Simian Spirit Guide (exile from hand) ───────────────────────────────

class SimianSpiritGuideBehavior(CardBehavior):
    def generate_actions(self, state, card_name):
        if card_name not in state.hand:
            return []
        return [Action(
            action_type=EXILE_FOR_MANA,
            source_card="Simian Spirit Guide",
            description="Exile Simian Spirit Guide for {R}",
            costs=CostBundle(exile_from_hand="Simian Spirit Guide"),
            effects=EffectBundle(add_mana=ManaPool(R=1)),
            risk_level=RISK_NORMAL,
        )]


# ── Mana: Jeweled Amulet ─────────────────────────────────────────────────────

class JeweledAmuletBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        # Can only activate if it has a charge counter (from previous charge)
        if perm.counters.get("charge", 0) == 0:
            return []
        color = perm.counters.get("color", "C")
        return [Action(
            action_type=SACRIFICE_FOR_MANA,
            source_card="Jeweled Amulet",
            description=f"Activate Jeweled Amulet for stored {color} mana",
            costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
            risk_level=RISK_SAFE,
        )]

    def resolve_cast(self, state, stack_obj):
        pass


# ── Mana: Paradise Mantle ────────────────────────────────────────────────────

class ParadiseMantleBehavior(CardBehavior):
    # Only equips to Vivi; other creatures likely have summoning sickness.
    def generate_mana_actions(self, state, perm):
        if perm.attached_to is None:
            # Sorcery-speed equip to Vivi when stack is empty
            if state.stack:
                return []
            return [Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card="Paradise Mantle",
                description="Equip Paradise Mantle onto Vivi",
                costs=CostBundle(),
                effects=EffectBundle(),
                risk_level=RISK_SAFE,
                alt_cost_type=f"equip_mantle:{perm.perm_id}",
            )]
        # Equipped: untapped Vivi taps for U or R
        if perm.attached_to == "vivi" and state.vivi_available_as_creature_to_tap:
            return [
                Action(
                    action_type=ACTIVATE_MANA_ABILITY,
                    source_card="Paradise Mantle",
                    description=f"Tap Vivi (Paradise Mantle) for {{{color}}}",
                    costs=CostBundle(),
                    effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                    risk_level=RISK_SAFE,
                    alt_cost_type="tap_mantle_vivi",
                )
                for color in ("U", "R")
            ]
        return []


# ── Spell: Rite of Flame ──────────────────────────────────────────────────────

class RiteOfFlameBehavior(CardBehavior):
    # Graveyard bonus ignored per spec.
    def resolve_cast(self, state, stack_obj):
        state.floating_mana.R += 2
        state.trace[-1].notes.append("Rite of Flame adds RR")


# ── Spell: Jeska's Will ───────────────────────────────────────────────────────

class JeskasWillBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Mode 1: add R per card in opponent's hand
        r_amount = state.jeska_opponent_hand_size
        state.floating_mana.R += r_amount
        # Mode 2 (commander in play = Vivi): exile top 3, may cast this turn
        exiled = []
        for _ in range(min(3, len(state.library))):
            card = state.library.pop(0)
            state.exile.append(card)
            exiled.append(card)
            state.permissions.append(Permission(
                card_name=card,
                zone="exile",
                action_type=CAST_SPELL,
                expires="end_of_turn",
            ))
        state.trace[-1].notes.append(
            f"Jeska's Will: +{r_amount}R, exiled {exiled} for casting"
        )


# ── Spell: Gamble ─────────────────────────────────────────────────────────────

class GambleBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        if not state.library:
            return
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="any",
            tutor_destination="hand",
            source_card="Gamble",
            post_effect="gamble_discard",
            preferred_targets=["Final Fortune", "Last Chance", "Warrior's Oath", "Lotus Petal", "Jeska's Will"],
        ))


# ── Spell: Mystical Tutor ─────────────────────────────────────────────────────

class MysticalTutorBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        if not state.library:
            return
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="instant_sorcery",
            tutor_destination="top",
            source_card="Mystical Tutor",
            preferred_targets=["Final Fortune", "Last Chance", "Warrior's Oath", "Jeska's Will",
                               "Intuition", "Solve the Equation", "Gamble", "Gitaxian Probe"],
        ))


# ── Spell: Merchant Scroll ────────────────────────────────────────────────────

class MerchantScrollBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        if not state.library:
            return
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="blue_instant",
            tutor_destination="hand",
            source_card="Merchant Scroll",
            preferred_targets=["Intuition", "Snapback", "Force of Will", "Fierce Guardianship", "Mystical Tutor"],
        ))


# ── Spell: Solve the Equation ─────────────────────────────────────────────────

class SolveTheEquationBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        if not state.library:
            return
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="instant_sorcery",
            tutor_destination="hand",
            source_card="Solve the Equation",
            preferred_targets=["Final Fortune", "Last Chance", "Warrior's Oath", "Jeska's Will",
                               "Intuition", "Gamble", "Gitaxian Probe", "Snapback"],
        ))


# ── Spell: Intuition ──────────────────────────────────────────────────────────

class IntuitionBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Greedy sim assumption: opponent always gives us the best card.
        # The player's 3-card pile choice is not modelled as a pending choice
        # because the opponent decides which you get — exposing the pile choice
        # to policy without modelling the opponent response adds noise.
        if not state.library:
            return
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="any",
            tutor_destination="hand",
            source_card="Intuition",
            post_effect="intuition_discard_two",
            preferred_targets=["Chrome Mox", "Lion's Eye Diamond", "Lotus Petal",
                               "Mox Amber", "Mox Diamond", "Mox Opal"],
        ))


# ── Spell: Dizzy Spell ────────────────────────────────────────────────────────

class DizzySpellBehavior(CardBehavior):
    # Power reduction ignored.
    _TRANSMUTE_PREFERRED = ["Gitaxian Probe", "Twisted Image", "Sol Ring", "Mana Vault", "Rite of Flame"]

    def generate_actions(self, state, card_name):
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None or card_name not in state.hand:
            return []
        actions = []
        # Instant spell mode: requires a creature target.
        from .action_generator import _get_harmful_creature_targets
        targets = _get_harmful_creature_targets(state)
        if targets:
            from .mana import can_pay_cost
            from .mana import ManaCost
            cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
            if can_pay_cost(state.floating_mana, cost):
                for t_id, t_name in targets:
                    actions.append(Action(
                        action_type=CAST_SPELL,
                        source_card=card_name,
                        description=f"Cast {card_name} targeting {t_name}",
                        costs=CostBundle(mana=cost),
                        requires_target=True,
                        target=t_id,
                        risk_level=RISK_NORMAL,
                    ))
        # Transmute mode: sorcery speed only
        if not state.stack:
            actions.append(Action(
                action_type=ACTIVATE_TRANSMUTE,
                source_card=card_name,
                description=f"Transmute {card_name} → MV=1",
                costs=CostBundle(),
                risk_level=RISK_NORMAL,
            ))
        return actions

    def resolve_cast(self, state, stack_obj):
        pass  # Power reduction not modeled

    def transmute_pending_choice(self):
        from .state import PendingChoice
        return PendingChoice(
            choice_type="tutor",
            tutor_filter="mv=1",
            tutor_destination="hand",
            source_card="Dizzy Spell (transmute)",
            preferred_targets=self._TRANSMUTE_PREFERRED,
        )


# ── Creature: Drift of Phantasms ──────────────────────────────────────────────

class DriftOfPhantasmsBehavior(CardBehavior):
    # Creature keywords ignored.
    _TRANSMUTE_PREFERRED = [
        "Alchemist's Gambit", "Final Fortune", "Last Chance", "Warrior's Oath",
        "Jeska's Will", "Intuition", "Solve the Equation", "Snapback", "Tandem Lookout",
    ]

    def generate_actions(self, state, card_name):
        from .action_generator import _gen_normal_and_alt_cast_actions
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None or card_name not in state.hand:
            return []
        actions = list(_gen_normal_and_alt_cast_actions(state, card_name, cd))
        # Transmute mode: sorcery speed only
        if not state.stack:
            actions.append(Action(
                action_type=ACTIVATE_TRANSMUTE,
                source_card=card_name,
                description=f"Transmute {card_name} → MV=3",
                costs=CostBundle(),
                risk_level=RISK_NORMAL,
            ))
        return actions

    def transmute_pending_choice(self):
        from .state import PendingChoice
        return PendingChoice(
            choice_type="tutor",
            tutor_filter="mv=3",
            tutor_destination="hand",
            source_card="Drift of Phantasms (transmute)",
            preferred_targets=self._TRANSMUTE_PREFERRED,
        )


# ── Creature: Imperial Recruiter ──────────────────────────────────────────────

class ImperialRecruiterBehavior(CardBehavior):
    _PREFERRED = ["Simian Spirit Guide", "Ragavan, Nimble Pilferer", "Tandem Lookout"]

    def on_enter(self, state, perm):
        from .state import PendingChoice
        if not state.library:
            return
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="creature_power_lte2",
            tutor_destination="hand",
            source_card="Imperial Recruiter",
            preferred_targets=self._PREFERRED,
        ))


# ── Spell: Gitaxian Probe ─────────────────────────────────────────────────────

class GitaxianProbeBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Draw 1 card on resolution (separate from Curiosity draw)
        _draw(state, 1)
        state.trace[-1].notes.append("Gitaxian Probe: drew 1")


# ── Spell: Twisted Image ──────────────────────────────────────────────────────

class TwistedImageBehavior(CardBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import _get_creature_targets, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        actions = []
        for t_id, t_name in _get_creature_targets(state):
            actions.append(_make_cast_action(
                card_name, cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name}",
            ))
        return actions

    def resolve_cast(self, state, stack_obj):
        _draw(state, 1)
        state.trace[-1].notes.append("Twisted Image: drew 1")


# ── Spell: Repeal ─────────────────────────────────────────────────────────────

class RepealBehavior(CardBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import _repeal_targets, _make_cast_action, _max_x_for
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        max_x = _max_x_for(state, cd)
        for x in range(0, max_x + 1):
            cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana,
                            x_cost=True, x_value=x)
            if not can_pay_cost(state.floating_mana, cost):
                continue
            targets = _repeal_targets(state, x)
            if not targets:
                continue
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, cost, RISK_NORMAL, cd,
                    x_value=x,
                    target=t_id,
                    description=f"Cast Repeal X={x} (bounce {t_name})",
                ))
        return actions

    def resolve_cast(self, state, stack_obj):
        _draw(state, 1)
        # Bounce target is handled when action is resolved
        if stack_obj.targets:
            target_id = stack_obj.targets[0]
            perm = state.get_perm_by_id(target_id)
            if perm:
                state.remove_perm_by_id(target_id)
                state.hand.append(perm.card_name)
                state.trace[-1].notes.append(f"Repeal bounced: {perm.card_name}")
        state.trace[-1].notes.append("Repeal: drew 1")


# ── Spell: Mogg Salvage ───────────────────────────────────────────────────────

class MoggSalvageBehavior(CardBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import _get_artifact_targets, _make_cast_action, _we_control_mountain
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        normal_cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in _get_artifact_targets(state):
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        if state.opponent_controls_island and _we_control_mountain(state):
            for t_id, t_name in _get_artifact_targets(state):
                actions.append(_make_cast_action(
                    card_name, ManaCost.zero(), RISK_SAFE, cd,
                    alt_cost_type="mogg_salvage_free",
                    target=t_id,
                    description=f"Cast {card_name} for free targeting {t_name}",
                ))
        return actions


# ── Spell: Strike It Rich ─────────────────────────────────────────────────────

class StrikeItRichBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Creates a Treasure token (sacrifice for U/R in this UR-only sim)
        from .state import Permanent
        treasure = Permanent(card_name="_Treasure", tapped=False)
        state.battlefield.append(treasure)
        state.trace[-1].notes.append("Strike It Rich: created Treasure token")


# ── Spell: Miscellaneous baubles ──────────────────────────────────────────────

class MishraBaubleBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Draw at next upkeep = not modeled; just a 0-cost noncreature spell
        pass


class UrzaBaubleBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        pass


class LodestoneBaubleBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        pass


class VexingBaubleBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        pass


# ── Creatures: Tandem Lookout ─────────────────────────────────────────────────

class TandemLookoutBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Soulbond with Vivi if available → double curiosity draws
        if state.vivi_on_battlefield:
            state.curiosity_effect_count += 1
            state.update_curiosity_draw()
            state.trace[-1].notes.append(
                f"Tandem Lookout paired with Vivi: curiosity_count={state.curiosity_effect_count}"
            )


# ── Enchantments: Curiosity, Ophidian Eye ────────────────────────────────────

class CuriosityBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Enchant Vivi → increase curiosity count
        if state.vivi_on_battlefield:
            state.curiosity_effect_count += 1
            state.update_curiosity_draw()
            state.trace[-1].notes.append(
                f"Curiosity on Vivi: curiosity_count={state.curiosity_effect_count}"
            )


class OphidianEyeBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        if state.vivi_on_battlefield:
            state.curiosity_effect_count += 1
            state.update_curiosity_draw()
            state.trace[-1].notes.append(
                f"Ophidian Eye on Vivi: curiosity_count={state.curiosity_effect_count}"
            )


# ── Misc spells with no special resolution effect ────────────────────────────

class NullBehavior(CardBehavior):
    """For spells that just resolve with no modeled effect."""
    pass


# ── Spell: Snapback ───────────────────────────────────────────────────────────

class SnapbackBehavior(CardBehavior):
    # Bounces a creature; not a counterspell.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_harmful_creature_targets, _blue_cards_in_hand_except, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_harmful_creature_targets(state)
        if not targets:
            return []
        normal_cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        for pitch in _blue_cards_in_hand_except(state, card_name):
            for t_id, t_name in targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {pitch}) targeting {t_name}",
                    costs=CostBundle(pitched_card=pitch),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_RISKY,
                    alt_cost_type="pitch_blue",
                ))
        return actions

    def resolve_cast(self, state, stack_obj):
        if not stack_obj.targets:
            return
        target_id = stack_obj.targets[0]
        perm = state.get_perm_by_id(target_id)
        if perm is None:
            return
        if perm.card_name.startswith("_opponent"):
            state.trace[-1].notes.append(f"Snapback: bounced dummy {perm.card_name}")
        else:
            state.remove_perm_by_id(target_id)
            state.hand.append(perm.card_name)
            state.trace[-1].notes.append(f"Snapback: bounced {perm.card_name} to hand")


# ── Spell: Boomerang Basics ───────────────────────────────────────────────────

class BoomerangBasicsBehavior(CardBehavior):
    # Sorcery speed; bounce nonland permanent; own → hand + draw 1; dummy → no draw.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_nonland_permanent_targets, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        if state.stack:
            return []
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        actions = []
        for t_id, t_name in _get_nonland_permanent_targets(state):
            actions.append(_make_cast_action(
                card_name, cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name}",
            ))
        return actions

    def resolve_cast(self, state, stack_obj):
        if not stack_obj.targets:
            return
        target_id = stack_obj.targets[0]
        perm = state.get_perm_by_id(target_id)
        if perm is None:
            return
        if perm.card_name.startswith("_opponent"):
            state.trace[-1].notes.append(f"Boomerang Basics: bounced dummy")
        else:
            state.remove_perm_by_id(target_id)
            state.hand.append(perm.card_name)
            _draw(state, 1)
            state.trace[-1].notes.append(f"Boomerang Basics: bounced {perm.card_name}, drew 1")


# ── Spell: Cave-In ────────────────────────────────────────────────────────────

class CaveInBehavior(CardBehavior):
    # pitch_red alt cost handled generically; custom resolve kills Ragavan/Tandem Lookout.
    # Cast still triggers normal noncreature Vivi/Curiosity draw.

    def resolve_cast(self, state, stack_obj):
        killed = []
        for name in ("Ragavan, Nimble Pilferer", "Tandem Lookout"):
            perms = state.get_permanents_by_name(name)
            for p in perms:
                state.remove_perm_by_id(p.perm_id)
                state.graveyard.append(name)
                killed.append(name)
        if killed:
            state.trace[-1].notes.append(f"Cave-In: killed {killed}")


# ── Spell: Chain of Vapor ─────────────────────────────────────────────────────

class ChainOfVaporBehavior(CardBehavior):
    # Bounce nonland permanent; optional copy by sacrificing a land.
    # Copies do not trigger Curiosity.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_nonland_permanent_targets, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        actions = []
        for t_id, t_name in _get_nonland_permanent_targets(state):
            actions.append(_make_cast_action(
                card_name, cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name}",
            ))
        return actions

    def resolve_cast(self, state, stack_obj):
        if not stack_obj.targets:
            return
        target_id = stack_obj.targets[0]
        perm = state.get_perm_by_id(target_id)
        if perm and not perm.card_name.startswith("_opponent"):
            state.remove_perm_by_id(target_id)
            state.hand.append(perm.card_name)
            state.trace[-1].notes.append(f"Chain of Vapor: bounced {perm.card_name}")
        # Optional copy: sacrifice a land to copy. Enqueue as pending chain copy if lands available.
        # Copies are not cast (no Curiosity trigger); modeled as a no-op here for now.


# ── Spell: Crowd's Favor ──────────────────────────────────────────────────────

class CrowdsFavorBehavior(CardBehavior):
    # Requires creature target; normal cast or convoke using untapped creature.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_creature_targets, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_creature_targets(state)
        if not targets:
            return []
        normal_cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        # Convoke: tap an untapped creature to pay the cost
        from .cards import get_card as gc
        for perm in state.battlefield:
            if perm.tapped:
                continue
            pcd = gc(perm.card_name)
            if pcd and pcd.is_creature:
                for t_id, t_name in targets:
                    actions.append(Action(
                        action_type=CAST_SPELL,
                        source_card=card_name,
                        description=f"Cast {card_name} (convoke {perm.card_name}) targeting {t_name}",
                        costs=CostBundle(),
                        requires_target=True,
                        target=t_id,
                        risk_level=RISK_SAFE,
                        alt_cost_type=f"convoke:{perm.perm_id}",
                    ))
        return actions


# ── Spell: Gut Shot ───────────────────────────────────────────────────────────

class GutShotBehavior(CardBehavior):
    # Requires creature/player/dummy target; normal red cost or free life-cost mode.
    # Damage ignored; useful as free spell/draw trigger.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_harmful_creature_targets, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_harmful_creature_targets(state)
        if not targets:
            targets = [("_player_self", "[self/player]")]
        normal_cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        # Free life-cost mode
        for t_id, t_name in targets:
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card=card_name,
                description=f"Cast {card_name} (pay life) targeting {t_name}",
                costs=CostBundle(pay_life=2),
                requires_target=True,
                target=t_id,
                risk_level=RISK_SAFE,
                alt_cost_type="pay_life",
            ))
        return actions


# ── Spell: Pyrokinesis ────────────────────────────────────────────────────────

class PyrokinesisBehavior(CardBehavior):
    # Requires legal creature target; normal cast or pitch red card.
    # Damage ignored; useful as free spell/draw trigger.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_harmful_creature_targets, _red_cards_in_hand_except, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_harmful_creature_targets(state)
        if not targets:
            return []
        normal_cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        for pitch in _red_cards_in_hand_except(state, card_name):
            for t_id, t_name in targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {pitch}) targeting {t_name}",
                    costs=CostBundle(pitched_card=pitch),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_RISKY,
                    alt_cost_type="pitch_red",
                ))
        return actions


# ── Spell: Redirect Lightning ─────────────────────────────────────────────────

class RedirectLightningBehavior(CardBehavior):
    # Requires normal {R} cost plus ignored additional life payment; redirection ignored.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_single_target_stack_objects
        from .cards import get_card
        from .mana import ManaCost, can_pay_cost
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        targets = _get_single_target_stack_objects(state)
        actions = []
        for t_id, t_name in targets:
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card=card_name,
                description=f"Cast {card_name} (pay life) targeting {t_name}",
                costs=CostBundle(mana=cost, pay_life=5),
                requires_target=True,
                target=t_id,
                risk_level=RISK_SAFE,
                alt_cost_type="pay_life",
            ))
        return actions


# ── Spell: Secret Identity ────────────────────────────────────────────────────

class SecretIdentityBehavior(CardBehavior):
    # Sorcery speed; requires creature target; manifest dread ignored.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_creature_targets, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        if state.stack:
            return []
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        actions = []
        for t_id, t_name in _get_creature_targets(state):
            actions.append(_make_cast_action(
                card_name, cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name}",
            ))
        return actions


# ── Spell: Thunderclap ────────────────────────────────────────────────────────

class ThunderclapBehavior(CardBehavior):
    # Requires creature target; normal cast or sacrifice Mountain.
    # Kills Ragavan/Tandem Lookout if targeted; dummy target ignored.

    def generate_actions(self, state, card_name):
        from .action_generator import _get_harmful_creature_targets, _we_control_mountain, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_harmful_creature_targets(state)
        if not targets:
            return []
        normal_cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        if _we_control_mountain(state):
            # Find a Mountain perm to sacrifice
            mountain_perm = next(
                (p for p in state.battlefield
                 if p.card_name in ("Mountain", "Volcanic Island", "Steam Vents", "Thundering Falls")),
                None,
            )
            if mountain_perm:
                for t_id, t_name in targets:
                    actions.append(Action(
                        action_type=CAST_SPELL,
                        source_card=card_name,
                        description=f"Cast {card_name} (sac Mountain) targeting {t_name}",
                        costs=CostBundle(sacrifice_permanent_id=mountain_perm.perm_id),
                        requires_target=True,
                        target=t_id,
                        risk_level=RISK_RISKY,
                        alt_cost_type="sacrifice_mountain",
                    ))
        return actions

    def resolve_cast(self, state, stack_obj):
        if not stack_obj.targets:
            return
        target_id = stack_obj.targets[0]
        perm = state.get_perm_by_id(target_id)
        if perm is None or perm.card_name.startswith("_opponent"):
            return
        if perm.card_name in ("Ragavan, Nimble Pilferer", "Tandem Lookout"):
            state.remove_perm_by_id(target_id)
            state.graveyard.append(perm.card_name)
            state.trace[-1].notes.append(f"Thunderclap: killed {perm.card_name}")


# ── Baubles: activated tap/sac abilities ─────────────────────────────────────

class MishraBaubleBehavior(CardBehavior):
    # Delayed next-upkeep draw ignored.
    def resolve_cast(self, state, stack_obj):
        pass  # enters battlefield

    def generate_activate_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=SACRIFICE_FOR_MANA,
            source_card="Mishra's Bauble",
            description="Mishra's Bauble: tap, sac, target player (no immediate draw)",
            costs=CostBundle(tap_permanent_id=perm.perm_id, sacrifice_permanent_id=perm.perm_id),
            effects=EffectBundle(),
            risk_level=RISK_SAFE,
        )]


class UrzaBaubleBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        pass  # enters battlefield

    def generate_activate_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=SACRIFICE_FOR_MANA,
            source_card="Urza's Bauble",
            description="Urza's Bauble: tap, sac, target player (no immediate draw)",
            costs=CostBundle(tap_permanent_id=perm.perm_id, sacrifice_permanent_id=perm.perm_id),
            effects=EffectBundle(),
            risk_level=RISK_SAFE,
        )]


class LodestoneBaubleBehavior(CardBehavior):
    # Actual ability putting basics on libraries is ignored.
    def resolve_cast(self, state, stack_obj):
        pass  # enters battlefield

    def generate_activate_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=SACRIFICE_FOR_MANA,
            source_card="Lodestone Bauble",
            description="Lodestone Bauble: tap, sac (library effect ignored)",
            costs=CostBundle(tap_permanent_id=perm.perm_id, sacrifice_permanent_id=perm.perm_id),
            effects=EffectBundle(),
            risk_level=RISK_SAFE,
        )]


class VexingBaubleBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        pass  # enters battlefield

    def generate_activate_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=SACRIFICE_FOR_MANA,
            source_card="Vexing Bauble",
            description="Vexing Bauble: tap, sac (no draw)",
            costs=CostBundle(tap_permanent_id=perm.perm_id, sacrifice_permanent_id=perm.perm_id),
            effects=EffectBundle(),
            risk_level=RISK_SAFE,
        )]


# ── Spell: Blazing Shoal ─────────────────────────────────────────────────────

# ── Treasure token behavior ───────────────────────────────────────────────────

class TreasureBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        return [
            Action(
                action_type=SACRIFICE_FOR_MANA,
                source_card="_Treasure",
                description=f"Sacrifice Treasure token for {{{color}}}",
                costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
            )
            for color in ("U", "R")
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw(state: GameState, n: int) -> None:
    from .resolver import draw_cards
    draw_cards(state, n)


# ── Counterspells ─────────────────────────────────────────────────────────────

class CounterspellBehavior(CardBehavior):
    """Removes the targeted stack object when this counterspell resolves."""

    def __init__(self, target_filter: str = "any"):
        self.target_filter = target_filter

    def get_stack_targets(self, state):
        from .action_generator import _get_typed_stack_targets
        return _get_typed_stack_targets(state, self.target_filter)

    def resolve_cast(self, state, stack_obj):
        if not stack_obj.targets:
            return
        target_id = stack_obj.targets[0]
        target_obj = state.get_stack_object(target_id)
        if target_obj is None:
            return  # already resolved or removed

        # Disrupting Shoal: only counters if pitched card MV (= x_value) matches target MV
        if stack_obj.card_name == "Disrupting Shoal":
            from .cards import get_card
            target_cd = get_card(target_obj.card_name)
            target_mv = target_cd.mv if target_cd else -1
            if stack_obj.x_value != target_mv:
                state.trace[-1].notes.append(
                    f"Disrupting Shoal failed: pitch MV={stack_obj.x_value} "
                    f"≠ {target_obj.card_name} MV={target_mv}"
                )
                return

        # Counter: remove target from stack, send to graveyard (or exile if flashback)
        state.remove_stack_object(target_id)
        dest = "exile" if target_obj.alt_cost_used == "flashback" else "graveyard"
        getattr(state, dest).append(target_obj.card_name)
        state.trace[-1].notes.append(
            f"{stack_obj.card_name} countered {target_obj.card_name} → {dest}"
        )


# ── Spell: Mental Misstep ────────────────────────────────────────────────────

class MentalMisstepBehavior(CounterspellBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import (
            _get_mv1_stack_targets, _get_any_stack_targets, _make_cast_action,
        )
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        normal_cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in _get_mv1_stack_targets(state):
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        for t_id, t_name in _get_mv1_stack_targets(state):
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
        return actions


# ── Spell: Misdirection ───────────────────────────────────────────────────────

class MisdirectionBehavior(CounterspellBehavior):

    def resolve_cast(self, state, stack_obj):
        # Target-changing has no modeled effect; action mainly provides free spell/draw trigger.
        pass

    def generate_actions(self, state, card_name):
        from .action_generator import (
            _get_any_stack_targets, _get_single_target_stack_objects,
            _blue_cards_in_hand_except, _make_cast_action,
        )
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        normal_cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in _get_any_stack_targets(state):
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        blue_pitches = _blue_cards_in_hand_except(state, card_name)
        for pitch in blue_pitches:
            for t_id, t_name in _get_single_target_stack_objects(state):
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
        return actions


# ── Spell: Daze ──────────────────────────────────────────────────────────────

class DazeBehavior(CounterspellBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import (
            _get_any_stack_targets, _islands_on_battlefield, _make_cast_action,
        )
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        normal_cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in _get_any_stack_targets(state):
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        islands = _islands_on_battlefield(state)
        if islands:
            for t_id, t_name in _get_any_stack_targets(state):
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (return island) targeting {t_name}",
                    costs=CostBundle(return_land_to_hand=True,
                                     tap_permanent_id=islands[0].perm_id),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_EXPENSIVE,
                    alt_cost_type="return_island",
                ))
        return actions


# ── Spell: Pact of Negation ───────────────────────────────────────────────────

class PactOfNegationBehavior(CounterspellBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import _get_any_stack_targets
        actions = []
        for t_id, t_name in _get_any_stack_targets(state):
            actions.append(Action(
                action_type=CAST_SPELL,
                source_card=card_name,
                description=f"Cast {card_name} (free) targeting {t_name}",
                costs=CostBundle(),
                requires_target=True,
                target=t_id,
                risk_level=RISK_NORMAL,
                alt_cost_type="delayed_upkeep",
            ))
        return actions


# ── Spell: Disrupting Shoal ───────────────────────────────────────────────────

class DisruptingShoalBehavior(CounterspellBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import (
            _get_any_stack_targets, _blue_cards_in_hand_except,
            _make_cast_action, _stack_object_mv_by_name,
        )
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        normal_cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana, x_cost=cd.x_in_cost)
        # Normal X-cost cast
        from .mana import can_pay_cost as _cpc
        from .action_generator import _max_x_for
        max_x = _max_x_for(state, cd)
        for x in range(0, max_x + 1):
            cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana, x_cost=True, x_value=x)
            if can_pay_cost(state.floating_mana, cost):
                for t_id, t_name in _get_any_stack_targets(state):
                    actions.append(_make_cast_action(
                        card_name, cost, RISK_NORMAL, cd,
                        x_value=x, target=t_id,
                        description=f"Cast {card_name} (X={x}) targeting {t_name}",
                    ))
        # Pitch alt cost
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
        return actions


# ── Spell: An Offer You Can't Refuse ─────────────────────────────────────────

class AnOfferYouCantRefuseBehavior(CounterspellBehavior):
    # Counters noncreature spells; opponent gets Treasures (modeled as own Treasures since no real opponent).
    def __init__(self):
        super().__init__(target_filter="noncreature")

    def resolve_cast(self, state, stack_obj):
        super().resolve_cast(state, stack_obj)
        # Create 2 Treasure tokens (opponent would receive them in real game; sim gives them to self)
        from .state import Permanent
        for _ in range(2):
            state.battlefield.append(Permanent(card_name="_Treasure", tapped=False))
        state.trace[-1].notes.append("An Offer You Can't Refuse: created 2 Treasure tokens")


# ── Spell: Commandeer ─────────────────────────────────────────────────────────

class CommandeerBehavior(CardBehavior):
    # Gains control of target noncreature spell; for own spells (all spells in sim) no effect and target remains on stack.
    def generate_actions(self, state, card_name):
        from .action_generator import (
            _get_typed_stack_targets, _blue_cards_in_hand_except, _make_cast_action,
        )
        from .mana import can_pay_cost
        from .cards import get_card
        from itertools import combinations
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_typed_stack_targets(state, "noncreature")
        normal_cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        blue_cards = _blue_cards_in_hand_except(state, card_name)
        for card1, card2 in combinations(blue_cards, 2):
            for t_id, t_name in targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {card1}, {card2}) targeting {t_name}",
                    costs=CostBundle(pitch_blue_count=2, pitched_card=card1, pitched_card_2=card2),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_DESPERATE,
                    alt_cost_type="pitch_blue_blue",
                ))
        return actions

    def resolve_cast(self, state, stack_obj):
        # Target-changing control effect; own spells remain on stack unmodified.
        pass


# ── Spell: Deflecting Swat ────────────────────────────────────────────────────

class DeflectingSwatBehavior(CardBehavior):
    # Redirects a target; no modeled effect. Free if commander (Vivi) is on battlefield.
    def generate_actions(self, state, card_name):
        from .action_generator import _get_single_target_stack_objects, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_single_target_stack_objects(state)
        # Free if commander controlled
        if state.vivi_on_battlefield:
            for t_id, t_name in targets:
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
        # Normal cast
        normal_cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        return actions

    def resolve_cast(self, state, stack_obj):
        # Target-changing has no modeled effect.
        pass


# ── Spell: Fierce Guardianship ────────────────────────────────────────────────

class FierceGuardianshipBehavior(CounterspellBehavior):
    # Counters noncreature spells; free if commander (Vivi) is on battlefield.
    def __init__(self):
        super().__init__(target_filter="noncreature")

    def generate_actions(self, state, card_name):
        from .action_generator import _get_typed_stack_targets, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []
        targets = _get_typed_stack_targets(state, "noncreature")
        # Free if commander controlled
        if state.vivi_on_battlefield:
            for t_id, t_name in targets:
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
        # Normal cast
        normal_cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if can_pay_cost(state.floating_mana, normal_cost):
            for t_id, t_name in targets:
                actions.append(_make_cast_action(
                    card_name, normal_cost, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast {card_name} targeting {t_name}",
                ))
        return actions


# ── Spell: Pyroblast ──────────────────────────────────────────────────────────

class PyroblastBehavior(CardBehavior):

    def generate_actions(self, state, card_name):
        from .action_generator import (
            _get_typed_stack_targets, _get_blue_permanents, _make_cast_action,
        )
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        normal_cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, normal_cost):
            return []
        actions = []
        for t_id, t_name in _get_typed_stack_targets(state, "blue_spell"):
            actions.append(_make_cast_action(
                card_name, normal_cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name} (counter)",
            ))
        for t_id, t_name in _get_blue_permanents(state):
            actions.append(_make_cast_action(
                card_name, normal_cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name} (destroy)",
            ))
        return actions

    def resolve_cast(self, state, stack_obj):
        if not stack_obj.targets:
            return
        target_id = stack_obj.targets[0]
        # Stack target: counter the spell
        target_obj = state.get_stack_object(target_id)
        if target_obj is not None:
            state.remove_stack_object(target_id)
            dest = "exile" if target_obj.alt_cost_used == "flashback" else "graveyard"
            getattr(state, dest).append(target_obj.card_name)
            state.trace[-1].notes.append(
                f"Pyroblast countered {target_obj.card_name} → {dest}"
            )
            return
        # Permanent target: destroy it
        perm = state.remove_perm_by_id(target_id)
        if perm is not None:
            state.graveyard.append(perm.card_name)
            state.trace[-1].notes.append(f"Pyroblast destroyed {perm.card_name}")


# ── Spell: Blazing Shoal ─────────────────────────────────────────────────────

class BlazingShoalBehavior(CardBehavior):
    # Power boost not modeled; card is useful as free spell/draw trigger.

    def generate_actions(self, state, card_name):
        from .action_generator import (
            _get_creature_targets, _red_cards_in_hand_except,
            _stack_object_mv_by_name, _make_cast_action, _max_x_for,
        )
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        targets = _get_creature_targets(state)
        if not targets:
            return []
        actions = []
        max_x = _max_x_for(state, cd)
        for x in range(0, max_x + 1):
            cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana, x_cost=True, x_value=x)
            if can_pay_cost(state.floating_mana, cost):
                for t_id, t_name in targets:
                    actions.append(_make_cast_action(
                        card_name, cost, RISK_NORMAL, cd,
                        x_value=x,
                        target=t_id,
                        description=f"Cast {card_name} X={x} targeting {t_name}",
                    ))
        red_pitches = _red_cards_in_hand_except(state, card_name)
        for pitch in red_pitches:
            pitch_mv = _stack_object_mv_by_name(pitch)
            for t_id, t_name in targets:
                actions.append(Action(
                    action_type=CAST_SPELL,
                    source_card=card_name,
                    description=f"Cast {card_name} (pitch {pitch}, X={pitch_mv}) targeting {t_name}",
                    costs=CostBundle(pitched_card=pitch),
                    requires_target=True,
                    target=t_id,
                    risk_level=RISK_RISKY,
                    alt_cost_type="pitch_red_x",
                    x_value=pitch_mv,
                ))
        return actions


# ── Split card: Invert // Invent ──────────────────────────────────────────────

class InvertInventBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        if stack_obj.alt_cost_used != "invent_face":
            return  # Invert half: swap P/T, no modeled effect

        if not state.library:
            return
        from .state import PendingChoice
        # Queue both tutors; instant resolves first (index 0), then sorcery.
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="instant",
            tutor_destination="hand",
            source_card="Invent (instant)",
            preferred_targets=["Snapback", "Force of Will", "Fierce Guardianship", "Intuition", "Mystical Tutor"],
        ))
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="sorcery",
            tutor_destination="hand",
            source_card="Invent (sorcery)",
            preferred_targets=["Final Fortune", "Last Chance", "Warrior's Oath", "Jeska's Will",
                               "Solve the Equation", "Gamble", "Rite of Flame"],
        ))


# ── Fetchlands ────────────────────────────────────────────────────────────────

class FetchlandBehavior(CardBehavior):
    """Fetchland with a fixed fetch priority list (island-fetchlands and mountain-fetchlands)."""

    def __init__(self, priority: list[str]) -> None:
        self._priority = priority

    def generate_mana_actions(self, state: "GameState", perm: "Permanent") -> list[Action]:
        if not perm.counters.get("fetchable"):
            return []
        for card_name in self._priority:
            if card_name in state.library:
                return [Action(
                    action_type=FETCH_LAND,
                    source_card=perm.card_name,
                    description=f"Fetch {card_name} with {perm.card_name}",
                    costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
                    effects=EffectBundle(fetch_target_card=card_name),
                    risk_level=RISK_SAFE,
                )]
        return []


class FetchlandFlexBehavior(CardBehavior):
    """Fetchland that can fetch either of two basics if no dual is available (Scalding Tarn, Prismatic Vista)."""

    def __init__(self, shared_priority: list[str], basics: list[str]) -> None:
        self._shared = shared_priority
        self._basics = basics

    def generate_mana_actions(self, state: "GameState", perm: "Permanent") -> list[Action]:
        if not perm.counters.get("fetchable"):
            return []
        for card_name in self._shared:
            if card_name in state.library:
                return [Action(
                    action_type=FETCH_LAND,
                    source_card=perm.card_name,
                    description=f"Fetch {card_name} with {perm.card_name}",
                    costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
                    effects=EffectBundle(fetch_target_card=card_name),
                    risk_level=RISK_SAFE,
                )]
        return [
            Action(
                action_type=FETCH_LAND,
                source_card=perm.card_name,
                description=f"Fetch {card_name} with {perm.card_name}",
                costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
                effects=EffectBundle(fetch_target_card=card_name),
                risk_level=RISK_SAFE,
            )
            for card_name in self._basics
            if card_name in state.library
        ]


# ── MDFC Lands ────────────────────────────────────────────────────────────────
# Bucket logic: spell faces use card-specific behavior; land faces (untapped, fixed color)
# are handled by generic action_generator scaffolding via can_play_as_land + mana_colors.

class _MDFCLandMixin:
    """Delegates mana generation to _default_mana_actions so MDFC land faces tap correctly."""
    def generate_mana_actions(self, state, perm):
        from .action_generator import _default_mana_actions
        from .cards import get_card
        cd = get_card(perm.card_name)
        if cd is None:
            return []
        return _default_mana_actions(state, perm, cd)


class HydroelectricSpecimenBehavior(_MDFCLandMixin, CardBehavior):
    # Skip lifeloss. ETB effect modeled mainly to create targetable stack context.
    def on_enter(self, state, perm):
        from .stack import StackObject
        # Push a triggered ETB ability onto the stack so it can be targeted by Deflecting Swat.
        state.stack.append(StackObject(card_name="Hydroelectric Specimen ETB"))


class PinnacleMOnkBehavior(_MDFCLandMixin, CardBehavior):
    # Skip lifeloss.
    def on_enter(self, state, perm):
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="graveyard_return",
            tutor_filter="instant_sorcery",
            source_card="Pinnacle Monk / Mystic Peak",
        ))


class SeaGateRestorationBehavior(_MDFCLandMixin, CardBehavior):
    # Skip lifeloss; no maximum hand size modeled.
    def resolve_cast(self, state, stack_obj):
        draw_count = len(state.hand) + 1
        _draw(state, draw_count)
        state.trace[-1].notes.append(f"Sea Gate Restoration: drew {draw_count}")


class ShatterSkullSmashingBehavior(_MDFCLandMixin, CardBehavior):
    # Skip lifeloss; damage mode ignored; only X=0 cast needed.
    def generate_actions(self, state, card_name):
        from .action_generator import _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        if state.stack:
            return []
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana, x_cost=True, x_value=0)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        actions = [_make_cast_action(card_name, cost, RISK_NORMAL, cd, x_value=0)]
        return actions


class SinkIntoStuporBehavior(_MDFCLandMixin, CardBehavior):
    # Skip lifeloss; owner-library placement simplified away.
    def generate_actions(self, state, card_name):
        from .action_generator import _get_opponent_permanent_target, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_u=cd.pip_u, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        actions = []
        for t_id, t_name in _get_opponent_permanent_target(state):
            actions.append(_make_cast_action(
                card_name, cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name}",
            ))
        return actions


class SunderingEruptionBehavior(_MDFCLandMixin, CardBehavior):
    # Skip lifeloss; land destruction only modeled against dummy target.
    def generate_actions(self, state, card_name):
        from .action_generator import _get_opponent_land_target, _make_cast_action
        from .mana import can_pay_cost
        from .cards import get_card
        if state.stack:
            return []
        cd = get_card(card_name)
        if cd is None:
            return []
        cost = ManaCost(pip_r=cd.pip_r, generic=cd.generic_mana)
        if not can_pay_cost(state.floating_mana, cost):
            return []
        actions = []
        for t_id, t_name in _get_opponent_land_target(state):
            actions.append(_make_cast_action(
                card_name, cost, RISK_NORMAL, cd,
                target=t_id,
                description=f"Cast {card_name} targeting {t_name}",
            ))
        return actions


# ── Other Lands ───────────────────────────────────────────────────────────────

class FieryIsletBehavior(CardBehavior):
    """Taps for U or R; also has a sacrifice ability: pay {1}, tap, sac → draw 1."""
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        actions = [
            Action(
                action_type=ACTIVATE_MANA_ABILITY,
                source_card="Fiery Islet",
                description=f"Tap Fiery Islet for {{{color}}}",
                costs=CostBundle(tap_permanent_id=perm.perm_id),
                effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                risk_level=RISK_SAFE,
            )
            for color in ("U", "R")
        ]
        # Draw ability: {1}, T, sacrifice Fiery Islet → draw a card
        from .mana import can_pay_cost
        draw_cost = ManaCost(generic=1)
        if can_pay_cost(state.floating_mana, draw_cost):
            actions.append(Action(
                action_type=SACRIFICE_FOR_MANA,
                source_card="Fiery Islet",
                description="Fiery Islet: pay {1}, sac → draw 1",
                costs=CostBundle(
                    mana=draw_cost,
                    tap_permanent_id=perm.perm_id,
                    sacrifice_permanent_id=perm.perm_id,
                ),
                effects=EffectBundle(draw_cards=1),
                risk_level=RISK_SAFE,
            ))
        return actions


class GemstonesCavernsBehavior(CardBehavior):
    """Taps for U/R if luck counter present, else colorless only."""
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        has_luck = perm.counters.get("luck_counter", 0) > 0
        if has_luck:
            return [
                Action(
                    action_type=ACTIVATE_MANA_ABILITY,
                    source_card="Gemstone Caverns",
                    description=f"Tap Gemstone Caverns for {{{color}}}",
                    costs=CostBundle(tap_permanent_id=perm.perm_id),
                    effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                    risk_level=RISK_SAFE,
                )
                for color in ("U", "R")
            ]
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Gemstone Caverns",
            description="Tap Gemstone Caverns for {C}",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(C=1)),
            risk_level=RISK_SAFE,
        )]


class CavernOfSoulsBehavior(CardBehavior):
    """Taps for {C} always; if creatures in hand, also offers colored mana for creature spells."""
    def generate_mana_actions(self, state, perm):
        from .cards import get_card as _get_card
        if perm.tapped:
            return []
        actions = [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Cavern of Souls",
            description="Tap Cavern of Souls for {C}",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(C=1)),
            risk_level=RISK_SAFE,
        )]
        has_creature_in_hand = any(
            (cd := _get_card(c)) and cd.is_creature
            for c in state.hand
        )
        if has_creature_in_hand:
            for color in ("U", "R"):
                actions.append(Action(
                    action_type=ACTIVATE_MANA_ABILITY,
                    source_card="Cavern of Souls",
                    description=f"Tap Cavern of Souls for {{{color}}} (creature spells only)",
                    costs=CostBundle(tap_permanent_id=perm.perm_id),
                    effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
                    risk_level=RISK_SAFE,
                ))
        return actions


class ChooseLandTypeBehavior(CardBehavior):
    """Enters untapped; creates pending basic-type choice (Island or Mountain); taps for chosen color."""

    def on_enter(self, state, perm):
        from .state import PendingChoice
        state.pending_choices.append(PendingChoice(
            choice_type="land_type",
            perm_id=perm.perm_id,
            source_card=perm.card_name,
        ))

    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        land_type = perm.counters.get("land_type")
        if land_type is None:
            return []  # Choice not yet resolved
        color = "U" if land_type == "Island" else "R"
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card=perm.card_name,
            description=f"Tap {perm.card_name} for {{{color}}}",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
            risk_level=RISK_SAFE,
        )]


class ThranPortalBehavior(ChooseLandTypeBehavior):
    """Enters tapped if more than 2 other lands on the battlefield; otherwise untapped."""

    def on_enter(self, state, perm):
        from .cards import get_card as _get_card
        other_land_count = sum(
            1 for p in state.battlefield
            if p.perm_id != perm.perm_id and (cd := _get_card(p.card_name)) and cd.is_land
        )
        if other_land_count > 2:
            perm.tapped = True
        super().on_enter(state, perm)


# ── Creature: Niv-Mizzet, Visionary ──────────────────────────────────────────

class NivMizzetVisionaryBehavior(CardBehavior):
    # Full printed trigger details simplified to Curiosity-like draw engine.
    def resolve_cast(self, state, stack_obj):
        state.curiosity_effect_count += 1
        state.update_curiosity_draw()
        state.trace[-1].notes.append(
            f"Niv-Mizzet, Visionary: curiosity_count={state.curiosity_effect_count}"
        )


# ── Enchantment: Virtue of Courage / Embereth Blaze ──────────────────────────

class VirtueOfCourageBehavior(CardBehavior):
    # Embereth Blaze damage ignored; Virtue trigger is modeled through Vivi damage to opponents.
    CARD_NAME = "Virtue of Courage / Embereth Blaze"
    ADVENTURE_COST = ManaCost(pip_r=1, generic=1)   # {1}{R}
    VIRTUE_COST    = ManaCost(pip_r=2, generic=3)   # {3}{R}{R}

    def generate_actions(self, state, card_name):
        from .action_generator import _make_cast_action, _get_creature_targets
        from .mana import can_pay_cost
        from .cards import get_card
        cd = get_card(card_name)
        if cd is None:
            return []
        actions = []

        # Normal enchantment cast from hand (sorcery speed)
        if not state.stack and can_pay_cost(state.floating_mana, self.VIRTUE_COST):
            actions.append(_make_cast_action(card_name, self.VIRTUE_COST, RISK_NORMAL, cd))

        # Adventure: cast Embereth Blaze (instant speed) from hand, targeting a creature
        if can_pay_cost(state.floating_mana, self.ADVENTURE_COST):
            for t_id, t_name in _get_creature_targets(state):
                actions.append(_make_cast_action(
                    card_name, self.ADVENTURE_COST, RISK_NORMAL, cd,
                    target=t_id,
                    description=f"Cast Embereth Blaze (adventure) targeting {t_name}",
                    alt_cost_type="adventure",
                ))

        return actions

    def resolve_cast(self, state, stack_obj):
        if stack_obj.alt_cost_used == "adventure":
            # Embereth Blaze resolves: exile the card with permission to cast Virtue side
            state.exile.append(self.CARD_NAME)
            state.permissions.append(Permission(
                card_name=self.CARD_NAME,
                zone="exile",
                action_type=CAST_SPELL,
                expires="end_of_turn",
            ))
            state.trace[-1].notes.append(
                "Embereth Blaze resolved: Virtue of Courage exiled with cast permission"
            )
        # Normal enchantment resolution: just enters battlefield via resolver

    def on_enter(self, state, perm):
        state.virtue_of_courage_on_battlefield = True
        state.trace[-1].notes.append("Virtue of Courage entered battlefield")


# ── Registry ──────────────────────────────────────────────────────────────────

CARD_BEHAVIORS: dict[str, CardBehavior] = {
    "Sol Ring":            SolRingBehavior(),
    "Mana Vault":          ManaVaultBehavior(),
    "Grim Monolith":       GrimMonolithBehavior(),
    "Lotus Petal":         LotusPetalBehavior(),
    "Lion's Eye Diamond":  LionsEyeDiamondBehavior(),
    "Chrome Mox":          ChromeMoxBehavior(),
    "Mox Diamond":         MoxDiamondBehavior(),
    "Mox Opal":            MoxOpalBehavior(),
    "Mox Amber":           MoxAmberBehavior(),
    "Springleaf Drum":     SpringleafDrumBehavior(),
    "Simian Spirit Guide": SimianSpiritGuideBehavior(),
    "Jeweled Amulet":      JeweledAmuletBehavior(),
    "Paradise Mantle":     ParadiseMantleBehavior(),
    "Rite of Flame":       RiteOfFlameBehavior(),
    "Jeska's Will":        JeskasWillBehavior(),
    "Dizzy Spell":         DizzySpellBehavior(),
    "Drift of Phantasms":  DriftOfPhantasmsBehavior(),
    "Imperial Recruiter":  ImperialRecruiterBehavior(),
    "Gamble":              GambleBehavior(),
    "Mystical Tutor":      MysticalTutorBehavior(),
    "Merchant Scroll":     MerchantScrollBehavior(),
    "Solve the Equation":  SolveTheEquationBehavior(),
    "Intuition":           IntuitionBehavior(),
    "Gitaxian Probe":      GitaxianProbeBehavior(),
    "Twisted Image":       TwistedImageBehavior(),
    "Mogg Salvage":        MoggSalvageBehavior(),
    "Repeal":              RepealBehavior(),
    "Strike It Rich":      StrikeItRichBehavior(),
    "Mishra's Bauble":     MishraBaubleBehavior(),
    "Urza's Bauble":       UrzaBaubleBehavior(),
    "Lodestone Bauble":    LodestoneBaubleBehavior(),
    "Vexing Bauble":       VexingBaubleBehavior(),
    "Boomerang Basics":    BoomerangBasicsBehavior(),
    "Cave-In":             CaveInBehavior(),
    "Chain of Vapor":      ChainOfVaporBehavior(),
    "Crowd's Favor":       CrowdsFavorBehavior(),
    "Gut Shot":            GutShotBehavior(),
    "Pyrokinesis":         PyrokinesisBehavior(),
    "Redirect Lightning":  RedirectLightningBehavior(),
    "Secret Identity":     SecretIdentityBehavior(),
    "Thunderclap":         ThunderclapBehavior(),
    "Wild Ride":           NullBehavior(),
    "Tandem Lookout":      TandemLookoutBehavior(),
    "Curiosity":           CuriosityBehavior(),
    "Ophidian Eye":        OphidianEyeBehavior(),
    "Niv-Mizzet, Visionary":              NivMizzetVisionaryBehavior(),
    "Virtue of Courage / Embereth Blaze": VirtueOfCourageBehavior(),
    "Invert / Invent":     InvertInventBehavior(),
    "_Treasure":           TreasureBehavior(),
    # Counterspells — CounterspellBehavior removes the targeted stack object on resolution
    "Force of Will":              CounterspellBehavior(),
    "Fierce Guardianship":        FierceGuardianshipBehavior(),
    "Pact of Negation":           PactOfNegationBehavior(),
    "Swan Song":                  CounterspellBehavior(target_filter="instant_sorcery_enchantment"),
    "Flusterstorm":               CounterspellBehavior(target_filter="instant_sorcery"),
    "Mental Misstep":             MentalMisstepBehavior(),
    "Daze":                       DazeBehavior(),
    "Snapback":                   SnapbackBehavior(),
    "An Offer You Can't Refuse":  AnOfferYouCantRefuseBehavior(),
    "Disrupting Shoal":           DisruptingShoalBehavior(),
    "Blazing Shoal":              BlazingShoalBehavior(),
    "Commandeer":                 CommandeerBehavior(),
    "Misdirection":               MisdirectionBehavior(),
    "Deflecting Swat":            DeflectingSwatBehavior(),
    "Pyroblast":                  PyroblastBehavior(),
    # Generic No-Op Permanents — opponent-cast triggers ignored; opponents do not cast spells in this sim
    "Mystic Remora":              NullBehavior(),
    "Rhystic Study":              NullBehavior(),
    # Fetchlands
    "Arid Mesa":        FetchlandBehavior(["Volcanic Island", "Steam Vents", "Mountain"]),
    "Bloodstained Mire": FetchlandBehavior(["Volcanic Island", "Steam Vents", "Mountain"]),
    "Flooded Strand":   FetchlandBehavior(["Volcanic Island", "Steam Vents", "Island"]),
    "Misty Rainforest": FetchlandBehavior(["Volcanic Island", "Steam Vents", "Island"]),
    "Polluted Delta":   FetchlandBehavior(["Volcanic Island", "Steam Vents", "Island"]),
    "Scalding Tarn":    FetchlandFlexBehavior(["Volcanic Island", "Steam Vents"], ["Island", "Mountain"]),
    "Wooded Foothills": FetchlandBehavior(["Volcanic Island", "Steam Vents", "Mountain"]),
    "Prismatic Vista":  FetchlandFlexBehavior([], ["Island", "Mountain"]),
    # Other Lands
    "Fiery Islet":        FieryIsletBehavior(),
    "Gemstone Caverns":   GemstonesCavernsBehavior(),
    "Cavern of Souls":    CavernOfSoulsBehavior(),
    "Multiversal Passage": ChooseLandTypeBehavior(),
    "Thran Portal":       ThranPortalBehavior(),
    # MDFC Lands
    "Hydroelectric Specimen / Hydroelectric Laboratory": HydroelectricSpecimenBehavior(),
    "Pinnacle Monk / Mystic Peak":                       PinnacleMOnkBehavior(),
    "Sea Gate Restoration / Sea Gate, Reborn":           SeaGateRestorationBehavior(),
    "Shatterskull Smashing / Shatterskull, the Hammer Pass": ShatterSkullSmashingBehavior(),
    "Sink into Stupor / Soporific Springs":              SinkIntoStuporBehavior(),
    "Sundering Eruption / Volcanic Fissure":             SunderingEruptionBehavior(),
}
