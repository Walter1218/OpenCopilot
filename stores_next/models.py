from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApplyStatus(str, Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class EventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_STAGE_CHANGED = "task.stage_changed"
    TASK_DELTA = "task.delta"
    TASK_ARTIFACT = "task.artifact"
    TASK_WARNING = "task.warning"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"


@dataclass(slots=True)
class ContextSnapshot:
    context_snapshot_id: str
    trigger: str
    source_app: str
    selection_text: str = ""
    document_title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class TaskResult:
    summary: str = ""
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    next_actions: List[Dict[str, Any]] = field(default_factory=list)
    apply_operations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    action: str
    context_snapshot_id: str
    provider: str = "hermes_local"
    session_id: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED
    progress_stage: str = "queued"
    progress_message: str = ""
    result: Optional[TaskResult] = None
    error: Optional[Dict[str, Any]] = None
    provider_run_id: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class TaskEvent:
    event_id: str
    task_id: str
    type: EventType
    sequence: int
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class ApplyPreview:
    preview_id: str
    task_id: str
    operation: Dict[str, Any]
    diff: Dict[str, Any]
    status: ApplyStatus = ApplyStatus.CREATED
    warnings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
