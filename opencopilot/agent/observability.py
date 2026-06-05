"""
管线统——可观测性模块

解决三套割裂的追踪/日志系统：
  1. 消除 _timer_log() 在 pipeline.py 和 middlewares.py 中重复定义
  2. 将 [Timer] 埋点接入 ObservabilityModule 的 Metrics + Tracer
  3. 提供统一的 SQLite 持久化日志出口（替代易丢失的文本文件）

用法:
  from opencopilot.agent.observability import PipelineObservability

  obs = PipelineObservability.get_instance()
  obs.timer("SessionSetup", total=0.003, extra={"mem": 0.002, "persona": 0.001})
  obs.log("Pipeline", "LLM call completed", level="info")
  obs.metric("llm.ttfb", 2.426, tags={"action_type": "default"})
"""
import os
import time
import threading
import sys
import traceback
from dataclasses import field, dataclass
from typing import Optional, Dict, Any, List


class _NullObservability:
    """空实现，当 ObservabilityModule 不可用时降级"""
    def log(self, *args, **kwargs): pass
    def metric(self, *args, **kwargs): pass
    def trace_start(self, *args, **kwargs): return None
    def trace_end(self, *args, **kwargs): pass
    def span(self, *args, **kwargs): pass


@dataclass
class TimerEntry:
    """单个中间件的计时记录"""
    name: str               # 中间件名称
    total: float = 0.0      # 总耗时(s)
    extra: Dict[str, float] = field(default_factory=dict)  # 细分项目
    session_id: str = ""
    action_type: str = "default"
    error: Optional[str] = None
    timestamp: float = 0.0


class PipelineObservability:
    """
    管线可观测性统一入口。

    Singleton 模式，所有管线模块通过此类输出计时/日志/指标。
    日志写入 SQLite（pipeline_logs.db），同时输出到 stderr 便于终端查看。
    """

    _instance: Optional["PipelineObservability"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._obs = None           # ObservabilityModule 实例
        self._timer_history: List[TimerEntry] = []  # 最近 100 条计时记录
        self._max_history = 100
        self._log_store = None     # LogStore 实例（延迟初始化）

        # 尝试导入 ObservabilityModule
        try:
            from opencopilot.observability import (
                ObservabilityModule, ObservabilityConfig, LogLevel,
            )
            self._obs_config = ObservabilityConfig(
                log_level=LogLevel.INFO.value,
                enable_tracing=True,
                enable_performance_monitoring=True,
            )
            self._obs_module = ObservabilityModule(self._obs_config)
            self._have_obs = True
        except Exception:
            self._obs_module = _NullObservability()
            self._have_obs = False
            # 诊断日志：ObservabilityModule 导入失败时输出原因
            sys.stderr.write(
                f"[PipelineObservability] WARN: ObservabilityModule 导入失败，"
                f"降级为空实现。原因: {traceback.format_exc()}\n"
            )
            sys.stderr.flush()

    @classmethod
    def get_instance(cls) -> "PipelineObservability":
        """获取单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def set_observability_module(cls, obs_module):
        """注入外部 ObservabilityModule 实例（由 asu_custom_agent.py 调用）"""
        inst = cls.get_instance()
        inst._obs_module = obs_module
        inst._have_obs = obs_module is not None

    # ---- 内部工具 ----

    def _get_log_store(self):
        """延迟初始化 LogStore"""
        if self._log_store is None:
            from .log_store import LogStore
            self._log_store = LogStore.get_instance()
        return self._log_store

    def _thread_tag(self) -> str:
        """返回当前线程标识，用于日志追踪"""
        return f"[T-{threading.current_thread().ident}]"

    def _write_log(
        self, msg: str, *,
        session_id: str = "",
        source: str = "",
        event: str = "LOG",
        level: str = "INFO",
        caller_id: Optional[int] = None,
        worker_id: Optional[int] = None,
        worker_type: str = "",
        chunk_count: Optional[int] = None,
        elapsed_ms: Optional[float] = None,
        data_json: str = "",
    ):
        """统一日志输出：stderr + SQLite"""
        tagged = f"{self._thread_tag()} {msg}"
        # 使用 stderr 而非 stdout，避免被 PyQt 事件循环吞掉
        sys.stderr.write(tagged + "\n")
        sys.stderr.flush()

        # 写入 SQLite
        try:
            store = self._get_log_store()
            store.insert(
                session_id=session_id,
                caller_id=caller_id,
                worker_id=worker_id,
                worker_type=worker_type,
                event=event,
                level=level,
                source=source,
                message=msg,
                chunk_count=chunk_count,
                elapsed_ms=elapsed_ms,
                data_json=data_json,
            )
        except Exception:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()

    # ---- Timer 埋点 ----

    def timer(self, middleware_or_msg: str, total: float = 0.0, *,
              extra: Dict[str, float] = None,
              session_id: str = "",
              action_type: str = "default",
              status: str = "ok"):
        """
        记录中间件计时。

        支持两种调用方式：
          1. 结构化: obs.timer("SessionSetup", 0.003, extra={"mem": 0.002})
          2. 兼容旧格式: obs.timer("[Timer] SessionSetup: total=0.003s | mem=0.002")

        - 写入 pipeline_timer.log 文件
        - 输出到 stdout (flush)
        - 记录到 ObservabilityModule 的 metrics（如果可用）
        """
        # 检测是否是预格式化的消息字符串
        raw_msg = middleware_or_msg
        if raw_msg.startswith("[Timer] "):
            msg = raw_msg
            # 从消息中提取 middleware 名称和 total 用于 metrics
            try:
                rest = raw_msg[len("[Timer] "):]
                mw = rest.split(":")[0].strip()
                # 解析 total=X.XXXs
                import re
                total_match = re.search(r'total=([\d.]+)s', rest)
                if total_match and total == 0.0:
                    total = float(total_match.group(1))
            except Exception:
                mw = ""
        else:
            # 结构化调用
            mw = middleware_or_msg
            if extra:
                parts = " | ".join(f"{k}={v:.3f}" for k, v in extra.items())
                msg = f"[Timer] {mw}: total={total:.3f}s | {parts}"
            else:
                msg = f"[Timer] {mw}: total={total:.3f}s"

        if status != "ok":
            msg += f" ({status})"

        self._write_log(msg)

        # 历史记录（内存，最近 100 条）
        entry = TimerEntry(
            name=mw,
            total=total,
            extra=extra or {},
            session_id=session_id,
            action_type=action_type,
            timestamp=time.time(),
        )
        self._timer_history.append(entry)
        if len(self._timer_history) > self._max_history:
            self._timer_history.pop(0)

        # 发送到 ObservabilityModule metrics（异步方法，在同步上下文中 fire-and-forget）
        if self._have_obs and mw:
            try:
                import asyncio
                loop = getattr(threading.current_thread(), "_obs_loop", None)
                if loop is None or loop.is_closed():
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                if loop and loop.is_running():
                    # 在已有事件循环中，创建 task
                    loop.create_task(self._obs_module.record_metric(
                        name=f"pipeline.{mw}.duration",
                        value=total if total > 0 else 0,
                        metric_type="histogram",
                        tags={
                            "middleware": mw,
                            "action_type": action_type,
                            "status": status,
                        },
                    ))
                else:
                    # 同步上下文，用 _run_async 或跳过
                    pass
            except Exception:
                pass

    def pipeline_total(self, total: float, action_type: str, text: str):
        """记录整条管线总耗时"""
        msg = f"[Timer] Pipeline TOTAL: {total:.3f}s | action={action_type} text={text[:40]}"
        self._write_log(msg)

        # 上报 metrics
        if self._have_obs:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._obs_module.record_metric(
                        name="pipeline.total.duration",
                        value=total,
                        metric_type="histogram",
                        tags={"action_type": action_type},
                    ))
                except RuntimeError:
                    pass  # 同步上下文，跳过 async metric
            except Exception:
                pass

    def agent_turn(self, ctx, paradigm: str, turns: int, tool_calls: int):
        """记录 Agent Loop 的 turn 信息"""
        msg = (f"[Agent] paradigm={paradigm} turns={turns} "
               f"tool_calls={tool_calls} action={ctx.action_type}")
        self._write_log(msg)

        if self._have_obs:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._obs_module.record_metric(
                        name="pipeline.agent.turns",
                        value=float(turns),
                        metric_type="histogram",
                        tags={
                            "paradigm": paradigm,
                            "action_type": ctx.action_type,
                            "tool_calls": str(tool_calls),
                        },
                    ))
                except RuntimeError:
                    pass  # 同步上下文，跳过 async metric
            except Exception:
                pass

    def ai_response(self, session_id: str, content: str, *,
                    paradigm: str = "llm", chunk_count: int = 0,
                    elapsed_ms: Optional[float] = None, caller_id: Optional[int] = None,
                    action_type: str = "default"):
        """记录 AI 回复内容到日志系统。

        - stderr: 输出摘要（前 120 字符 + 统计信息）
        - SQLite data_json: 存储完整回复内容，可按 session_id 检索

        Args:
            session_id: 会话 ID
            content: AI 回复完整文本
            paradigm: 范式（llm / one_shot / plan_solve / plan_react）
            chunk_count: 流式 chunk 数
            elapsed_ms: 回复耗时（毫秒）
            caller_id: 调用者 ID
            action_type: 动作类型（chat/translate/coding/...）
        """
        import json as _json
        chars = len(content)
        preview = content[:120].replace('\n', '\\n')

        # stderr 摘要
        msg = (f"[AI_RESPONSE] session={session_id[:8]} | action={action_type} paradigm={paradigm} "
               f"| chunks={chunk_count} chars={chars} | {preview}...")
        sys.stderr.write(f"{self._thread_tag()} {msg}\n")
        sys.stderr.flush()

        # SQLite 完整记录（内容存入 data_json）
        try:
            store = self._get_log_store()
            store.insert(
                session_id=session_id,
                caller_id=caller_id,
                event="AI_RESPONSE",
                source="LLM",
                level="INFO",
                message=f"paradigm={paradigm} chunks={chunk_count} chars={chars}",
                chunk_count=chunk_count,
                elapsed_ms=elapsed_ms,
                data_json=_json.dumps({"content": content, "chars": chars, "paradigm": paradigm},
                                      ensure_ascii=False),
            )
        except Exception:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()

    # ---- 跨模块 Boundary 日志（供 GUI/Worker/Caller 调用） ----

    def caller_log(self, caller_id: int, msg: str, *, session_id: str = "", **kwargs):
        """Caller 层边界日志"""
        self._write_log(
            f"[Caller#{caller_id}] {msg}",
            source="Caller", session_id=session_id,
            caller_id=caller_id, **kwargs,
        )

    def worker_log(self, worker_id: int, worker_type: str, msg: str, *,
                   session_id: str = "", **kwargs):
        """Worker 层边界日志"""
        self._write_log(
            f"[{worker_type}#{worker_id}] {msg}",
            source="Worker", session_id=session_id,
            worker_id=worker_id, worker_type=worker_type, **kwargs,
        )

    def gui_log(self, msg: str, *, session_id: str = "", **kwargs):
        """GUI 层边界日志"""
        self._write_log(
            f"[GUI] {msg}",
            source="GUI", session_id=session_id, **kwargs,
        )

    # ---- 日志 ----

    def log(self, source: str, message: str, level: str = "info",
            *, session_id: str = "", event: str = "LOG",
            extra_data: Dict[str, Any] = None, **kwargs):
        """统一日志出口，支持结构化 extra_data 写入 data_json 字段"""
        import json as _json
        data_json = _json.dumps(extra_data, ensure_ascii=False) if extra_data else ""
        msg = f"[{source}] {message}"
        self._write_log(msg, source=source, level=level,
                        session_id=session_id, event=event,
                        data_json=data_json, **kwargs)
        if self._have_obs:
            try:
                getattr(self._obs_module, level)(
                    message, tags={"source": source}
                )
            except Exception:
                pass

    def error(self, source: str, message: str, exc_info: bool = False,
              *, session_id: str = "", **kwargs):
        """统一错误日志"""
        msg = f"[{source}] ERROR: {message}"
        self._write_log(msg, source=source, level="ERROR",
                        session_id=session_id, **kwargs)
        if self._have_obs:
            try:
                self._obs_module.error(message, tags={"source": source})
            except Exception:
                pass

    # ---- Metrics ----

    def metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录指标到 ObservabilityModule"""
        if self._have_obs:
            try:
                self._obs_module.record_metric(
                    name=name, value=value, tags=tags or {},
                )
            except Exception:
                pass

    # ---- 查询接口 ----

    def get_recent_timers(self, n: int = 10) -> List[TimerEntry]:
        """获取最近 N 条计时记录"""
        return self._timer_history[-n:]

    def get_timer_stats(self) -> Dict[str, Any]:
        """获取计时统计摘要"""
        if not self._timer_history:
            return {}
        by_mw = {}
        for e in self._timer_history:
            if e.name not in by_mw:
                by_mw[e.name] = {"count": 0, "total": 0.0, "min": float("inf"), "max": 0.0}
            b = by_mw[e.name]
            b["count"] += 1
            b["total"] += e.total
            b["min"] = min(b["min"], e.total)
            b["max"] = max(b["max"], e.total)
        for v in by_mw.values():
            v["avg"] = v["total"] / v["count"]
        return {
            "total_requests": len(self._timer_history),
            "middlewares": by_mw,
        }
