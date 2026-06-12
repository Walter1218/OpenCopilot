"""V5AgentWorker — v5 UI 统一的 AI Agent 调用封装

设计原则：
    - UI 层只 import 本模块，不直接依赖具体后端实现
    - 统一处理 think 标签过滤、错误处理、埋点
    - 通过 pyqtSignal 将流式输出异步回传给 UI
    - 通过配置路由选择自研智能体或 vnext/provider 智能体
"""
import json
import re
import threading
import time

import httpx
from PyQt6.QtCore import QThread, pyqtSignal

from gui.v5.agent_runtime import AgentExecutionRoute, resolve_agent_route, resolve_fallback_decision
from gui.v5.telemetry import telemetry
from gui_next.smart_copilot.runtime import SmartCopilotApiRuntime


class V5AgentWorker(QThread):
    """v5 UI 统一的 Agent Pipeline Worker"""

    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    started_signal = pyqtSignal()

    _next_id = 0
    _DEFAULT_CONNECT_TIMEOUT_SEC = 5.0
    _DEFAULT_WRITE_TIMEOUT_SEC = 30.0
    _DEFAULT_POOL_TIMEOUT_SEC = 5.0
    _MIN_READ_TIMEOUT_SEC = 45.0
    _MAX_READ_TIMEOUT_SEC = 480.0
    _SIZE_TIMEOUT_DIVISOR = 600.0
    _ACTION_MIN_READ_TIMEOUT_SEC = {
        "translate": 60.0,
        "ppt": 90.0,
    }

    def __init__(
        self,
        prompt: str,
        action_type: str = "chat",
        session_id: str = "",
        context_source: str = "selection",
        context_meta: dict = None,
        context_envelope: dict = None,
        image_base64: str = None,
        is_new_task: bool = True,
        enable_web_search: bool = False,
    ):
        super().__init__()
        V5AgentWorker._next_id += 1
        self._wid = V5AgentWorker._next_id

        self.prompt = prompt
        self.action_type = action_type
        self.session_id = session_id or telemetry().new_session_id()
        self.context_source = context_source
        self.context_meta = context_meta or {}
        self.context_envelope = context_envelope
        self.image_base64 = image_base64
        self.is_new_task = is_new_task
        self.enable_web_search = enable_web_search

        self._is_running = True
        self._cancel_event = threading.Event()
        self.full_text = ""
        self._api_runtime = SmartCopilotApiRuntime()
        self._initial_route = resolve_agent_route(self.action_type)
        self._execution_route = self._initial_route
        self._fallback_used = False
        self._vnext_runtime_used = False

    def get_execution_route(self) -> AgentExecutionRoute:
        return self._execution_route

    def run(self):
        t = telemetry()
        t.emit(
            "V5_AGENT_START",
            worker_id=self._wid,
            action=self.action_type,
            session_id=self.session_id,
            text_len=len(self.prompt),
            context_source=self.context_source,
            agent_backend=self._initial_route.agent_backend,
            provider=self._initial_route.provider,
            routing_mode=self._initial_route.routing_mode,
        )
        self.started_signal.emit()

        try:
            print(
                f"[v5] AgentWorker#{self._wid} 启动 | "
                f"action={self.action_type} | session={self.session_id[:8]} | "
                f"source={self.context_source} | backend={self._execution_route.backend}"
            )
            full_text, chunk_count = self._run_with_optional_fallback(t)

            is_cancelled = self._cancel_event.is_set() or not self._is_running

            # 即使被取消，只要已有有效输出就发出 finished_signal
            # 避免 LLM 完成后因竞态取消导致结果丢失
            # 注意：vnext_provider 的 task.completed 事件直接赋值 full_text 但不增加 chunk_count
            # 所以只检查 full_text 是否非空
            if full_text:
                self.full_text = full_text
                t.emit(
                    "V5_AGENT_DONE",
                    worker_id=self._wid,
                    action=self.action_type,
                    session_id=self.session_id,
                    chunks=chunk_count,
                    output_len=len(full_text),
                    agent_backend=self._execution_route.agent_backend,
                    provider=self._execution_route.provider,
                    routing_mode=self._execution_route.routing_mode,
                    initial_agent_backend=self._initial_route.agent_backend,
                    initial_provider=self._initial_route.provider,
                    fallback_used=self._fallback_used,
                    was_cancelled=is_cancelled,
                )
                print(
                    f"[v5] AgentWorker#{self._wid} {'被取消但有输出' if is_cancelled else '完成'} | "
                    f"chunks={chunk_count} | output_len={len(full_text)}"
                )
                self.finished_signal.emit(full_text)
                return

            # 无输出且被取消 → 真正取消
            if is_cancelled:
                print(f"[v5] AgentWorker#{self._wid} 被取消 | chunks={chunk_count}")
                return

        except Exception as e:
            t.emit(
                "V5_AGENT_ERROR",
                worker_id=self._wid,
                action=self.action_type,
                session_id=self.session_id,
                error=str(e),
                prompt_len=len(self.prompt),
                context_source=self.context_source,
                agent_backend=self._execution_route.agent_backend,
                provider=self._execution_route.provider,
                routing_mode=self._execution_route.routing_mode,
                initial_agent_backend=self._initial_route.agent_backend,
                initial_provider=self._initial_route.provider,
                fallback_used=self._fallback_used,
            )
            print(f"[v5] AgentWorker#{self._wid} 异常 | error={e}")
            self.error_signal.emit(f"[错误]: {e}")
            self.full_text = ""
        finally:
            if self._vnext_runtime_used:
                self._api_runtime.shutdown()

    def stop(self):
        self._is_running = False
        self._cancel_event.set()
        telemetry().emit(
            "V5_AGENT_STOP",
            worker_id=self._wid,
            action=self.action_type,
            session_id=self.session_id,
            agent_backend=self._execution_route.agent_backend,
            provider=self._execution_route.provider,
            routing_mode=self._execution_route.routing_mode,
            fallback_used=self._fallback_used,
        )

    def _run_with_optional_fallback(self, telemetry_client) -> tuple[str, int]:
        try:
            return self._run_current_route()
        except Exception as error:
            decision = resolve_fallback_decision(error, self._execution_route)
            if not decision.enabled:
                raise

            target_route = AgentExecutionRoute(
                backend=decision.target_backend,
                provider=decision.target_provider,
                model=self._initial_route.model,
                routing_mode=f"fallback_{decision.reason}",
            )
            telemetry_client.emit(
                "V5_AGENT_FALLBACK",
                worker_id=self._wid,
                action=self.action_type,
                session_id=self.session_id,
                from_agent_backend=self._execution_route.agent_backend,
                from_provider=self._execution_route.provider,
                to_agent_backend=target_route.agent_backend,
                to_provider=target_route.provider,
                reason=decision.reason,
            )
            self._fallback_used = True
            self._execution_route = target_route
            return self._run_current_route()

    def _run_current_route(self) -> tuple[str, int]:
        if self._execution_route.backend == "self_agent":
            return self._run_self_agent()
        return self._run_vnext_provider()

    def _build_selection_text(self) -> str:
        source_text = self.context_meta.get("source_text")
        if isinstance(source_text, str) and source_text.strip():
            return source_text
        task_text = self.context_meta.get("task")
        if isinstance(task_text, str) and task_text.strip():
            return task_text
        if self.action_type == "chat":
            return ""
        return self.prompt

    def _build_context_snapshot_payload(self) -> dict:
        metadata = {
            "context_source": self.context_source,
            "context_meta": self.context_meta,
            "context_envelope": self.context_envelope or {},
            "image_attached": bool(self.image_base64),
            "enable_web_search": self.enable_web_search,
        }
        return {
            "trigger": "double_right_click" if self.context_source != "chat" else "chat_send",
            "source_app": f"v5_{self.context_source}",
            "selection_text": self._build_selection_text(),
            "document_title": self.context_meta.get("file_path", "") or self.context_meta.get("source_type", ""),
            "metadata": metadata,
        }

    def _create_context_snapshot(self, client: httpx.Client) -> str:
        response = client.post("/vnext/context/snapshots", json=self._build_context_snapshot_payload())
        response.raise_for_status()
        return response.json()["context_snapshot_id"]

    def _create_task(self, client: httpx.Client, context_snapshot_id: str) -> str:
        response = client.post(
            "/vnext/tasks",
            json={
                "action": self.action_type,
                "user_input": self.prompt,
                "context_snapshot_id": context_snapshot_id,
                "agent_preferences": {
                    "provider": self._execution_route.provider,
                    "model": self._execution_route.model,
                },
            },
        )
        response.raise_for_status()
        return response.json()["task_id"]

    def _run_self_agent(self) -> tuple[str, int]:
        from opencopilot.agent.caller import call_agent_pipeline_sync

        full_text = ""
        chunk_count = 0
        timeout = self._build_client_timeout().read
        for chunk in call_agent_pipeline_sync(
            text=self.prompt,
            action_type=self.action_type,
            session_id=self.session_id,
            context_source=self.context_source,
            context_meta=self.context_meta,
            context_envelope=self.context_envelope,
            image_base64=self.image_base64,
            is_new_task=self.is_new_task,
            enable_web_search=self.enable_web_search,
            timeout=timeout,
            cancel_event=self._cancel_event,
        ):
            if self._cancel_event.is_set() or not self._is_running:
                break
            full_text += chunk
            chunk_count += 1
            self.text_updated.emit(self._filter_think_tags(full_text).strip())
        return full_text, chunk_count

    def _run_vnext_provider(self) -> tuple[str, int]:
        full_text = ""
        chunk_count = 0
        task_id = ""
        self._vnext_runtime_used = True
        base_url = self._api_runtime.ensure_ready()
        client_timeout = self._build_client_timeout()
        with httpx.Client(base_url=base_url, timeout=client_timeout) as client:
            context_snapshot_id = self._create_context_snapshot(client)
            task_id = self._create_task(client, context_snapshot_id)

            last_sequence = 0
            terminal_seen = False
            while self._is_running and not self._cancel_event.is_set():
                events_response = client.get(f"/vnext/tasks/{task_id}/events")
                events_response.raise_for_status()
                events = events_response.json().get("events", [])
                fresh_events = [event for event in events if event.get("sequence", 0) > last_sequence]

                for event in fresh_events:
                    last_sequence = max(last_sequence, event.get("sequence", 0))
                    event_type = event.get("type", "")
                    payload = event.get("payload", {})
                    if event_type == "task.delta":
                        full_text += payload.get("delta", "")
                        chunk_count += 1
                        self.text_updated.emit(self._filter_think_tags(full_text).strip())
                    elif event_type == "task.completed":
                        summary = payload.get("summary", "")
                        if summary:
                            full_text = summary
                            self.text_updated.emit(self._filter_think_tags(full_text).strip())
                        terminal_seen = True
                    elif event_type == "task.failed":
                        raise RuntimeError(payload.get("error") or payload.get("message") or "Hermes task failed")

                if terminal_seen:
                    break
                time.sleep(0.35)

            if self._cancel_event.is_set() or not self._is_running:
                return full_text, chunk_count

            task_response = client.get(f"/vnext/tasks/{task_id}")
            task_response.raise_for_status()
            task_payload = task_response.json()
            if task_payload.get("error"):
                raise RuntimeError(task_payload["error"].get("message", "Hermes task failed"))
            result = task_payload.get("result") or {}
            final_summary = result.get("summary", "")
            if final_summary:
                full_text = final_summary
                self.text_updated.emit(self._filter_think_tags(full_text).strip())

        return full_text, chunk_count

    @classmethod
    def _safe_json_size(cls, value) -> int:
        if not value:
            return 0
        try:
            return len(json.dumps(value, ensure_ascii=False, default=str))
        except (TypeError, ValueError):
            return len(str(value))

    def _estimate_input_size_chars(self) -> int:
        selection_text = self._build_selection_text()
        image_size = len(self.image_base64) // 4 if self.image_base64 else 0
        return (
            len(self.prompt)
            + len(selection_text)
            + self._safe_json_size(self.context_meta)
            + self._safe_json_size(self.context_envelope or {})
            + image_size
        )

    def _build_client_timeout(self) -> httpx.Timeout:
        estimated_chars = self._estimate_input_size_chars()
        size_based_timeout = self._MIN_READ_TIMEOUT_SEC + min(
            300.0,
            estimated_chars / self._SIZE_TIMEOUT_DIVISOR,
        )
        action_floor = self._ACTION_MIN_READ_TIMEOUT_SEC.get(
            self.action_type,
            self._MIN_READ_TIMEOUT_SEC,
        )
        read_timeout = min(
            self._MAX_READ_TIMEOUT_SEC,
            max(action_floor, size_based_timeout),
        )
        return httpx.Timeout(
            connect=self._DEFAULT_CONNECT_TIMEOUT_SEC,
            read=read_timeout,
            write=self._DEFAULT_WRITE_TIMEOUT_SEC,
            pool=self._DEFAULT_POOL_TIMEOUT_SEC,
        )

    @staticmethod
    def _filter_think_tags(text: str) -> str:
        display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        if "<think>" in display:
            display = display.split("<think>")[0] + "\n\n[AI 正在深度思考中...]"
        return display
