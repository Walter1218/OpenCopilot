from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentPreferences(BaseModel):
    provider: str = "auto"
    model: str = "default"
    temperature: float = 0.2


class TaskConstraints(BaseModel):
    safe_apply_only: bool = True
    max_latency_ms: int = 12000
    require_evidence: bool = True


class CreateContextSnapshotRequest(BaseModel):
    trigger: str = "double_right_click"
    source_app: str
    selection_text: str = ""
    document_title: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateTaskRequest(BaseModel):
    action: str
    user_input: str = ""
    context_snapshot_id: str
    agent_preferences: AgentPreferences = Field(default_factory=AgentPreferences)
    constraints: TaskConstraints = Field(default_factory=TaskConstraints)


class ApplyPreviewRequest(BaseModel):
    task_id: str
    apply_operation: Dict[str, Any]


class ApplyCommitRequest(BaseModel):
    preview_id: str
    confirmed_by_user: bool = True


class TaskResultResponse(BaseModel):
    summary: str = ""
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    next_actions: List[Dict[str, Any]] = Field(default_factory=list)
    apply_operations: List[Dict[str, Any]] = Field(default_factory=list)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    action: str
    provider: str
    progress_stage: str
    progress_message: str
    provider_run_id: Optional[str] = None
    result: Optional[TaskResultResponse] = None
    error: Optional[Dict[str, Any]] = None
