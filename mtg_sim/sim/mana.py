from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ManaPool:
    U: int = 0
    R: int = 0
    C: int = 0
    ANY: int = 0  # flexible mana that can pay any pip or generic

    def total(self) -> int:
        return self.U + self.R + self.C + self.ANY

    def copy(self) -> ManaPool:
        return ManaPool(U=self.U, R=self.R, C=self.C, ANY=self.ANY)

    def add(self, other: ManaPool) -> None:
        self.U += other.U
        self.R += other.R
        self.C += other.C
        self.ANY += other.ANY

    def add_color(self, color: str, amount: int = 1) -> None:
        if color == "U":
            self.U += amount
        elif color == "R":
            self.R += amount
        elif color == "C":
            self.C += amount
        else:
            self.ANY += amount

    def __repr__(self) -> str:
        parts = []
        if self.U:
            parts.append(f"{self.U}U")
        if self.R:
            parts.append(f"{self.R}R")
        if self.C:
            parts.append(f"{self.C}C")
        if self.ANY:
            parts.append(f"{self.ANY}*")
        return "{" + ",".join(parts) + "}" if parts else "{0}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ManaPool):
            return False
        return self.U == other.U and self.R == other.R and self.C == other.C and self.ANY == other.ANY


@dataclass
class ManaCost:
    pip_u: int = 0
    pip_r: int = 0
    generic: int = 0
    x_cost: bool = False
    x_value: int = 0
    pip_ur_hybrid: int = 0  # {U/R} hybrid pips — satisfied by U, R, or ANY (not C)

    @property
    def total_mana(self) -> int:
        return self.pip_u + self.pip_r + self.generic + self.x_value + self.pip_ur_hybrid

    def is_free(self) -> bool:
        return self.total_mana == 0

    @classmethod
    def zero(cls) -> ManaCost:
        return cls()

    def __repr__(self) -> str:
        parts = []
        if self.generic:
            parts.append(str(self.generic))
        if self.x_cost:
            parts.append(f"X={self.x_value}")
        if self.pip_u:
            parts.append("U" * self.pip_u)
        if self.pip_r:
            parts.append("R" * self.pip_r)
        if self.pip_ur_hybrid:
            parts.append("{U/R}" * self.pip_ur_hybrid)
        return "{" + "".join(parts) + "}" if parts else "{0}"


def can_pay_cost(pool: ManaPool, cost: ManaCost) -> bool:
    # Pure U pips: U first, then ANY
    u_from_any = max(0, cost.pip_u - pool.U)
    if u_from_any > pool.ANY:
        return False
    remaining_any = pool.ANY - u_from_any

    # Pure R pips: R first, then remaining ANY
    r_from_any = max(0, cost.pip_r - pool.R)
    if r_from_any > remaining_any:
        return False
    remaining_any -= r_from_any

    # Hybrid {U/R} pips: surplus U, then surplus R, then remaining ANY (C cannot pay hybrid)
    surplus_u = max(0, pool.U - cost.pip_u)
    surplus_r = max(0, pool.R - cost.pip_r)
    available_for_hybrid = surplus_u + surplus_r + remaining_any
    if cost.pip_ur_hybrid > available_for_hybrid:
        return False
    remaining_after_hybrid = available_for_hybrid - cost.pip_ur_hybrid

    # Generic: whatever colored surplus remains after hybrid + C
    generic_needed = cost.generic + cost.x_value
    return remaining_after_hybrid + pool.C >= generic_needed


def pay_cost(pool: ManaPool, cost: ManaCost) -> ManaPool:
    if not can_pay_cost(pool, cost):
        raise ValueError(f"Cannot pay {cost} from {pool}")

    p = pool.copy()

    # Pay pure U pips: U first, then ANY
    u_from_u = min(cost.pip_u, p.U)
    p.U -= u_from_u
    p.ANY -= cost.pip_u - u_from_u

    # Pay pure R pips: R first, then ANY
    r_from_r = min(cost.pip_r, p.R)
    p.R -= r_from_r
    p.ANY -= cost.pip_r - r_from_r

    # Pay hybrid {U/R} pips: surplus U first, then surplus R, then ANY
    hybrid = cost.pip_ur_hybrid
    h_from_u = min(hybrid, p.U)
    p.U -= h_from_u
    hybrid -= h_from_u
    h_from_r = min(hybrid, p.R)
    p.R -= h_from_r
    hybrid -= h_from_r
    p.ANY -= hybrid

    # Pay generic: C first, then ANY, then U, then R
    generic = cost.generic + cost.x_value
    take = min(generic, p.C)
    p.C -= take
    generic -= take
    take = min(generic, p.ANY)
    p.ANY -= take
    generic -= take
    take = min(generic, p.U)
    p.U -= take
    generic -= take
    take = min(generic, p.R)
    p.R -= take
    generic -= take

    assert generic == 0
    return p


def choose_mana_color(pool: ManaPool, available_colors: str) -> str:
    """Pick the most useful color given what we have and what might be needed."""
    if "U" in available_colors and pool.U == 0:
        return "U"
    if "R" in available_colors and pool.R == 0:
        return "R"
    if "U" in available_colors:
        return "U"
    if "R" in available_colors:
        return "R"
    return "C"
