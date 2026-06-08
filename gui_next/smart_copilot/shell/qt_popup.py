from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..runtime import SmartCopilotApiRuntime
from ..services import UnifiedApiClient
from .floating_panel import FloatingPanel


class SmartCopilotPopupVNext(QWidget):
    def __init__(self, api_runtime: SmartCopilotApiRuntime | None = None) -> None:
        super().__init__()
        self._api_runtime = api_runtime or SmartCopilotApiRuntime()
        self._panel: FloatingPanel | None = None
        self._selection_text = ""
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(350)
        self._poll_timer.timeout.connect(self._poll_task_events)
        self._build_ui()

    def cleanup(self) -> None:
        self._poll_timer.stop()
        if self._panel is not None:
            self._panel.close()
        self._api_runtime.shutdown()

    def set_selected_text(self, text: str) -> None:
        self._selection_text = text
        self.selection_view.setPlainText(text)
        self._ensure_context_snapshot()
        self._render_state()

    def jump_to_chat(self, context_text: str = "", source: str = "") -> None:
        _ = source
        self.action_selector.setCurrentText("chat")
        if context_text.strip():
            self.instruction_input.setPlainText(context_text)
        self.show()
        self.raise_()
        self.activateWindow()
        self.instruction_input.setFocus()

    def inject_chat_message(self, message: str) -> None:
        current = self.instruction_input.toPlainText().strip()
        self.instruction_input.setPlainText(f"{current}\n\n{message}".strip())

    def switch_to_chat(self) -> None:
        self.action_selector.setCurrentText("chat")
        self.instruction_input.setFocus()

    def closeEvent(self, event: Any) -> None:  # type: ignore[override]
        self._poll_timer.stop()
        self.hide()
        event.ignore()

    def _build_ui(self) -> None:
        self.setWindowTitle("Smart Copilot")
        self.resize(760, 620)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel("Smart Copilot")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        form = QFormLayout()
        self.status_label = QLabel("idle")
        self.action_selector = QComboBox()
        self.action_selector.addItems(["chat", "review", "explain", "polish"])
        form.addRow("Status", self.status_label)
        form.addRow("Action", self.action_selector)
        root.addLayout(form)

        self.selection_view = QPlainTextEdit()
        self.selection_view.setReadOnly(True)
        self.selection_view.setPlaceholderText("Selection text from double right click")
        self.selection_view.setMinimumHeight(140)
        root.addWidget(QLabel("Selection"))
        root.addWidget(self.selection_view)

        self.instruction_input = QTextEdit()
        self.instruction_input.setPlaceholderText("Optional instruction for Hermes")
        self.instruction_input.setMinimumHeight(100)
        root.addWidget(QLabel("Instruction"))
        root.addWidget(self.instruction_input)

        button_row = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.preview_button = QPushButton("Preview")
        self.commit_button = QPushButton("Commit")
        self.close_button = QPushButton("Close")
        self.run_button.clicked.connect(self._on_run_clicked)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        self.commit_button.clicked.connect(self._on_commit_clicked)
        self.close_button.clicked.connect(self.hide)
        button_row.addWidget(self.run_button)
        button_row.addWidget(self.preview_button)
        button_row.addWidget(self.commit_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)
        root.addLayout(button_row)

        self.result_view = QPlainTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setPlaceholderText("Hermes result")
        self.result_view.setMinimumHeight(180)
        root.addWidget(QLabel("Result"))
        root.addWidget(self.result_view)

        self.diff_view = QPlainTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setPlaceholderText("Apply preview diff")
        self.diff_view.setMinimumHeight(120)
        root.addWidget(QLabel("Apply Preview"))
        root.addWidget(self.diff_view)

    def _ensure_panel(self) -> FloatingPanel:
        if self._panel is not None:
            return self._panel
        base_url = self._api_runtime.ensure_ready()
        self._panel = FloatingPanel(api_client=UnifiedApiClient(base_url=base_url))
        return self._panel

    def _ensure_context_snapshot(self) -> None:
        panel = self._ensure_panel()
        current_selection = self.selection_view.toPlainText()
        panel.summon(
            source_app="System Selection",
            selection_text=current_selection,
            document_title="",
            metadata={"entry": "system_double_right_click"},
        )

    def _on_run_clicked(self) -> None:
        try:
            self._ensure_context_snapshot()
            panel = self._ensure_panel()
            panel.task_vm.create_task(
                action=self.action_selector.currentText(),
                context_snapshot_id=panel.ui_state.latest_context_id,
                user_input=self.instruction_input.toPlainText().strip(),
                provider="hermes_local",
            )
            self._render_state()
            self._poll_timer.start()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Run Failed", exc)

    def _on_preview_clicked(self) -> None:
        try:
            preview = self._ensure_panel().preview_latest_apply()
            self.diff_view.setPlainText(str(preview.get("diff", {})))
            self._render_state()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Preview Failed", exc)

    def _on_commit_clicked(self) -> None:
        try:
            self._ensure_panel().commit_latest_preview()
            self._render_state()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Commit Failed", exc)

    def _poll_task_events(self) -> None:
        try:
            panel = self._ensure_panel()
            panel.task_vm.poll_once()
            self._render_state()
            if panel.ui_state.status in {"succeeded", "failed", "cancelled", "applied"}:
                self._poll_timer.stop()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._poll_timer.stop()
            self._show_error("Polling Failed", exc)

    def _render_state(self) -> None:
        if self._panel is None:
            self.status_label.setText("idle")
            self.preview_button.setEnabled(False)
            self.commit_button.setEnabled(False)
            return
        snapshot = self._panel.snapshot()
        ui_state = snapshot["ui_state"]
        status_parts = [
            ui_state["status"] or "idle",
            ui_state["progress_stage"] or "-",
            ui_state["progress_message"] or "-",
        ]
        self.status_label.setText(" | ".join(status_parts))
        self.result_view.setPlainText(snapshot["result_view"]["summary"] or ui_state["error_message"] or "")
        self.diff_view.setPlainText(str(ui_state["latest_preview_diff"] or ""))
        self.preview_button.setEnabled(snapshot["apply_bar"]["can_preview"])
        self.commit_button.setEnabled(snapshot["apply_bar"]["can_commit"])

    def _show_error(self, title: str, exc: Exception) -> None:
        QMessageBox.critical(self, title, str(exc))
