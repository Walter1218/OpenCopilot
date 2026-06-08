from __future__ import annotations

from collections import defaultdict
import threading
from typing import DefaultDict, List

from .models import TaskEvent


class EventStore:
    def __init__(self) -> None:
        self._events: DefaultDict[str, List[TaskEvent]] = defaultdict(list)
        self._lock = threading.RLock()

    def append(self, event: TaskEvent) -> TaskEvent:
        with self._lock:
            self._events[event.task_id].append(event)
            return event

    def list_for_task(self, task_id: str) -> list[TaskEvent]:
        with self._lock:
            return list(self._events.get(task_id, []))

    def next_sequence(self, task_id: str) -> int:
        with self._lock:
            return len(self._events.get(task_id, [])) + 1

    def last_for_task(self, task_id: str) -> TaskEvent | None:
        with self._lock:
            events = self._events.get(task_id, [])
            return events[-1] if events else None
