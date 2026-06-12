from __future__ import annotations

from uuid import uuid4

from stores_next.apply_preview_store import ApplyPreviewStore
from stores_next.models import ApplyPreview
from stores_next.task_store import TaskStore


class ApplyService:
    def __init__(self, apply_store: ApplyPreviewStore, task_store: TaskStore) -> None:
        self._apply_store = apply_store
        self._task_store = task_store

    def create_preview(self, *, task_id: str, operation: dict) -> ApplyPreview:
        task = self._task_store.get(task_id)
        if task is None:
            raise KeyError(f"Unknown task_id: {task_id}")
        preview = ApplyPreview(
            preview_id=f"ap_{uuid4().hex[:12]}",
            task_id=task_id,
            operation=operation,
            diff={"before": "original selection", "after": "updated selection"},
        )
        return self._apply_store.create(preview)

    def commit_preview(self, preview_id: str) -> str:
        self._apply_store.mark_confirmed(preview_id)
        return "succeeded"
