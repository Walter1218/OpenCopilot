from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from ..components import ApplyBarModel, ContextCardModel, ResultViewModel
from ..services import EventStreamClient, SmartCopilotUIState, UnifiedApiClient
from ..viewmodels import SummonViewModel, TaskViewModel


@dataclass(slots=True)
class FloatingPanel:
    title: str = "Smart Copilot"
    visible: bool = False
    api_client: UnifiedApiClient = field(default_factory=UnifiedApiClient)
    ui_state: SmartCopilotUIState = field(default_factory=SmartCopilotUIState)
    summon_vm: SummonViewModel | None = None
    task_vm: TaskViewModel | None = None

    def __post_init__(self) -> None:
        if self.summon_vm is None:
            self.summon_vm = SummonViewModel(api_client=self.api_client, ui_state=self.ui_state)
        else:
            self.summon_vm.api_client = self.api_client
            self.summon_vm.ui_state = self.ui_state

        if self.task_vm is None:
            event_stream = EventStreamClient(base_url=self.api_client.base_url, api_client=self.api_client)
            self.task_vm = TaskViewModel(
                api_client=self.api_client,
                event_stream=event_stream,
                ui_state=self.ui_state,
            )
        else:
            self.task_vm.api_client = self.api_client
            self.task_vm.ui_state = self.ui_state

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def close(self) -> None:
        self.hide()
        self.api_client.close()

    def summon(
        self,
        *,
        source_app: str,
        selection_text: str,
        document_title: str = "",
        metadata: Dict[str, Any] | None = None,
        trigger: str = "double_right_click",
    ) -> Dict[str, Any]:
        self.show()
        return self.summon_vm.collect_context(
            source_app=source_app,
            selection_text=selection_text,
            document_title=document_title,
            metadata=metadata,
            trigger=trigger,
        )

    def run_action(
        self,
        *,
        action: str,
        user_input: str = "",
        provider: str = "hermes_local",
        max_polls: int = 10,
        interval_sec: float = 0.25,
    ) -> Dict[str, Any]:
        return self.task_vm.run_task(
            action=action,
            context_snapshot_id=self.ui_state.latest_context_id,
            user_input=user_input,
            provider=provider,
            max_polls=max_polls,
            interval_sec=interval_sec,
        )

    def preview_latest_apply(self) -> Dict[str, Any]:
        return self.task_vm.preview_latest_apply()

    def commit_latest_preview(self) -> Dict[str, Any]:
        return self.task_vm.commit_apply()

    def snapshot(self) -> Dict[str, Any]:
        context_card = self.summon_vm.context_card if self.summon_vm is not None else ContextCardModel()
        result_view = self.task_vm.result_view if self.task_vm is not None else ResultViewModel()
        apply_bar = self.task_vm.apply_bar if self.task_vm is not None else ApplyBarModel()
        return {
            "visible": self.visible,
            "title": self.title,
            "ui_state": {
                "status": self.ui_state.status,
                "latest_task_id": self.ui_state.latest_task_id,
                "latest_context_id": self.ui_state.latest_context_id,
                "active_action": self.ui_state.active_action,
                "progress_stage": self.ui_state.progress_stage,
                "progress_message": self.ui_state.progress_message,
                "latest_result_summary": self.ui_state.latest_result_summary,
                "latest_preview_id": self.ui_state.latest_preview_id,
                "error_message": self.ui_state.error_message,
                "latest_preview_diff": self.ui_state.latest_preview_diff,
                "latest_apply_operations": self.ui_state.latest_apply_operations,
                "event_log": self.ui_state.event_log,
            },
            "context_card": {
                "source_app": context_card.source_app,
                "document_title": context_card.document_title,
                "selection_chars": context_card.selection_chars,
            },
            "result_view": {
                "summary": result_view.summary,
                "artifacts": result_view.artifacts,
                "warnings": result_view.warnings,
            },
            "apply_bar": {
                "can_preview": apply_bar.can_preview,
                "can_commit": apply_bar.can_commit,
            },
        }
