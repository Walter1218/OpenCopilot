from __future__ import annotations

from dataclasses import dataclass

from .floating_panel import FloatingPanel


@dataclass(slots=True)
class SmartCopilotLauncher:
    trigger: str = "double_right_click"

    def launch(self) -> str:
        return self.trigger

    def launch_panel(
        self,
        *,
        source_app: str,
        selection_text: str,
        document_title: str = "",
    ) -> FloatingPanel:
        panel = FloatingPanel()
        panel.summon(
            source_app=source_app,
            selection_text=selection_text,
            document_title=document_title,
            trigger=self.trigger,
        )
        return panel
