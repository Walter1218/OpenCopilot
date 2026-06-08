from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApplyBarModel:
    can_preview: bool = False
    can_commit: bool = False
