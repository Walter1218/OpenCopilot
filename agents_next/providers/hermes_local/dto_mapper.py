from __future__ import annotations

from platform_next.gateway.agent_gateway.protocol import UnifiedTaskRequest


class HermesDtoMapper:
    def build_input_text(self, request: UnifiedTaskRequest) -> str:
        context = request.context_payload or {}
        selection_text = context.get("selection_text", "").strip()
        source_app = context.get("source_app", "unknown")
        document_title = context.get("document_title", "").strip()

        sections = [
            f"Action: {request.action}",
            f"Source App: {source_app}",
        ]
        if document_title:
            sections.append(f"Document Title: {document_title}")
        if selection_text:
            sections.append("Selected Content:")
            sections.append(selection_text)
        if request.user_input.strip():
            sections.append("User Instruction:")
            sections.append(request.user_input.strip())
        return "\n".join(sections)

    def to_run_request(self, request: UnifiedTaskRequest) -> dict:
        model = (request.model or "default").strip() or "default"
        return {
            "input": self.build_input_text(request),
            "model": model,
            "session_id": request.task_id,
            "metadata": {
                "task_id": request.task_id,
                "context_snapshot_id": request.context_snapshot_id,
                "action": request.action,
                "model": model,
                "source_app": request.context_payload.get("source_app", ""),
            },
        }
