from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class SmartCopilotUIState:
    status: str = "idle"
    latest_task_id: str = ""
    latest_context_id: str = ""
    active_action: str = ""
    progress_stage: str = ""
    progress_message: str = ""
    latest_result_summary: str = ""
    latest_preview_id: str = ""
    error_message: str = ""
    latest_preview_diff: Dict[str, Any] = field(default_factory=dict)
    latest_apply_operations: List[Dict[str, Any]] = field(default_factory=list)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
