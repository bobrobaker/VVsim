from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class StackObject:
    card_name: str
    stack_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    targets: list[str] = field(default_factory=list)   # stack_ids or permanent_ids
    x_value: int = 0
    alt_cost_used: Optional[str] = None
    pitched_card: Optional[str] = None

    def has_targets(self) -> bool:
        return len(self.targets) > 0

    def __repr__(self) -> str:
        base = self.card_name
        if self.targets:
            base += f"→{self.targets}"
        return base
