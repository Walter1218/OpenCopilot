from __future__ import annotations

from stores_next.context_store import ContextStore
from stores_next.models import ContextSnapshot


class ContextService:
    def __init__(self, context_store: ContextStore) -> None:
        self._context_store = context_store

    def create_snapshot(self, snapshot: ContextSnapshot) -> ContextSnapshot:
        return self._context_store.create(snapshot)
