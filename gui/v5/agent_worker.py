"""V5AgentWorker — v5 UI 统一的 AI Agent 调用封装

设计原则：
    - UI 层只 import 本模块，不直接依赖 opencopilot.agent.caller
    - 统一处理 think 标签过滤、错误处理、埋点
    - 通过 pyqtSignal 将流式输出异步回传给 UI

用法：
    from gui.v5.agent_worker import V5AgentWorker

    worker = V5AgentWorker(
        prompt="解释这段代码",
        action_type="explain",
        session_id="...",
        context_source="selection",
        context_meta={"source_text": "..."},
    )
    worker.text_updated.connect(self._update_result)
    worker.finished_signal.connect(self._on_finished)
    worker.error_signal.connect(self._on_error)
    worker.start()

    # 取消
    worker.stop()
"""
import json
import re
import threading
import time

import httpx
from PyQt6.QtCore import pyqtSignal, QThread

from gui.v5.telemetry import telemetry
from gui_next.smart_copilot.runtime import SmartCopilotApiRuntime


class V5AgentWorker(QThread):
    """v5 UI 统一的 Agent Pipeline Worker

    Signals:
        text_updated(str):   流式 chunk 输出（已过滤 think 标签）
        finished_signal(str): 完成时返回完整文本
        error_signal(str):    错误信息
        started_signal():     Worker 启动时发射
    """

    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    started_signal = pyqtSignal()

    _next_id = 0  # 类变量，进程级自增
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
        """
        Args:
            prompt: 用户输入文本 / 指令
            action_type: 动作类型 — explain/fix/polish/chat/coding/ppt/translate/...
            session_id: 会话 ID（空则自动生成）
            context_source: 上下文来源 — selection/active_doc/browser/clipboard/file/chat
            context_meta: 上下文元信息（如 source_text、file_path 等）
            context_envelope: 上下文信封（IDE/文档全文+选中文本等）
            image_base64: 图片 Base64 编码
            is_new_task: 是否新任务（影响会话记忆重置）
            enable_web_search: 是否启用联网搜索（调研模式自动开启）
        """
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

    def run(self):
        """执行 Agent Pipeline，流式输出通过 Signal 回传"""
        t = telemetry()
        t.emit(
            "V5_AGENT_START",
            worker_id=self._wid,
            action=self.action_type,
            session_id=self.session_id,
            text_len=len(self.prompt),
            context_source=self.context_source,
            agent_backend="hermes_vnext",
            provider="hermes_local",
        )
        self.started_signal.emit()

        try:
            full_text = ""
            chunk_count = 0
            print(
                f"[v5] AgentWorker#{self._wid} 启动 | "
                f"action={self.action_type} | session={self.session_id[:8]} | "
                f"source={self.context_source}"
            )
            # #region debug-point A:worker-start
            import json, urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"A","location":"gui/v5/agent_worker.py:run","msg":"[DEBUG] V5AgentWorker run start","data":{"action_type":self.action_type,"context_source":self.context_source,"session_id":self.session_id,"prompt_len":len(self.prompt),"context_meta_keys":sorted(list(self.context_meta.keys()))}}).encode(), headers={"Content-Type":"application/json"})).read()
            # #endregion

            task_id = ""
            base_url = self._api_runtime.ensure_ready()
            # #region debug-point C:api-runtime
            import json, urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"C","location":"gui/v5/agent_worker.py:run","msg":"[DEBUG] API runtime ready","data":{"base_url":base_url}}).encode(), headers={"Content-Type":"application/json"})).read()
            # #endregion
            client_timeout = self._build_client_timeout()
            with httpx.Client(base_url=base_url, timeout=client_timeout) as client:
                context_snapshot_id = self._create_context_snapshot(client)
                # #region debug-point A:context-created
                import json, urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"A","location":"gui/v5/agent_worker.py:run","msg":"[DEBUG] Context snapshot created","data":{"context_snapshot_id":context_snapshot_id,"selection_len":len(self._build_selection_text())}}).encode(), headers={"Content-Type":"application/json"})).read()
                # #endregion
                task_id = self._create_task(client, context_snapshot_id)
                # #region debug-point A:task-created
                import json, urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"A","location":"gui/v5/agent_worker.py:run","msg":"[DEBUG] Task created","data":{"task_id":task_id,"action_type":self.action_type}}).encode(), headers={"Content-Type":"application/json"})).read()
                # #endregion

                last_sequence = 0
                terminal_seen = False
                while self._is_running and not self._cancel_event.is_set():
                    events_response = client.get(f"/vnext/tasks/{task_id}/events")
                    events_response.raise_for_status()
                    events = events_response.json().get("events", [])
                    fresh_events = [event for event in events if event.get("sequence", 0) > last_sequence]
                    # #region debug-point A:event-batch
                    import json, urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"A","location":"gui/v5/agent_worker.py:run","msg":"[DEBUG] Event batch fetched","data":{"task_id":task_id,"total_events":len(events),"fresh_events":len(fresh_events),"last_sequence":last_sequence}}).encode(), headers={"Content-Type":"application/json"})).read()
                    # #endregion

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
                    print(f"[v5] AgentWorker#{self._wid} 被取消 | chunks={chunk_count}")
                    return

                task_response = client.get(f"/vnext/tasks/{task_id}")
                task_response.raise_for_status()
                task_payload = task_response.json()
                # #region debug-point D:task-result
                import json, urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"D","location":"gui/v5/agent_worker.py:run","msg":"[DEBUG] Task payload fetched","data":{"task_id":task_id,"status":task_payload.get("status"),"provider_run_id":task_payload.get("provider_run_id"),"has_result":bool(task_payload.get("result")),"error":task_payload.get("error")}}).encode(), headers={"Content-Type":"application/json"})).read()
                # #endregion
                if task_payload.get("error"):
                    raise RuntimeError(task_payload["error"].get("message", "Hermes task failed"))
                result = task_payload.get("result") or {}
                final_summary = result.get("summary", "")
                if final_summary:
                    full_text = final_summary
                    self.text_updated.emit(self._filter_think_tags(full_text).strip())

            self.full_text = full_text
            t.emit(
                "V5_AGENT_DONE",
                worker_id=self._wid,
                action=self.action_type,
                session_id=self.session_id,
                chunks=chunk_count,
                output_len=len(full_text),
                agent_backend="hermes_vnext",
                provider="hermes_local",
            )
            print(
                f"[v5] AgentWorker#{self._wid} 完成 | "
                f"chunks={chunk_count} | output_len={len(full_text)}"
            )
            self.finished_signal.emit(full_text)

        except Exception as e:
            # #region debug-point D:worker-exception
            import json, urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"D","location":"gui/v5/agent_worker.py:run","msg":"[DEBUG] Worker exception","data":{"error":str(e),"action_type":self.action_type,"context_source":self.context_source}}).encode(), headers={"Content-Type":"application/json"})).read()
            # #endregion
            t.emit(
                "V5_AGENT_ERROR",
                worker_id=self._wid,
                action=self.action_type,
                session_id=self.session_id,
                error=str(e),
                prompt_len=len(self.prompt),
                context_source=self.context_source,
                agent_backend="hermes_vnext",
                provider="hermes_local",
            )
            print(f"[v5] AgentWorker#{self._wid} 异常 | error={e}")
            self.error_signal.emit(f"[错误]: {e}")
            self.full_text = ""
        finally:
            self._api_runtime.shutdown()

    def stop(self):
        """停止 Worker 并取消 Agent Pipeline"""
        self._is_running = False
        self._cancel_event.set()
        telemetry().emit(
            "V5_AGENT_STOP",
            worker_id=self._wid,
            action=self.action_type,
            session_id=self.session_id,
            agent_backend="hermes_vnext",
            provider="hermes_local",
        )

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
                "agent_preferences": {"provider": "hermes_local"},
            },
        )
        response.raise_for_status()
        return response.json()["task_id"]

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
        """过滤 <think> 标签，未闭合时显示思考中提示"""
        display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        if "<think>" in display:
            display = display.split("<think>")[0] + "\n\n[AI 正在深度思考中...]"
        return display
