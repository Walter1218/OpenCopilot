import json
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List, AsyncGenerator
from abc import ABC, abstractmethod

from .observability import PipelineObservability


@dataclass
class PipelineContext:
    request: Dict[str, Any]
    session_id: str
    text: str
    action_type: str = "default"
    persona: str = "default"
    persona_prompt: str = ""
    enriched_system: str = ""
    messages: List[Dict] = field(default_factory=list)
    image_base64: Optional[str] = None
    is_new_task: bool = False
    user_message_content: Any = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    response_content: Optional[str] = None
    should_short_circuit: bool = False

    stream_writer: Optional[Callable] = None
    http_headers_sent: bool = False

    # 异步 SSE 输出 (FastAPI 内嵌模式)
    _async_queue: Optional[asyncio.Queue] = None

    # Web Search 联网搜索配置
    enable_web_search: bool = False
    web_search_force: bool = False
    web_search_max_keyword: int = 3
    web_search_limit: int = 3
    web_search_user_location: Optional[Dict] = None
    web_search_annotations: List[Dict] = field(default_factory=list)  # 搜索来源引用

    # 追踪信息
    trace_id: Optional[str] = None
    _span_stack: List[str] = field(default_factory=list)

    def use_async_queue(self, queue: asyncio.Queue):
        """切换到异步队列模式（FastAPI 内嵌）"""
        self._async_queue = queue

    def write_sse(self, chunk: str):
        if self.stream_writer:
            data = json.dumps({"chunk": chunk}, ensure_ascii=False)
            self.stream_writer.write(f"data: {data}\n\n".encode("utf-8"))

    def write_sse_done(self):
        if self.stream_writer:
            self.stream_writer.write(b"data: [DONE]\n\n")

    def write_sse_annotations(self, annotations: list):
        """发送 web search 搜索来源引用"""
        if self.stream_writer and annotations:
            data = json.dumps({"annotations": annotations}, ensure_ascii=False)
            self.stream_writer.write(f"data: {data}\n\n".encode("utf-8"))

    async def awrite_sse(self, chunk: str):
        """异步 SSE 写入（FastAPI 模式）"""
        if self._async_queue is not None:
            data = json.dumps({"chunk": chunk}, ensure_ascii=False)
            await self._async_queue.put(f"data: {data}\n\n")

    async def awrite_sse_done(self):
        """异步 SSE 完成信号"""
        if self._async_queue is not None:
            await self._async_queue.put("data: [DONE]\n\n")

    async def awrite_sse_annotations(self, annotations: list):
        """异步发送 web search 来源引用"""
        if self._async_queue is not None and annotations:
            data = json.dumps({"annotations": annotations}, ensure_ascii=False)
            await self._async_queue.put(f"data: {data}\n\n")

    def short_circuit(self, content: str):
        self.response_content = content
        self.should_short_circuit = True

    def send_http_headers(self):
        handler = self.metadata.get("_handler")
        if handler and not self.http_headers_sent:
            handler.send_response(200)
            handler.send_header("Content-Type", "text/event-stream")
            handler.send_header("Cache-Control", "no-cache")
            handler.send_header("Connection", "keep-alive")
            handler.end_headers()
            self.http_headers_sent = True


class BaseMiddleware(ABC):

    @abstractmethod
    async def process(self, ctx: PipelineContext, next_fn: Callable[[], object]) -> None:
        """
        异步处理管线节点。

        Args:
            ctx: 管线上下文
            next_fn: 调用下一个中间件的异步回调 (callable, not awaitable)
        """
        pass


class MiddlewarePipeline:
    """中间件管线

    支持自动追踪：当注入 tracer 后，execute() 会为整条管线创建 Trace，
    为每个中间件创建 Span，记录执行耗时和状态。

    异步模式：在 FastAPI/uvicorn 事件循环中直接运行，支持高并发。
    """

    def __init__(self, tracer=None):
        self._middlewares: List[BaseMiddleware] = []
        self._tracer = tracer

    def use(self, middleware: BaseMiddleware) -> "MiddlewarePipeline":
        self._middlewares.append(middleware)
        return self

    def set_tracer(self, tracer):
        """注入分布式追踪器"""
        self._tracer = tracer

    async def execute(self, ctx: PipelineContext) -> None:
        """异步执行管线（FastAPI 内嵌模式）"""
        # 启动 Trace
        trace = None
        if self._tracer:
            trace = self._tracer.start_trace(
                operation="pipeline.execute",
                tags={
                    "action_type": ctx.action_type,
                    "session_id": ctx.session_id,
                    "text_preview": ctx.text[:80] if ctx.text else "",
                },
            )
            ctx.trace_id = trace.trace_id

        obs = PipelineObservability.get_instance()
        mws = self._middlewares
        _t_pipeline_start = time.time()

        async def dispatch(i: int):
            if i >= len(mws) or ctx.should_short_circuit:
                if ctx.should_short_circuit and i < len(mws):
                    # 记录是哪个中间件触发了 short_circuit
                    blocker = mws[i - 1].__class__.__name__ if i > 0 else "unknown"
                    obs.log(
                        "Pipeline", f"Short-circuited by {blocker} at step {i}",
                        session_id=ctx.session_id, level="WARNING",
                        event="PIPELINE_SHORT_CIRCUIT",
                        extra_data={
                            "blocker": blocker,
                            "action_type": ctx.action_type,
                            "response_preview": (ctx.response_content or "")[:100],
                        },
                    )
                return

            mw_name = mws[i].__class__.__name__

            # 为每个中间件创建 Span（通过 ObservabilityModule）
            span = None
            if self._tracer and trace:
                span = self._tracer.start_span(
                    trace_id=trace.trace_id,
                    operation=f"middleware.{mw_name}",
                    parent_id=ctx._span_stack[-1] if ctx._span_stack else None,
                    tags={"action_type": ctx.action_type},
                )
                ctx._span_stack.append(span.span_id)

            _t_mw_start = time.time()
            try:
                await mws[i].process(ctx, lambda: dispatch(i + 1))
            except Exception as e:
                if span:
                    self._tracer.finish_span(span.span_id, "error")
                if ctx._span_stack and span and ctx._span_stack[-1] == span.span_id:
                    ctx._span_stack.pop()
                obs.timer(mw_name, time.time() - _t_mw_start,
                          action_type=ctx.action_type, status="error")
                obs.error("Pipeline", f"Middleware {mw_name} failed: {e}")
                raise
            else:
                if span:
                    self._tracer.finish_span(span.span_id)
                if ctx._span_stack and span and ctx._span_stack[-1] == span.span_id:
                    ctx._span_stack.pop()

            _t_mw_elapsed = time.time() - _t_mw_start
            obs.timer(mw_name, _t_mw_elapsed,
                      action_type=ctx.action_type,
                      session_id=ctx.session_id)

        await dispatch(0)

        # 完成 Trace
        if self._tracer and trace:
            status = "ok"
            if ctx.should_short_circuit:
                status = "short_circuit"
            self._tracer.finish_trace(trace.trace_id, status)

        _t_total = time.time() - _t_pipeline_start
        obs.pipeline_total(_t_total, ctx.action_type, ctx.text)
