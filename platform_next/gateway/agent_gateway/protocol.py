from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from stores_next.models import EventType


@dataclass(slots=True)
class UnifiedTaskRequest:
    task_id: str
    action: str
    user_input: str
    context_snapshot_id: str
    provider: str = "hermes_local"
    context_payload: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderEvent:
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)


class AgentProvider(Protocol):
    provider_id: str

    def healthcheck(self) -> bool: ...

    def create_run(self, request: UnifiedTaskRequest) -> str: ...

    def poll_events(self, run_id: str) -> List[ProviderEvent]: ...

    def get_result(self, run_id: str) -> Dict[str, Any]: ...
