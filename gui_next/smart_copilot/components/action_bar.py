from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ActionBarModel:
    actions: list[str] = field(default_factory=lambda: ["review", "explain", "polish"])
