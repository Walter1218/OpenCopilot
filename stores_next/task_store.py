from __future__ import annotations

from dataclasses import replace
import threading
from typing import Dict, Optional

from .models import TaskRecord, TaskResult, TaskStatus, utc_now_iso


class TaskStore:
    def __init__(self) -> None:
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = threading.RLock()

    def create(self, task: TaskRecord) -> TaskRecord:
        with self._lock:
            self._tasks[task.task_id] = task
            return task

    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        stage: str = "",
        message: str = "",
    ) -> TaskRecord:
        with self._lock:
            task = self._require(task_id)
            updated = replace(
                task,
                status=status,
                progress_stage=stage or task.progress_stage,
                progress_message=message,
                updated_at=utc_now_iso(),
            )
            self._tasks[task_id] = updated
            return updated

    def set_provider_run_id(self, task_id: str, provider_run_id: str) -> TaskRecord:
        with self._lock:
            task = self._require(task_id)
            updated = replace(task, provider_run_id=provider_run_id, updated_at=utc_now_iso())
            self._tasks[task_id] = updated
            return updated

    def set_result(self, task_id: str, result: TaskResult) -> TaskRecord:
        with self._lock:
            task = self._require(task_id)
            updated = replace(
                task,
                result=result,
                status=TaskStatus.SUCCEEDED,
                progress_stage="completed",
                progress_message="Task completed",
                updated_at=utc_now_iso(),
            )
            self._tasks[task_id] = updated
            return updated

    def set_error(self, task_id: str, error: Dict[str, str]) -> TaskRecord:
        with self._lock:
            task = self._require(task_id)
            updated = replace(
                task,
                error=error,
                status=TaskStatus.FAILED,
                progress_stage="failed",
                progress_message=error.get("message", "task failed"),
                updated_at=utc_now_iso(),
            )
            self._tasks[task_id] = updated
            return updated

    def _require(self, task_id: str) -> TaskRecord:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Unknown task_id: {task_id}")
        return task
