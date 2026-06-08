from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from ..components import ContextCardModel
from ..services import SmartCopilotUIState, UnifiedApiClient


@dataclass(slots=True)
class SummonViewModel:
    api_client: UnifiedApiClient = field(default_factory=UnifiedApiClient)
    ui_state: SmartCopilotUIState = field(default_factory=SmartCopilotUIState)
    context_card: ContextCardModel = field(default_factory=ContextCardModel)

    def collect_context(
        self,
        source_app: str,
        selection_text: str,
        *,
        document_title: str = "",
        metadata: Dict[str, Any] | None = None,
        trigger: str = "double_right_click",
    ) -> dict:
        self.ui_state.status = "collecting"
        payload = {
            "trigger": trigger,
            "source_app": source_app,
            "selection_text": selection_text,
            "document_title": document_title,
            "metadata": metadata or {},
        }
        response = self.api_client.create_context_snapshot(payload)
        summary = response.get("summary", {})
        self.ui_state.latest_context_id = response.get("context_snapshot_id", "")
        self.ui_state.status = "ready"
        self.ui_state.error_message = ""
        self.context_card = ContextCardModel(
            source_app=summary.get("source_app", source_app),
            document_title=summary.get("document_title", document_title),
            selection_chars=summary.get("selection_chars", len(selection_text)),
        )
        return response
