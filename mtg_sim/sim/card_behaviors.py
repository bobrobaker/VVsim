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
    CAST_SPELL, ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA, SACRIFICE_FOR_MANA,
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
            for color in ("U", "R", "C")
        ]


# ── Mana: Lion's Eye Diamond ─────────────────────────────────────────────────

class LionsEyeDiamondBehavior(CardBehavior):
    """Tap, sacrifice, discard hand → add 3 of chosen color (RRR by default)."""

    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        actions = []
        for color, label in [("R", "RRR"), ("U", "UUU"), ("C", "CCC")]:
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
        color = "U" if imp.has_blue else "R" if imp.has_red else None
        if color is None:
            return []
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Chrome Mox",
            description=f"Tap Chrome Mox (imprinted {perm.imprinted_card}) for {{{color}}}",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(**{color: 1})),
            risk_level=RISK_SAFE,
        )]

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
            for color in ("U", "R", "C")
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
            for color in ("U", "R", "C")
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
            for color in ("U", "R", "C")
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


# ── Spell: Rite of Flame ──────────────────────────────────────────────────────

class RiteOfFlameBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        n = state.count_rites_in_graveyard()
        total = 2 + n
        state.floating_mana.R += total
        state.trace[-1].notes.append(f"Rite of Flame adds {total}R (graveyard bonus: {n})")


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
        # Creates a Treasure token (sacrifice for any color)
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
            for color in ("U", "R", "C")
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw(state: GameState, n: int) -> None:
    from .resolver import draw_cards
    draw_cards(state, n)


# ── Counterspells ─────────────────────────────────────────────────────────────

class CounterspellBehavior(CardBehavior):
    """Removes the targeted stack object when this counterspell resolves."""

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
        ))
        state.pending_choices.append(PendingChoice(
            choice_type="tutor",
            tutor_filter="sorcery",
            tutor_destination="hand",
            source_card="Invent (sorcery)",
        ))


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
    "Rite of Flame":       RiteOfFlameBehavior(),
    "Jeska's Will":        JeskasWillBehavior(),
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
    "Tandem Lookout":      TandemLookoutBehavior(),
    "Curiosity":           CuriosityBehavior(),
    "Ophidian Eye":        OphidianEyeBehavior(),
    "Invert / Invent":     InvertInventBehavior(),
    "_Treasure":           TreasureBehavior(),
    # Counterspells — CounterspellBehavior removes the targeted stack object on resolution
    "Force of Will":              CounterspellBehavior(),
    "Fierce Guardianship":        CounterspellBehavior(),
    "Pact of Negation":           CounterspellBehavior(),
    "Swan Song":                  CounterspellBehavior(),
    "Flusterstorm":               CounterspellBehavior(),
    "Mental Misstep":             MentalMisstepBehavior(),
    "Daze":                       CounterspellBehavior(),
    "Snapback":                   CounterspellBehavior(),
    "An Offer You Can't Refuse":  CounterspellBehavior(),
    "Disrupting Shoal":           CounterspellBehavior(),
    "Commandeer":                 CounterspellBehavior(),
    "Misdirection":               MisdirectionBehavior(),
}
