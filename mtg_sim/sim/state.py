from __future__ import annotations
from dataclasses import dataclass, field
from random import Random
from typing import Optional
from .mana import ManaPool
import uuid


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
    trace: list = field(default_factory=list)         # list[ActionLog]
    rng: Optional[Random] = None

    # For Jeska's Will exile-cast permissions
    jeska_opponent_hand_size: int = 7

    def update_curiosity_draw(self) -> None:
        self.cards_drawn_per_noncreature_spell = 3 * self.curiosity_effect_count

    def get_permanents_by_name(self, name: str) -> list:
        return [p for p in self.battlefield if p.card_name == name]

    def get_perm_by_id(self, perm_id: str) -> Optional[Permanent]:
        for p in self.battlefield:
            if p.perm_id == perm_id:
                return p
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
