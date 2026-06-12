from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..components import ApplyBarModel, ResultViewModel
from ..services import EventStreamClient, SmartCopilotUIState, UnifiedApiClient


@dataclass(slots=True)
class TaskViewModel:
    api_client: UnifiedApiClient = field(default_factory=UnifiedApiClient)
    event_stream: EventStreamClient | None = None
    ui_state: SmartCopilotUIState = field(default_factory=SmartCopilotUIState)
    result_view: ResultViewModel = field(default_factory=ResultViewModel)
    apply_bar: ApplyBarModel = field(default_factory=ApplyBarModel)
    _latest_apply_operation: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.event_stream is None:
            self.event_stream = EventStreamClient(base_url=self.api_client.base_url, api_client=self.api_client)
        else:
            self.event_stream.api_client = self.api_client
            self.event_stream.base_url = self.api_client.base_url

    def create_task(
        self,
        action: str,
        context_snapshot_id: str,
        user_input: str = "",
        *,
        provider: str = "hermes_local",
        model: str = "default",
    ) -> dict:
        self.ui_state.status = "running"
        self.ui_state.active_action = action
        self.ui_state.progress_stage = "submitting"
        self.ui_state.progress_message = "Submitting task"
        self.ui_state.latest_result_summary = ""
        self.ui_state.latest_preview_id = ""
        self.ui_state.latest_preview_diff = {}
        self.ui_state.latest_apply_operations = []
        self.ui_state.event_log.clear()
        self.result_view = ResultViewModel()
        self.apply_bar.can_preview = False
        self.apply_bar.can_commit = False
        self._latest_apply_operation = {}
        payload = {
            "action": action,
            "context_snapshot_id": context_snapshot_id,
            "user_input": user_input,
            "agent_preferences": {"provider": provider, "model": model},
        }
        response = self.api_client.create_task(payload)
        self.ui_state.latest_task_id = response.get("task_id", "")
        self.event_stream.reset_task_cursor(self.ui_state.latest_task_id)
        self.ui_state.progress_stage = "executing"
        self.ui_state.progress_message = "Task accepted by provider"
        self.ui_state.error_message = ""
        return response

    def run_task(
        self,
        *,
        action: str,
        context_snapshot_id: str,
        user_input: str = "",
        provider: str = "hermes_local",
        model: str = "default",
        max_polls: int = 10,
        interval_sec: float = 0.25,
    ) -> Dict[str, Any]:
        task = self.create_task(
            action=action,
            context_snapshot_id=context_snapshot_id,
            user_input=user_input,
            provider=provider,
            model=model,
        )
        self.poll_until_terminal(max_polls=max_polls, interval_sec=interval_sec)
        return task

    def poll_until_terminal(self, *, max_polls: int = 10, interval_sec: float = 0.25) -> List[Dict[str, Any]]:
        task_id = self._require_task_id()
        events = self.event_stream.wait_until_terminal(
            task_id,
            max_polls=max_polls,
            interval_sec=interval_sec,
        )
        self._consume_events(events)
        self.refresh_task_state()
        return events

    def poll_once(self) -> List[Dict[str, Any]]:
        task_id = self._require_task_id()
        events = self.event_stream.poll_task_events(task_id)
        if not events:
            return []
        self._consume_events(events)
        if self._has_terminal_event(events):
            self.refresh_task_state()
        return events

    def refresh_task_state(self) -> Dict[str, Any]:
        task_id = self._require_task_id()
        task_state = self.api_client.get_task(task_id)
        self.ui_state.status = task_state.get("status", self.ui_state.status)
        self.ui_state.progress_stage = task_state.get("progress_stage", "")
        self.ui_state.progress_message = task_state.get("progress_message", "")
        self.ui_state.error_message = ""
        result = task_state.get("result") or {}
        self.result_view = ResultViewModel(
            summary=result.get("summary", ""),
            artifacts=result.get("artifacts", []),
            warnings=result.get("warnings", []),
        )
        self.ui_state.latest_result_summary = self.result_view.summary
        self.ui_state.latest_apply_operations = result.get("apply_operations", [])
        self._latest_apply_operation = (
            self.ui_state.latest_apply_operations[0] if self.ui_state.latest_apply_operations else {}
        )
        self.apply_bar.can_preview = bool(self._latest_apply_operation)
        self.apply_bar.can_commit = False
        error = task_state.get("error")
        if error:
            self.ui_state.status = "failed"
            self.ui_state.error_message = error.get("message", "task failed")
        return task_state

    def create_apply_preview(self, apply_operation: Dict[str, Any]) -> Dict[str, Any]:
        task_id = self._require_task_id()
        preview = self.api_client.create_apply_preview(
            {"task_id": task_id, "apply_operation": apply_operation}
        )
        self.ui_state.latest_preview_id = preview.get("preview_id", "")
        self.ui_state.latest_preview_diff = preview.get("diff", {})
        self.apply_bar.can_commit = preview.get("safe_to_commit", False)
        return preview

    def preview_latest_apply(self) -> Dict[str, Any]:
        if not self._latest_apply_operation:
            raise ValueError("apply_operation is not available")
        return self.create_apply_preview(self._latest_apply_operation)

    def commit_apply(self, preview_id: str | None = None) -> Dict[str, Any]:
        target_preview_id = preview_id or self.ui_state.latest_preview_id
        if not target_preview_id:
            raise ValueError("preview_id is required before commit")
        result = self.api_client.commit_apply(
            {"preview_id": target_preview_id, "confirmed_by_user": True}
        )
        if result.get("status") == "succeeded":
            self.ui_state.status = "applied"
        return result

    def _consume_events(self, events: List[Dict[str, Any]]) -> None:
        self.ui_state.event_log.extend(events)
        for event in events:
            event_type = event.get("type", "")
            payload = event.get("payload", {})
            if event_type == "task.stage_changed":
                self.ui_state.progress_stage = payload.get("stage", self.ui_state.progress_stage)
                self.ui_state.progress_message = payload.get("message", self.ui_state.progress_message)
            elif event_type == "task.delta":
                self.result_view.summary += payload.get("delta", "")
            elif event_type == "task.completed":
                self.ui_state.status = "succeeded"
                self.ui_state.latest_result_summary = payload.get("summary", self.result_view.summary)
                if not self.result_view.summary:
                    self.result_view.summary = self.ui_state.latest_result_summary
                self.ui_state.progress_stage = "completed"
                self.ui_state.progress_message = "Task completed"
            elif event_type == "task.failed":
                self.ui_state.status = "failed"
                self.ui_state.error_message = payload.get("error") or payload.get("message", "task failed")
                self.ui_state.progress_stage = "failed"

    def _require_task_id(self) -> str:
        if not self.ui_state.latest_task_id:
            raise ValueError("task_id is not available")
        return self.ui_state.latest_task_id

    @staticmethod
    def _has_terminal_event(events: List[Dict[str, Any]]) -> bool:
        return any(
            event.get("type") in {"task.completed", "task.failed", "task.cancelled"}
            for event in events
        )
