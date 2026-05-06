from __future__ import annotations
from dataclasses import dataclass, field
from random import Random
from typing import Optional
from .mana import ManaPool
import uuid

# Number of opponents in the game.  Each Curiosity-like effect triggers once per
# opponent that Vivi damages, so draw_count = curiosity_effect_count * OPPONENT_COUNT.
OPPONENT_COUNT = 3


@dataclass
class Permanent:
    card_name: str
    tapped: bool = False
    counters: dict = field(default_factory=dict)
    imprinted_card: Optional[str] = None
    attached_to: Optional[str] = None
    perm_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    depletion_counters: int = 0

    def __repr__(self) -> str:
        t = " [T]" if self.tapped else ""
        imp = f" imp:{self.imprinted_card}" if self.imprinted_card else ""
        return f"{self.card_name}{t}{imp}"


@dataclass
class Permission:
    card_name: str
    zone: str                   # "exile", "graveyard"
    action_type: str
    expires: str                # "end_of_turn", "immediate"
    cost_modifier: Optional[dict] = None


@dataclass
class PendingChoice:
    """A player decision that must be resolved before the game can continue."""
    choice_type: str              # "imprint" | "discard" | "tutor"
    perm_id: str = ""             # for imprint/discard: perm needing the choice
    tutor_filter: str = "any"     # for tutor: "any" | "instant_sorcery" | "blue_instant" | "mv=1" | "mv=3" | "creature_power_lte2"
    tutor_destination: str = "hand"  # for tutor: "hand" | "top"
    source_card: str = ""         # which spell/card created this choice (for display)
    post_effect: str = ""         # optional follow-up: "gamble_discard"
    preferred_targets: list = None  # ordering hint; preferred cards appear first in action list


@dataclass
class ActionLog:
    step: int
    event_type: str
    action_description: str
    cards_drawn: list = field(default_factory=list)
    mana_before: Optional[ManaPool] = None
    mana_after: Optional[ManaPool] = None
    hand_size_before: int = 0
    hand_size_after: int = 0
    noncreature_spells_cast: int = 0
    stack_snapshot: list = field(default_factory=list)
    notes: list = field(default_factory=list)


@dataclass
class GameState:
    hand: list = field(default_factory=list)        # card names
    library: list = field(default_factory=list)     # card names, top at index 0
    graveyard: list = field(default_factory=list)
    exile: list = field(default_factory=list)
    battlefield: list = field(default_factory=list)  # list[Permanent]
    stack: list = field(default_factory=list)        # list[StackObject]

    floating_mana: ManaPool = field(default_factory=ManaPool)

    curiosity_effect_count: int = 1
    cards_drawn_per_noncreature_spell: int = 3

    noncreature_spells_cast: int = 0
    total_spells_cast: int = 0
    total_cards_drawn: int = 0

    land_play_available: bool = True

    vivi_on_battlefield: bool = True
    vivi_available_as_creature_to_tap: bool = True
    legendary_permanent_available: bool = True

    permissions: list = field(default_factory=list)   # list[Permission]
    pending_choices: list = field(default_factory=list)  # list[PendingChoice]
    trace: list = field(default_factory=list)         # list[ActionLog]
    rng: Optional[Random] = None

    # For Jeska's Will exile-cast permissions
    jeska_opponent_hand_size: int = 7
    virtue_of_courage_on_battlefield: bool = False

    # Assumption: does opponent control an island? (affects Mogg Salvage free cost)
    opponent_controls_island: bool = True

    # Stable dummy permanents representing opponent creatures/artifacts/lands for targeting.
    # These are never on state.battlefield; they exist only as valid target placeholders.
    _opponent_creature_perm: Optional["Permanent"] = field(default=None, repr=False)
    _opponent_artifact_perm: Optional["Permanent"] = field(default=None, repr=False)
    _opponent_land_perm: Optional["Permanent"] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._opponent_creature_perm is None:
            self._opponent_creature_perm = Permanent(card_name="_opponent_creature")
        if self._opponent_artifact_perm is None:
            self._opponent_artifact_perm = Permanent(card_name="_opponent_artifact")
        if self._opponent_land_perm is None:
            self._opponent_land_perm = Permanent(card_name="_opponent_land")

    @property
    def pending_curiosity_draws(self) -> int:
        """Total draws buffered in draw-trigger stack objects above unresolved spells."""
        return sum(obj.draw_count for obj in self.stack if obj.is_draw_trigger)

    def update_curiosity_draw(self) -> None:
        self.cards_drawn_per_noncreature_spell = OPPONENT_COUNT * self.curiosity_effect_count

    def get_permanents_by_name(self, name: str) -> list:
        return [p for p in self.battlefield if p.card_name == name]

    def get_perm_by_id(self, perm_id: str) -> Optional[Permanent]:
        for p in self.battlefield:
            if p.perm_id == perm_id:
                return p
        if self._opponent_creature_perm and self._opponent_creature_perm.perm_id == perm_id:
            return self._opponent_creature_perm
        if self._opponent_artifact_perm and self._opponent_artifact_perm.perm_id == perm_id:
            return self._opponent_artifact_perm
        if self._opponent_land_perm and self._opponent_land_perm.perm_id == perm_id:
            return self._opponent_land_perm
        return None

    def remove_perm_by_id(self, perm_id: str) -> Optional[Permanent]:
        for i, p in enumerate(self.battlefield):
            if p.perm_id == perm_id:
                return self.battlefield.pop(i)
        return None

    def get_stack_object(self, stack_id: str):
        for obj in self.stack:
            if obj.stack_id == stack_id:
                return obj
        return None

    def remove_stack_object(self, stack_id: str):
        for i, obj in enumerate(self.stack):
            if obj.stack_id == stack_id:
                return self.stack.pop(i)
        return None

    def count_artifacts(self) -> int:
        from .cards import get_card
        return sum(1 for p in self.battlefield if (cd := get_card(p.card_name)) and cd.is_artifact)

    def has_untapped_creature(self) -> bool:
        from .cards import get_card
        for p in self.battlefield:
            if not p.tapped:
                cd = get_card(p.card_name)
                if cd and cd.is_creature:
                    return True
        return self.vivi_available_as_creature_to_tap

    def get_untapped_creature_perm(self) -> Optional[Permanent]:
        from .cards import get_card
        for p in self.battlefield:
            if not p.tapped:
                cd = get_card(p.card_name)
                if cd and cd.is_creature:
                    return p
        return None

    def count_rites_in_graveyard(self) -> int:
        return self.graveyard.count("Rite of Flame")

    def lands_in_hand(self) -> list:
        from .cards import get_card
        return [c for c in self.hand if (cd := get_card(c)) and cd.is_land]

    def has_land_on_battlefield(self) -> bool:
        from .cards import get_card
        return any((cd := get_card(p.card_name)) and cd.is_land for p in self.battlefield)


def validate_state(state: GameState) -> None:
    """Assert no non-basic, non-token card appears in more than one zone simultaneously."""
    from collections import Counter
    from .cards import get_card

    all_names: list[str] = (
        state.hand
        + state.library
        + state.graveyard
        + state.exile
        + [p.card_name for p in state.battlefield]
        + [obj.card_name for obj in state.stack]
    )

    counts = Counter(all_names)
    for name, count in counts.items():
        if count <= 1:
            continue
        if name.startswith("_"):
            continue  # tokens (_Treasure) may duplicate
        cd = get_card(name)
        if cd and "Basic" in cd.card_types:
            continue  # basic lands may have multiple copies in deck
        raise AssertionError(
            f"Zone consistency violation: '{name}' appears {count}x "
            f"(hand={state.hand.count(name)}, "
            f"library={state.library.count(name)}, "
            f"graveyard={state.graveyard.count(name)}, "
            f"exile={state.exile.count(name)}, "
            f"battlefield={sum(1 for p in state.battlefield if p.card_name == name)}, "
            f"stack={sum(1 for o in state.stack if o.card_name == name)})"
        )
