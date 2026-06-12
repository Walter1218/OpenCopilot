from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .unified_api_client import UnifiedApiClient


@dataclass(slots=True)
class EventStreamClient:
    base_url: str = ""
    api_client: UnifiedApiClient | None = None
    _last_sequence_by_task: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.api_client is None:
            resolved_base_url = self.base_url or os.getenv(
                "SMART_COPILOT_API_BASE_URL",
                "http://127.0.0.1:8000",
            )
            self.base_url = resolved_base_url.rstrip("/")
            self.api_client = UnifiedApiClient(base_url=self.base_url)
            return

        if not self.base_url:
            self.base_url = self.api_client.base_url
        else:
            self.base_url = self.base_url.rstrip("/")
            self.api_client.base_url = self.base_url

    def task_events_url(self, task_id: str) -> str:
        return f"{self.base_url}/vnext/tasks/{task_id}/events"

    def poll_task_events(self, task_id: str) -> List[Dict[str, Any]]:
        payload = self.api_client.list_task_events(task_id)
        last_sequence = self._last_sequence_by_task.get(task_id, 0)
        new_events = [
            event
            for event in payload.get("events", [])
            if event.get("sequence", 0) > last_sequence
        ]
        if new_events:
            self._last_sequence_by_task[task_id] = max(event.get("sequence", 0) for event in new_events)
        return new_events

    def reset_task_cursor(self, task_id: str) -> None:
        self._last_sequence_by_task.pop(task_id, None)

    def wait_until_terminal(
        self,
        task_id: str,
        *,
        max_polls: int = 10,
        interval_sec: float = 0.25,
    ) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        for _ in range(max_polls):
            events = self.poll_task_events(task_id)
            collected.extend(events)
            if any(event.get("type") in {"task.completed", "task.failed", "task.cancelled"} for event in events):
                break
            time.sleep(interval_sec)
        return collected
