from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class StackObject:
    card_name: str
    stack_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    targets: list[str] = field(default_factory=list)        # stack_ids or permanent_ids
    target_names: list[str] = field(default_factory=list)   # readable names for display
    x_value: int = 0
    alt_cost_used: Optional[str] = None
    pitched_card: Optional[str] = None
    # Curiosity draw triggers are stack objects, not a separate counter.
    is_draw_trigger: bool = False
    draw_count: int = 0

    def has_targets(self) -> bool:
        return len(self.targets) > 0

    def __repr__(self) -> str:
        if self.is_draw_trigger:
            return f"[DrawTrigger:{self.draw_count}]"
        base = self.card_name
        if self.targets:
            display = self.target_names if self.target_names else self.targets
            base += f"→{display}"
        return base
