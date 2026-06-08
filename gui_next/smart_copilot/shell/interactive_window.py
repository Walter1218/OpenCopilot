from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..components import ActionBarModel
from ..services import UnifiedApiClient
from .floating_panel import FloatingPanel


@dataclass(slots=True)
class _StatusLabels:
    status: QLabel
    context_id: QLabel
    task_id: QLabel
    progress: QLabel
    action: QLabel


class InteractiveTestWindow(QWidget):
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000") -> None:
        super().__init__()
        self._action_bar = ActionBarModel()
        self._panel: FloatingPanel | None = None
        self._request_log: list[dict[str, Any]] = []
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(350)
        self._poll_timer.timeout.connect(self._poll_task_events)
        self._build_ui()
        self._reset_panel(api_base_url)
        self._apply_defaults()
        self._render_state()

    def closeEvent(self, event: Any) -> None:  # type: ignore[override]
        self._poll_timer.stop()
        if self._panel is not None:
            self._panel.close()
        super().closeEvent(event)

    def summon_context(self) -> dict[str, Any]:
        panel = self._ensure_panel()
        response = panel.summon(
            source_app=self.source_app_input.text().strip() or "Cursor",
            selection_text=self.selection_input.toPlainText(),
            document_title=self.document_title_input.text().strip(),
            metadata={"interactive_test": True},
        )
        self._append_log("context", response)
        self._render_state()
        return response

    def start_task(self) -> dict[str, Any]:
        panel = self._ensure_panel()
        if not panel.ui_state.latest_context_id:
            self.summon_context()
        response = panel.task_vm.create_task(
            action=self.action_selector.currentText(),
            context_snapshot_id=panel.ui_state.latest_context_id,
            user_input=self.user_input.toPlainText(),
        )
        self._append_log("task", response)
        self._render_state()
        self._poll_timer.start()
        return response

    def preview_apply(self) -> dict[str, Any]:
        panel = self._ensure_panel()
        preview = panel.preview_latest_apply()
        self._append_log("preview", preview)
        self._render_state()
        return preview

    def commit_apply(self) -> dict[str, Any]:
        panel = self._ensure_panel()
        result = panel.commit_latest_preview()
        self._append_log("commit", result)
        self._render_state()
        return result

    def refresh_state(self) -> None:
        panel = self._ensure_panel()
        if panel.ui_state.latest_task_id:
            panel.task_vm.refresh_task_state()
        self._render_state()

    def _build_ui(self) -> None:
        self.setWindowTitle("Smart Copilot vNext Interactive Test")
        self.resize(1180, 820)

        root = QVBoxLayout(self)
        root.addWidget(self._build_connection_group())
        root.addWidget(self._build_input_group())
        root.addLayout(self._build_action_row())
        root.addWidget(self._build_status_group())
        root.addLayout(self._build_output_grid())

    def _build_connection_group(self) -> QGroupBox:
        group = QGroupBox("Connection")
        form = QFormLayout(group)
        self.api_base_url_input = QLineEdit()
        self.api_base_url_input.setPlaceholderText("http://127.0.0.1:8000")
        form.addRow("API Base URL", self.api_base_url_input)
        return group

    def _build_input_group(self) -> QGroupBox:
        group = QGroupBox("Input")
        layout = QVBoxLayout(group)

        top_form = QFormLayout()
        self.source_app_input = QLineEdit()
        self.document_title_input = QLineEdit()
        self.action_selector = QComboBox()
        self.action_selector.addItems(self._action_bar.actions)
        top_form.addRow("Source App", self.source_app_input)
        top_form.addRow("Document Title", self.document_title_input)
        top_form.addRow("Action", self.action_selector)
        layout.addLayout(top_form)

        self.selection_input = QTextEdit()
        self.selection_input.setPlaceholderText("Selection text")
        self.selection_input.setMinimumHeight(140)
        layout.addWidget(QLabel("Selection Text"))
        layout.addWidget(self.selection_input)

        self.user_input = QTextEdit()
        self.user_input.setPlaceholderText("Optional follow-up or user instruction")
        self.user_input.setMinimumHeight(100)
        layout.addWidget(QLabel("User Input"))
        layout.addWidget(self.user_input)
        return group

    def _build_action_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        self.summon_button = QPushButton("Summon Context")
        self.run_button = QPushButton("Run Task")
        self.preview_button = QPushButton("Preview Apply")
        self.commit_button = QPushButton("Commit Apply")
        self.refresh_button = QPushButton("Refresh")
        self.reset_button = QPushButton("Reconnect")

        self.summon_button.clicked.connect(self._on_summon_clicked)
        self.run_button.clicked.connect(self._on_run_clicked)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        self.commit_button.clicked.connect(self._on_commit_clicked)
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        self.reset_button.clicked.connect(self._on_reconnect_clicked)

        layout.addWidget(self.summon_button)
        layout.addWidget(self.run_button)
        layout.addWidget(self.preview_button)
        layout.addWidget(self.commit_button)
        layout.addWidget(self.refresh_button)
        layout.addStretch(1)
        layout.addWidget(self.reset_button)
        return layout

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("State")
        form = QFormLayout(group)
        self.status_labels = _StatusLabels(
            status=QLabel("-"),
            context_id=QLabel("-"),
            task_id=QLabel("-"),
            progress=QLabel("-"),
            action=QLabel("-"),
        )
        form.addRow("Status", self.status_labels.status)
        form.addRow("Context ID", self.status_labels.context_id)
        form.addRow("Task ID", self.status_labels.task_id)
        form.addRow("Progress", self.status_labels.progress)
        form.addRow("Active Action", self.status_labels.action)
        return group

    def _build_output_grid(self) -> QGridLayout:
        grid = QGridLayout()

        self.summary_output = QPlainTextEdit()
        self.summary_output.setReadOnly(True)
        self.diff_output = QPlainTextEdit()
        self.diff_output.setReadOnly(True)
        self.events_output = QPlainTextEdit()
        self.events_output.setReadOnly(True)
        self.events_output.setMinimumHeight(220)

        grid.addWidget(QLabel("Result Summary"), 0, 0)
        grid.addWidget(QLabel("Apply Preview Diff"), 0, 1)
        grid.addWidget(self.summary_output, 1, 0)
        grid.addWidget(self.diff_output, 1, 1)
        grid.addWidget(QLabel("Event Log"), 2, 0, 1, 2)
        grid.addWidget(self.events_output, 3, 0, 1, 2)
        return grid

    def _apply_defaults(self) -> None:
        self.api_base_url_input.setText("http://127.0.0.1:8000")
        self.source_app_input.setText("Cursor")
        self.document_title_input.setText("demo.py")
        self.selection_input.setPlainText("def legacy_func(x):\n    return x")
        self.user_input.setPlainText("请帮我 review 并输出更好的版本")

    def _reset_panel(self, api_base_url: str | None = None) -> None:
        normalized_url = (api_base_url or self.api_base_url_input.text().strip() or "http://127.0.0.1:8000").rstrip(
            "/"
        )
        if self._panel is not None:
            self._panel.close()
        self.api_base_url_input.setText(normalized_url)
        self._panel = FloatingPanel(api_client=UnifiedApiClient(base_url=normalized_url))
        self._request_log = []

    def _ensure_panel(self) -> FloatingPanel:
        requested_url = (self.api_base_url_input.text().strip() or "http://127.0.0.1:8000").rstrip("/")
        if self._panel is None or self._panel.api_client.base_url != requested_url:
            self._reset_panel(requested_url)
        return self._panel

    def _render_state(self) -> None:
        panel = self._ensure_panel()
        snapshot = panel.snapshot()
        ui_state = snapshot["ui_state"]
        self.status_labels.status.setText(ui_state["status"] or "-")
        self.status_labels.context_id.setText(ui_state["latest_context_id"] or "-")
        self.status_labels.task_id.setText(ui_state["latest_task_id"] or "-")
        self.status_labels.progress.setText(
            f'{ui_state["progress_stage"] or "-"} | {ui_state["progress_message"] or "-"}'
        )
        self.status_labels.action.setText(ui_state["active_action"] or "-")
        self.summary_output.setPlainText(snapshot["result_view"]["summary"] or "")
        self.diff_output.setPlainText(json.dumps(ui_state["latest_preview_diff"], ensure_ascii=False, indent=2))
        merged_log = {
            "request_log": self._request_log,
            "event_log": ui_state["event_log"],
        }
        self.events_output.setPlainText(json.dumps(merged_log, ensure_ascii=False, indent=2))

        self.preview_button.setEnabled(snapshot["apply_bar"]["can_preview"])
        self.commit_button.setEnabled(snapshot["apply_bar"]["can_commit"])
        self.run_button.setEnabled(bool(ui_state["latest_context_id"]) or bool(self.selection_input.toPlainText().strip()))

    def _poll_task_events(self) -> None:
        panel = self._ensure_panel()
        try:
            events = panel.task_vm.poll_once()
            if events:
                self._append_log("events", events)
            self._render_state()
            status = panel.ui_state.status
            if status in {"succeeded", "failed", "cancelled"}:
                self._poll_timer.stop()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._poll_timer.stop()
            self._show_error("Poll Task Events Failed", exc)

    def _append_log(self, kind: str, payload: Any) -> None:
        self._request_log.append({"kind": kind, "payload": payload})

    def _show_error(self, title: str, exc: Exception) -> None:
        QMessageBox.critical(self, title, str(exc))

    def _on_summon_clicked(self) -> None:
        try:
            self.summon_context()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Summon Context Failed", exc)

    def _on_run_clicked(self) -> None:
        try:
            self.start_task()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Run Task Failed", exc)

    def _on_preview_clicked(self) -> None:
        try:
            self.preview_apply()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Preview Apply Failed", exc)

    def _on_commit_clicked(self) -> None:
        try:
            self.commit_apply()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Commit Apply Failed", exc)

    def _on_refresh_clicked(self) -> None:
        try:
            self.refresh_state()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Refresh Failed", exc)

    def _on_reconnect_clicked(self) -> None:
        try:
            self._poll_timer.stop()
            self._reset_panel()
            self._render_state()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self._show_error("Reconnect Failed", exc)
