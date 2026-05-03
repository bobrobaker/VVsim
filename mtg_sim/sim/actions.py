from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .mana import ManaCost, ManaPool

# ── Action type constants ────────────────────────────────────────────────────
INITIAL_CURIOSITY_DRAW = "INITIAL_CURIOSITY_DRAW"
CAST_SPELL             = "CAST_SPELL"
RESOLVE_STACK_OBJECT   = "RESOLVE_STACK_OBJECT"
PLAY_LAND              = "PLAY_LAND"
ACTIVATE_MANA_ABILITY  = "ACTIVATE_MANA_ABILITY"
EXILE_FOR_MANA         = "EXILE_FOR_MANA"
SACRIFICE_FOR_MANA     = "SACRIFICE_FOR_MANA"
STOP                   = "STOP"

# ── Terminal outcomes ────────────────────────────────────────────────────────
WIN_EXTRA_TURN              = "WIN_EXTRA_TURN"
WIN_NONCREATURE_SPELL_COUNT = "WIN_NONCREATURE_SPELL_COUNT"
BRICK_NO_ACTIONS            = "BRICK_NO_ACTIONS"
BRICK_NO_USEFUL_ACTIONS     = "BRICK_NO_USEFUL_ACTIONS"
ERROR_INVALID_STATE         = "ERROR_INVALID_STATE"

NONCREATURE_SPELL_WIN_THRESHOLD = 40

EXTRA_TURN_WIN_CARDS = frozenset({
    "Alchemist's Gambit",
    "Final Fortune",
    "Last Chance",
    "Warrior's Oath",
})

# ── Risk levels ──────────────────────────────────────────────────────────────
RISK_SAFE      = "safe"
RISK_NORMAL    = "normal"
RISK_EXPENSIVE = "expensive"
RISK_RISKY     = "risky"
RISK_DESPERATE = "desperate"

RISK_ORDER = [RISK_SAFE, RISK_NORMAL, RISK_EXPENSIVE, RISK_RISKY, RISK_DESPERATE]


@dataclass
class CostBundle:
    mana: ManaCost = field(default_factory=ManaCost.zero)
    tap_permanent_id: Optional[str] = None
    sacrifice_permanent_id: Optional[str] = None
    exile_from_hand: Optional[str] = None      # specific card name exiled as pitch cost
    pitch_blue_count: int = 0
    pitch_red_count: int = 0
    pitched_card: Optional[str] = None         # which card was chosen to pitch
    return_land_to_hand: bool = False
    pay_life: int = 0                          # ignored in sim
    discard_land: bool = False                 # for Mox Diamond ETB


@dataclass
class EffectBundle:
    add_mana: ManaPool = field(default_factory=ManaPool)
    draw_cards: int = 0
    tutor_type: Optional[str] = None
    tutor_destination: str = "hand"            # "hand" or "top"
    increase_curiosity_count: int = 0
    create_treasure: int = 0
    bounce_permanent_id: Optional[str] = None
    is_win: bool = False
    counter_target_id: Optional[str] = None   # stack_id to counter


@dataclass
class Action:
    action_type: str
    source_card: Optional[str]
    description: str
    costs: CostBundle = field(default_factory=CostBundle)
    effects: EffectBundle = field(default_factory=EffectBundle)
    requires_target: bool = False
    target: Optional[str] = None              # stack_id or permanent_id
    risk_level: str = RISK_NORMAL
    x_value: int = 0
    alt_cost_type: Optional[str] = None
    imprint_card: Optional[str] = None

    def __repr__(self) -> str:
        return f"[{self.action_type}] {self.description}"
