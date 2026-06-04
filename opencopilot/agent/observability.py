"""
管线统——可观测性模块

解决三套割裂的追踪/日志系统：
  1. 消除 _timer_log() 在 pipeline.py 和 middlewares.py 中重复定义
  2. 将 [Timer] 埋点接入 ObservabilityModule 的 Metrics + Tracer
  3. 提供统一的 structured logging 出口

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
from dataclasses import field, dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path


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
    自动检测 ObservabilityModule 是否可用，不可用时降级为纯文件日志。
    """

    _instance: Optional["PipelineObservability"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._timer_log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pipeline_timer.log"
        )
        self._obs = None           # ObservabilityModule 实例
        self._timer_history: List[TimerEntry] = []  # 最近 100 条计时记录
        self._max_history = 100

        # 尝试导入 ObservabilityModule
        try:
            from opencopilot.observability import (
                ObservabilityModule, ObservabilityConfig, LogLevel,
            )
            # 不创建新的 ObservabilityModule 实例，而是从 asu_custom_agent 获取已存在的
            # 如果获取失败，降级为独立实例
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
            # 从消息中提取 middleware 名称用于 metrics
            try:
                rest = raw_msg[len("[Timer] "):]
                mw = rest.split(":")[0].strip()
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

        # stdout
        print(msg, flush=True)

        # 文件
        try:
            with open(self._timer_log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

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
        print(msg, flush=True)
        try:
            with open(self._timer_log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def agent_turn(self, ctx, paradigm: str, turns: int, tool_calls: int):
        """记录 Agent Loop 的 turn 信息"""
        msg = (f"[Agent] paradigm={paradigm} turns={turns} "
               f"tool_calls={tool_calls} action={ctx.action_type}")
        print(msg, flush=True)
        try:
            with open(self._timer_log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

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

    # ---- 日志 ----

    def log(self, source: str, message: str, level: str = "info"):
        """统一日志出口"""
        print(f"[{source}] {message}", flush=True)
        if self._have_obs:
            try:
                getattr(self._obs_module, level)(
                    message, tags={"source": source}
                )
            except Exception:
                pass

    def error(self, source: str, message: str, exc_info: bool = False):
        """统一错误日志"""
        print(f"[{source}] ERROR: {message}", flush=True)
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
