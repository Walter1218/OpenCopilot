import json
import time
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from abc import ABC, abstractmethod

# 计时日志文件（追加写入）
_TIMER_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline_timer.log")

def _timer_log(msg: str):
    """写入计时日志到文件和 stdout"""
    print(msg, flush=True)
    try:
        with open(_TIMER_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


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
    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        pass


class MiddlewarePipeline:
    """中间件管线

    支持自动追踪：当注入 tracer 后，execute() 会为整条管线创建 Trace，
    为每个中间件创建 Span，记录执行耗时和状态。
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

    def execute(self, ctx: PipelineContext) -> None:
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

        mws = self._middlewares
        _t_pipeline_start = time.time()

        def dispatch(i: int):
            if i >= len(mws) or ctx.should_short_circuit:
                return

            mw_name = mws[i].__class__.__name__

            # 为每个中间件创建 Span
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
                mws[i].process(ctx, lambda: dispatch(i + 1))
            except Exception as e:
                if span:
                    self._tracer.finish_span(span.span_id, "error")
                if ctx._span_stack and span and ctx._span_stack[-1] == span.span_id:
                    ctx._span_stack.pop()
                raise
            else:
                if span:
                    self._tracer.finish_span(span.span_id)
                if ctx._span_stack and span and ctx._span_stack[-1] == span.span_id:
                    ctx._span_stack.pop()

            _t_mw_elapsed = time.time() - _t_mw_start
            _timer_log(f"[Timer] Pipeline.{mw_name}: {_t_mw_elapsed:.3f}s (cumulative={time.time()-_t_pipeline_start:.3f}s)")

        dispatch(0)

        # 完成 Trace
        if self._tracer and trace:
            status = "ok"
            if ctx.should_short_circuit:
                status = "short_circuit"
            self._tracer.finish_trace(trace.trace_id, status)

        _timer_log(f"[Timer] Pipeline TOTAL: {time.time()-_t_pipeline_start:.3f}s | action={ctx.action_type} text={ctx.text[:40]}")
