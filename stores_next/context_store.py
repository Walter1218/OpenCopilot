from __future__ import annotations

from typing import Dict, Optional

from .models import ContextSnapshot


class ContextStore:
    def __init__(self) -> None:
        self._snapshots: Dict[str, ContextSnapshot] = {}

    def create(self, snapshot: ContextSnapshot) -> ContextSnapshot:
        self._snapshots[snapshot.context_snapshot_id] = snapshot
        return snapshot

    def get(self, context_snapshot_id: str) -> Optional[ContextSnapshot]:
        return self._snapshots.get(context_snapshot_id)
