"""V5Telemetry — v5.0 UI 层埋点工具

薄封装层，通过 PipelineObservability.gui_log() 输出结构化事件日志。
所有 v5 模块统一使用此类进行 trace/debug/metrics。

事件命名规范: V5_{MODULE}_{ACTION}
  MODULE: SC / WORK / CHAT / STAB / SWIN / NAV / SET / WS
  ACTION: OPEN / CLOSE / SHOW / HIDE / CLICK / SEND / SWITCH / TOGGLE /
          LLM_START / LLM_CHUNK / LLM_DONE / LLM_ERROR / ...

Correlation ID 传播:
  app_run_id (进程级) → session_id (会话级) → trace_id (请求级)
"""
import time
import uuid
import json
from typing import Optional


class V5Telemetry:
    """v5 UI 层统一埋点工具（Singleton via _instance）"""

    _instance: Optional["V5Telemetry"] = None

    def __init__(self):
        self._obs = None  # PipelineObservability (lazy init)

    @classmethod
    def get(cls) -> "V5Telemetry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =========================================================================
    # 核心 emit
    # =========================================================================

    def emit(self, event: str, *, session_id: str = "", trace_id: str = "",
             **kwargs):
        """发送一条结构化事件日志。

        参数:
            event:      事件名，如 V5_SC_TAB_SWITCH
            session_id: 会话级关联 ID
            trace_id:   请求级追踪 ID
            **kwargs:   附加 context 字段 (action_id, text_len, etc.)
        """
        obs = self._get_obs()
        payload = {
            "ui_version": "v5",
            "ui_surface": "desktop",
            **kwargs,
        }

        if obs is None:
            # 降级: PipelineObservability 未初始化时走 stderr
            import sys
            parts = [f"[V5] {event}"]
            if trace_id:
                parts.append(f"trace={trace_id[:8]}")
            parts.extend(f"{k}={v}" for k, v in payload.items())
            sys.stderr.write(" | ".join(parts) + "\n")
            return

        # 构造消息: "V5_SC_TAB_SWITCH | from=0 to=1 tab=Chat"
        msg_parts = [event]
        msg_parts.extend(f"{k}={v}" for k, v in payload.items())
        msg = " | ".join(msg_parts)

        # 将 trace_id 和附加数据序列化到 data_json
        extra = {"trace_id": trace_id} if trace_id else {}
        extra.update(payload)
        data_json = json.dumps(extra, ensure_ascii=False, default=str) if extra else ""

        obs._write_log(
            f"[GUI] {msg}",
            source="V5_GUI",
            event=event,
            session_id=session_id,
            data_json=data_json,
        )

    # =========================================================================
    # 便捷方法
    # =========================================================================

    def window_event(self, event: str, window_type: str, **kwargs):
        """窗口生命周期事件"""
        self.emit(event, window_type=window_type, **kwargs)

    def action_event(self, event: str, action_id: str, source: str = "",
                     **kwargs):
        """用户操作事件"""
        self.emit(event, action_id=action_id, source=source, **kwargs)

    def nav_event(self, event: str, **kwargs):
        """导航跳转事件"""
        self.emit(event, **kwargs)

    def settings_event(self, event: str, section: str = "", **kwargs):
        """设置变更事件"""
        self.emit(event, section=section, **kwargs)

    # =========================================================================
    # LLM 请求链路追踪
    # =========================================================================

    def llm_start(self, source_tab: str, action_type: str,
                  session_id: str = "", text_len: int = 0) -> dict:
        """LLM 请求开始，返回 trace context 供后续事件关联。

        返回:
            {"trace_id": str, "session_id": str, "start_time": float}
        """
        trace_id = self.new_trace_id()
        if not session_id:
            session_id = self.new_session_id()
        ctx = {
            "trace_id": trace_id,
            "session_id": session_id,
            "start_time": time.monotonic(),
        }
        self.emit(
            f"V5_{source_tab}_LLM_START",
            session_id=session_id,
            trace_id=trace_id,
            action_type=action_type,
            text_len=text_len,
        )
        return ctx

    def llm_chunk(self, ctx: dict, source_tab: str, chunk_count: int = 0,
                   output_len: int = 0):
        """LLM 流式 chunk 到达（仅在关键节点打，不要每条都打）"""
        self.emit(
            f"V5_{source_tab}_LLM_CHUNK",
            session_id=ctx.get("session_id", ""),
            trace_id=ctx.get("trace_id", ""),
            chunk_count=chunk_count,
            output_len=output_len,
        )

    def llm_done(self, ctx: dict, source_tab: str, chunk_count: int = 0,
                 output_len: int = 0):
        """LLM 请求完成"""
        elapsed_ms = 0
        if "start_time" in ctx:
            elapsed_ms = round((time.monotonic() - ctx["start_time"]) * 1000, 1)
        self.emit(
            f"V5_{source_tab}_LLM_DONE",
            session_id=ctx.get("session_id", ""),
            trace_id=ctx.get("trace_id", ""),
            chunk_count=chunk_count,
            output_len=output_len,
            elapsed_ms=elapsed_ms,
        )

    def llm_error(self, ctx: dict, source_tab: str, error_msg: str):
        """LLM 请求错误"""
        elapsed_ms = 0
        if "start_time" in ctx:
            elapsed_ms = round((time.monotonic() - ctx["start_time"]) * 1000, 1)
        self.emit(
            f"V5_{source_tab}_LLM_ERROR",
            session_id=ctx.get("session_id", ""),
            trace_id=ctx.get("trace_id", ""),
            error_msg=error_msg,
            elapsed_ms=elapsed_ms,
        )

    # =========================================================================
    # ID 生成
    # =========================================================================

    @staticmethod
    def new_trace_id() -> str:
        """生成请求级 trace ID"""
        return uuid.uuid4().hex[:16]

    @staticmethod
    def new_session_id() -> str:
        """生成会话级 session ID"""
        return uuid.uuid4().hex[:16]

    # =========================================================================
    # 计时器
    # =========================================================================

    @staticmethod
    def timer():
        """返回一个计时上下文，用于测量操作耗时。

        用法:
            t = V5Telemetry.timer()
            # ... do work ...
            elapsed_ms = t.elapsed_ms()
        """
        return _Timer()

    # =========================================================================
    # 内部
    # =========================================================================

    def _get_obs(self):
        """Lazy 获取 PipelineObservability 实例"""
        if self._obs is None:
            try:
                from opencopilot.agent.observability import PipelineObservability
                self._obs = PipelineObservability.get_instance()
            except Exception:
                pass  # 启动阶段可能还没初始化
        return self._obs


class _Timer:
    """轻量计时器"""

    def __init__(self):
        self._start = time.monotonic()

    def elapsed_ms(self) -> float:
        return round((time.monotonic() - self._start) * 1000, 1)


# 模块级便捷引用
telemetry = V5Telemetry.get
