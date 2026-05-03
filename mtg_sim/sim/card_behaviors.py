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
    def generate_actions(self, state: GameState, card_name: str) -> list[Action]:
        return []

    def generate_mana_actions(self, state: GameState, perm: Permanent) -> list[Action]:
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
        return [Action(
            action_type=SACRIFICE_FOR_MANA,
            source_card="Lotus Petal",
            description="Sacrifice Lotus Petal for 1 mana",
            costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(ANY=1)),
            risk_level=RISK_SAFE,
        )]


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

    def on_enter(self, state, perm):
        from .cards import get_card
        # Choose cheapest non-artifact non-land colored card to imprint
        candidates = [
            c for c in state.hand
            if (cd := get_card(c)) and not cd.is_artifact and not cd.is_land
            and (cd.has_blue or cd.has_red) and c != "Chrome Mox"
        ]
        if not candidates:
            return
        # Prefer lowest-MV card (least valuable to imprint)
        candidates.sort(key=lambda c: get_card(c).mv)
        chosen = candidates[0]
        state.hand.remove(chosen)
        state.exile.append(chosen)
        perm.imprinted_card = chosen

    def resolve_cast(self, state, stack_obj):
        pass


# ── Mana: Mox Diamond ────────────────────────────────────────────────────────

class MoxDiamondBehavior(CardBehavior):
    def on_enter(self, state, perm):
        # Discard a land on ETB or sacrifice Mox Diamond
        lands = state.lands_in_hand()
        if lands:
            chosen = lands[0]
            state.hand.remove(chosen)
            state.graveyard.append(chosen)
        else:
            # Must sacrifice
            state.remove_perm_by_id(perm.perm_id)
            state.graveyard.append("Mox Diamond")

    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Mox Diamond",
            description="Tap Mox Diamond for 1 mana",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(ANY=1)),
            risk_level=RISK_SAFE,
        )]


# ── Mana: Mox Opal (metalcraft) ──────────────────────────────────────────────

class MoxOpalBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        if state.count_artifacts() < 3:
            return []
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Mox Opal",
            description="Tap Mox Opal (metalcraft) for 1 mana",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(ANY=1)),
            risk_level=RISK_SAFE,
        )]


# ── Mana: Mox Amber (legendary) ──────────────────────────────────────────────

class MoxAmberBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        if not state.legendary_permanent_available:
            return []
        # Vivi is UR legendary
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Mox Amber",
            description="Tap Mox Amber (Vivi legendary) for 1 mana",
            costs=CostBundle(tap_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(ANY=1)),
            risk_level=RISK_SAFE,
        )]


# ── Mana: Springleaf Drum ────────────────────────────────────────────────────

class SpringleafDrumBehavior(CardBehavior):
    def generate_mana_actions(self, state, perm):
        if perm.tapped:
            return []
        if not state.has_untapped_creature():
            return []
        creature = state.get_untapped_creature_perm()
        cid = creature.perm_id if creature else "vivi"
        return [Action(
            action_type=ACTIVATE_MANA_ABILITY,
            source_card="Springleaf Drum",
            description="Tap Springleaf Drum + creature for 1 mana",
            costs=CostBundle(
                tap_permanent_id=perm.perm_id,
                # Tapping Vivi is handled in resolver via flag
            ),
            effects=EffectBundle(add_mana=ManaPool(ANY=1)),
            risk_level=RISK_SAFE,
            alt_cost_type=f"tap_creature:{cid}",
        )]


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
        # Tutor any card to hand, then discard random card
        if not state.library:
            return
        # Find best target (handled by policy via tutor choice; here we pull "best")
        # For simulation: pick the most useful card not already in hand
        target = _pick_best_tutor_target(state, "any")
        if target and target in state.library:
            state.library.remove(target)
            state.hand.append(target)
            state.trace[-1].notes.append(f"Gamble tutored: {target}")
        # Discard random card from hand
        if state.hand and state.rng:
            discard = state.rng.choice(state.hand)
            state.hand.remove(discard)
            state.graveyard.append(discard)
            state.trace[-1].notes.append(f"Gamble discarded: {discard}")


# ── Spell: Mystical Tutor ─────────────────────────────────────────────────────

class MysticalTutorBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        target = _pick_best_tutor_target(state, "instant_sorcery")
        if target and target in state.library:
            state.library.remove(target)
            state.library.insert(0, target)
            state.trace[-1].notes.append(f"Mystical Tutor put {target} on top")


# ── Spell: Merchant Scroll ────────────────────────────────────────────────────

class MerchantScrollBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        from .cards import get_card
        target = _pick_best_tutor_target(state, "blue_instant")
        if target and target in state.library:
            state.library.remove(target)
            state.hand.append(target)
            state.trace[-1].notes.append(f"Merchant Scroll found: {target}")


# ── Spell: Solve the Equation ─────────────────────────────────────────────────

class SolveTheEquationBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        target = _pick_best_tutor_target(state, "instant_sorcery")
        if target and target in state.library:
            state.library.remove(target)
            state.hand.append(target)
            state.trace[-1].notes.append(f"Solve the Equation found: {target}")


# ── Spell: Intuition ──────────────────────────────────────────────────────────

class IntuitionBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        from .cards import get_card
        # Greedy: search for 3 cards, assume we get the best one
        # (opponent picks which one we get; we assume best case = best card)
        target = _pick_best_tutor_target(state, "any")
        if target and target in state.library:
            # Grab target + 2 filler cards
            state.library.remove(target)
            state.hand.append(target)
            # The other 2 go to graveyard
            for _ in range(min(2, len(state.library))):
                card = state.library.pop(0)
                state.graveyard.append(card)
            state.trace[-1].notes.append(f"Intuition (greedy) got: {target}")


# ── Spell: Gitaxian Probe ─────────────────────────────────────────────────────

class GitaxianProbeBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        # Draw 1 card on resolution (separate from Curiosity draw)
        _draw(state, 1)
        state.trace[-1].notes.append("Gitaxian Probe: drew 1")


# ── Spell: Twisted Image ──────────────────────────────────────────────────────

class TwistedImageBehavior(CardBehavior):
    def resolve_cast(self, state, stack_obj):
        _draw(state, 1)
        state.trace[-1].notes.append("Twisted Image: drew 1")


# ── Spell: Repeal ─────────────────────────────────────────────────────────────

class RepealBehavior(CardBehavior):
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
        return [Action(
            action_type=SACRIFICE_FOR_MANA,
            source_card="_Treasure",
            description="Sacrifice Treasure token for 1 mana",
            costs=CostBundle(sacrifice_permanent_id=perm.perm_id),
            effects=EffectBundle(add_mana=ManaPool(ANY=1)),
            risk_level=RISK_SAFE,
        )]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw(state: GameState, n: int) -> None:
    from .resolver import draw_cards
    draw_cards(state, n)


_TUTOR_PRIORITY_EXTRA_TURN = list(EXTRA_TURN_WIN_CARDS)

_TUTOR_PRIORITY = [
    # Extra-turn wins
    "Alchemist's Gambit", "Final Fortune", "Last Chance", "Warrior's Oath",
    # Free spells and draw engines
    "Gitaxian Probe", "Lotus Petal", "Lion's Eye Diamond", "Simian Spirit Guide",
    "Fierce Guardianship", "Pact of Negation",
    # Cheap noncreature spells
    "Rite of Flame", "Mystical Tutor", "Merchant Scroll", "Solve the Equation",
    "Gamble", "Intuition",
    # Counterspells
    "Force of Will", "Swan Song", "Flusterstorm", "Mental Misstep",
]


def _pick_best_tutor_target(state: GameState, tutor_type: str) -> str | None:
    from .cards import get_card
    in_hand = set(state.hand)

    def eligible(name: str) -> bool:
        if name in in_hand:
            return False
        cd = get_card(name)
        if cd is None:
            return False
        if tutor_type == "instant_sorcery":
            return cd.is_instant or cd.is_sorcery
        if tutor_type == "blue_instant":
            return cd.is_instant and cd.has_blue
        return cd.is_noncreature_spell or cd.can_play_as_land

    for priority_card in _TUTOR_PRIORITY:
        if priority_card in state.library and eligible(priority_card):
            return priority_card
    # Fallback: first eligible card in library
    for card in state.library:
        if eligible(card):
            return card
    return None


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
    "Repeal":              RepealBehavior(),
    "Strike It Rich":      StrikeItRichBehavior(),
    "Mishra's Bauble":     MishraBaubleBehavior(),
    "Urza's Bauble":       UrzaBaubleBehavior(),
    "Lodestone Bauble":    LodestoneBaubleBehavior(),
    "Vexing Bauble":       VexingBaubleBehavior(),
    "Tandem Lookout":      TandemLookoutBehavior(),
    "Curiosity":           CuriosityBehavior(),
    "Ophidian Eye":        OphidianEyeBehavior(),
    "_Treasure":           TreasureBehavior(),
}
