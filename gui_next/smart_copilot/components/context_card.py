from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContextCardModel:
    source_app: str = ""
    document_title: str = ""
    selection_chars: int = 0
