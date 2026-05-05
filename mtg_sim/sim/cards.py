from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import csv
import warnings

DEFAULT_ACTIVE_DECK_IDS = list(range(2, 101))

VIVI_CARD_ID = 1


@dataclass(frozen=True)
class CardData:
    card_id: int
    name: str
    mana_cost: str
    mv: int
    colors: str
    pip_u: int
    pip_r: int
    generic_mana: int
    pip_ur_hybrid: int
    x_in_cost: bool
    card_types: str
    is_noncreature_spell: bool
    can_play_as_land: bool
    land_enters_tapped: str      # "true", "false", "conditional"
    land_mana_mode: str          # "fixed", "fetch", "choice", "conditional", "limited", "none"
    land_limited_uses: int
    alt_costs: str
    produces_mana: bool
    mana_source_type: str
    mana_colors: str
    mana_amount: str
    mana_timing: str
    mana_condition: str
    requires_tap: bool
    requires_sacrifice: bool
    requires_discard: bool
    requires_exile: bool
    requires_creature: bool
    has_flash: bool

    @property
    def is_land(self) -> bool:
        return "Land" in self.card_types

    @property
    def is_creature(self) -> bool:
        return "Creature" in self.card_types

    @property
    def is_instant(self) -> bool:
        return "Instant" in self.card_types

    @property
    def is_sorcery(self) -> bool:
        return "Sorcery" in self.card_types

    @property
    def is_artifact(self) -> bool:
        return "Artifact" in self.card_types

    @property
    def is_enchantment(self) -> bool:
        return "Enchantment" in self.card_types

    @property
    def is_mdfc(self) -> bool:
        return "/" in self.name

    @property
    def has_blue(self) -> bool:
        return "U" in self.colors

    @property
    def has_red(self) -> bool:
        return "R" in self.colors

    @property
    def base_name(self) -> str:
        """For MDFCs, return the front face name."""
        return self.name.split(" / ")[0] if "/" in self.name else self.name


# Keyed by name for fast lookup during simulation; also accessible by card_id.
_CARD_LIBRARY_BY_NAME: dict[str, CardData] = {}
_CARD_LIBRARY_BY_ID: dict[int, CardData] = {}


def _parse_bool(s: str) -> bool:
    return s.strip().lower() == "true"


def _parse_int(s: str, default: int = 0) -> int:
    try:
        return int(s.strip())
    except (ValueError, AttributeError):
        return default


def load_card_library(csv_path: str) -> dict[str, CardData]:
    global _CARD_LIBRARY_BY_NAME, _CARD_LIBRARY_BY_ID
    _CARD_LIBRARY_BY_NAME = {}
    _CARD_LIBRARY_BY_ID = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            card = CardData(
                card_id=_parse_int(row["card_id"]),
                name=row["name"].strip(),
                mana_cost=row["mana_cost"].strip(),
                mv=_parse_int(row["mv"]),
                colors=row["colors"].strip(),
                pip_u=_parse_int(row["pip_u"]),
                pip_r=_parse_int(row["pip_r"]),
                generic_mana=_parse_int(row["generic_mana"]),
                pip_ur_hybrid=_parse_int(row.get("pip_ur_hybrid", "0")),
                x_in_cost=_parse_bool(row["x_in_cost"]),
                card_types=row["card_types"].strip(),
                is_noncreature_spell=_parse_bool(row["is_noncreature_spell"]),
                can_play_as_land=_parse_bool(row["can_play_as_land"]),
                land_enters_tapped=row["land_enters_tapped"].strip(),
                land_mana_mode=row["land_mana_mode"].strip(),
                land_limited_uses=_parse_int(row["land_limited_uses"]),
                alt_costs=row["alt_costs"].strip(),
                produces_mana=_parse_bool(row["produces_mana"]),
                mana_source_type=row["mana_source_type"].strip(),
                mana_colors=row["mana_colors"].strip(),
                mana_amount=row["mana_amount"].strip(),
                mana_timing=row["mana_timing"].strip(),
                mana_condition=row["mana_condition"].strip(),
                requires_tap=_parse_bool(row["requires_tap"]),
                requires_sacrifice=_parse_bool(row["requires_sacrifice"]),
                requires_discard=_parse_bool(row["requires_discard"]),
                requires_exile=_parse_bool(row["requires_exile"]),
                requires_creature=_parse_bool(row["requires_creature"]),
                has_flash=_parse_bool(row.get("has_flash", "false")),
            )
            _CARD_LIBRARY_BY_NAME[card.name] = card
            _CARD_LIBRARY_BY_ID[card.card_id] = card
    return _CARD_LIBRARY_BY_NAME


def build_active_deck(card_ids: list[int] | None = None) -> list[str]:
    """Return card names for the given IDs (default: IDs 2-100).

    Errors if any ID is missing from the card library.
    Warns if any card has no behavior registered in card_behaviors.
    """
    from .card_behaviors import CARD_BEHAVIORS

    if card_ids is None:
        card_ids = DEFAULT_ACTIVE_DECK_IDS

    names: list[str] = []
    for cid in card_ids:
        if cid not in _CARD_LIBRARY_BY_ID:
            raise ValueError(f"Card ID {cid} not found in card library")
        names.append(_CARD_LIBRARY_BY_ID[cid].name)

    missing_behavior = [n for n in names if n not in CARD_BEHAVIORS]
    if missing_behavior:
        warnings.warn(
            f"Active deck contains cards with no registered behavior "
            f"(will use generic rules only): {missing_behavior}",
            stacklevel=2,
        )

    return names


def get_card(name: str) -> Optional[CardData]:
    return _CARD_LIBRARY_BY_NAME.get(name)


def get_all_cards() -> dict[str, CardData]:
    return _CARD_LIBRARY_BY_NAME
