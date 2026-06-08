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
import re
import threading
from PyQt6.QtCore import pyqtSignal, QThread

from gui.v5.telemetry import telemetry


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
        )
        self.started_signal.emit()

        try:
            # 延迟导入，避免启动时加载重依赖
            from opencopilot.agent.caller import call_agent_pipeline_sync

            full_text = ""
            chunk_count = 0
            print(
                f"[v5] AgentWorker#{self._wid} 启动 | "
                f"action={self.action_type} | session={self.session_id[:8]} | "
                f"source={self.context_source}"
            )

            for chunk in call_agent_pipeline_sync(
                self.prompt,
                action_type=self.action_type,
                session_id=self.session_id,
                is_new_task=self.is_new_task,
                context_source=self.context_source,
                context_meta=self.context_meta,
                context_envelope=self.context_envelope,
                image_base64=self.image_base64,
                enable_web_search=self.enable_web_search,
                cancel_event=self._cancel_event,
            ):
                if not self._is_running:
                    print(f"[v5] AgentWorker#{self._wid} 被取消 | chunks={chunk_count}")
                    break

                full_text += chunk
                chunk_count += 1

                # 过滤 think 标签
                display_text = self._filter_think_tags(full_text)
                self.text_updated.emit(display_text.strip())

            self.full_text = full_text
            t.emit(
                "V5_AGENT_DONE",
                worker_id=self._wid,
                action=self.action_type,
                session_id=self.session_id,
                chunks=chunk_count,
                output_len=len(full_text),
            )
            print(
                f"[v5] AgentWorker#{self._wid} 完成 | "
                f"chunks={chunk_count} | output_len={len(full_text)}"
            )
            self.finished_signal.emit(full_text)

        except Exception as e:
            t.emit(
                "V5_AGENT_ERROR",
                worker_id=self._wid,
                action=self.action_type,
                session_id=self.session_id,
                error=str(e),
                prompt_len=len(self.prompt),
                context_source=self.context_source,
            )
            print(f"[v5] AgentWorker#{self._wid} 异常 | error={e}")
            self.error_signal.emit(f"[错误]: {e}")
            self.full_text = ""

    def stop(self):
        """停止 Worker 并取消 Agent Pipeline"""
        self._is_running = False
        self._cancel_event.set()
        telemetry().emit(
            "V5_AGENT_STOP",
            worker_id=self._wid,
            action=self.action_type,
            session_id=self.session_id,
        )

    @staticmethod
    def _filter_think_tags(text: str) -> str:
        """过滤 <think> 标签，未闭合时显示思考中提示"""
        display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        if "<think>" in display:
            display = display.split("<think>")[0] + "\n\n[AI 正在深度思考中...]"
        return display
