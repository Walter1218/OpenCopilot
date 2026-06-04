"""
统一 Agent Pipeline 调用器 —— OpenCopilot 唯一 AI 服务入口。

提供同步生成器和异步生成器两个接口，封装 PipelineContext 构建 +
pipeline.execute + SSE chunk 收集的完整链路。

同步版：供 QThread（AIWorker/ChatWorker）和 CLI 工具使用，通过内部线程桥接异步 Pipeline。
异步版：供 FastAPI 应用（smart_copilot_api.py、smart_copilot_platform.py）直接 await 使用。

用法：
    from opencopilot.agent.caller import call_agent_pipeline_sync, call_agent_pipeline_async

    # 同步生成器（QThread / CLI）
    for chunk in call_agent_pipeline_sync("你好", action_type="chat"):
        print(chunk, end="", flush=True)

    # 异步生成器（FastAPI）
    async for chunk in call_agent_pipeline_async("你好", action_type="chat"):
        yield chunk
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from queue import Queue as SyncQueue, Empty
from typing import Dict, Any, Optional, Generator, AsyncGenerator

from .pipeline import PipelineContext


def _get_pipeline():
    """延迟导入 Pipeline 实例，避免循环依赖."""
    import asu_custom_agent
    return asu_custom_agent.pipeline


def _load_ws_config() -> dict:
    """加载 Web Search 默认配置."""
    try:
        from llm_provider import load_config
        config = load_config()
        return config.get("web_search", {})
    except Exception:
        return {}


def _build_pipeline_context(
    text: str,
    action_type: str = "default",
    session_id: Optional[str] = None,
    context_source: str = "drag",
    context_meta: Optional[Dict[str, Any]] = None,
    context_envelope: Optional[Dict[str, Any]] = None,
    image_base64: Optional[str] = None,
    is_new_task: bool = True,
    enable_web_search: Optional[bool] = None,
    web_search_force: bool = False,
) -> PipelineContext:
    """构建 PipelineContext（内部工厂函数）"""
    ws_config = _load_ws_config()
    should_enable_ws = (
        enable_web_search if enable_web_search is not None
        else ws_config.get("enabled", False)
    )

    request = {
        "text": text,
        "context_source": context_source,
        "context_meta": context_meta or {},
    }

    ctx = PipelineContext(
        request=request,
        session_id=session_id or str(uuid.uuid4()),
        text=text,
        action_type=action_type,
        image_base64=image_base64,
        is_new_task=is_new_task,
        enable_web_search=should_enable_ws,
        web_search_force=web_search_force,
        web_search_max_keyword=ws_config.get("max_keyword", 3),
        web_search_limit=ws_config.get("limit", 3),
        web_search_user_location=ws_config.get("user_location"),
    )

    # context_envelope 通过 metadata 传递
    if context_envelope:
        ctx.metadata["context_envelope"] = context_envelope

    return ctx


def call_agent_pipeline_sync(
    text: str,
    action_type: str = "default",
    session_id: Optional[str] = None,
    context_source: str = "drag",
    context_meta: Optional[Dict[str, Any]] = None,
    context_envelope: Optional[Dict[str, Any]] = None,
    image_base64: Optional[str] = None,
    is_new_task: bool = True,
    enable_web_search: Optional[bool] = None,
    web_search_force: bool = False,
    timeout: float = 120.0,
) -> Generator[str, None, None]:
    """
    同步生成器版 Agent Pipeline 调用器。

    内部通过 daemon 线程桥接异步 Pipeline，chunk 实时 yield 保证流式输出。
    供 QThread（AIWorker/ChatWorker）和 CLI 工具使用。

    Args:
        text: 用户输入文本
        action_type: 动作类型（chat/coding/ppt/translate/...）
        session_id: 会话 ID，None 则自动生成
        context_source: 上下文来源（drag/ide/browser/file/chat）
        context_meta: 上下文元信息
        context_envelope: 上下文信封（IDE/文档全文+选中文本等）
        image_base64: 图片 Base64 编码
        is_new_task: 是否新任务（会影响会话记忆重置）
        enable_web_search: 是否开启联网搜索，None 从 config 读取
        web_search_force: 是否强制搜索
        timeout: 超时秒数

    Yields:
        str: SSE chunk 文本内容
    """
    chunk_queue: SyncQueue = SyncQueue()

    async def _run_pipeline():
        try:
            ctx = _build_pipeline_context(
                text=text,
                action_type=action_type,
                session_id=session_id,
                context_source=context_source,
                context_meta=context_meta,
                context_envelope=context_envelope,
                image_base64=image_base64,
                is_new_task=is_new_task,
                enable_web_search=enable_web_search,
                web_search_force=web_search_force,
            )

            async_queue: asyncio.Queue = asyncio.Queue()
            ctx.use_async_queue(async_queue)

            pipeline = _get_pipeline()
            pipeline_task = asyncio.create_task(pipeline.execute(ctx))

            done_received = False
            _start_time = time.time()
            while not done_received:
                try:
                    # 使用较短的超时，以便能及时检查 pipeline_task 是否已完成
                    line = await asyncio.wait_for(async_queue.get(), timeout=min(timeout, 5.0))
                except asyncio.TimeoutError:
                    # 检查总超时
                    if time.time() - _start_time > timeout:
                        chunk_queue.put(("error", "Agent 管线响应超时"))
                        chunk_queue.put(("done", None))
                        done_received = True
                        break
                    # 检查 pipeline 是否已经结束（例如 short_circuit 或异常）
                    if pipeline_task.done():
                        # Pipeline 已结束但队列没有 DONE 信号，处理 short_circuit
                        if ctx.should_short_circuit and ctx.response_content:
                            chunk_queue.put(("chunk", ctx.response_content))
                        elif pipeline_task.exception():
                            chunk_queue.put(("error", str(pipeline_task.exception())))
                        chunk_queue.put(("done", None))
                        done_received = True
                        break
                    # Pipeline 仍在运行，继续等待
                    continue

                if line == "data: [DONE]\n\n":
                    chunk_queue.put(("done", None))
                    done_received = True
                    break
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        chunk = data.get("chunk", "")
                        if chunk:
                            chunk_queue.put(("chunk", chunk))
                    except json.JSONDecodeError:
                        pass

            try:
                await asyncio.wait_for(pipeline_task, timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                pass

        except Exception as e:
            chunk_queue.put(("error", str(e)))
            chunk_queue.put(("done", None))

    thread = threading.Thread(target=lambda: asyncio.run(_run_pipeline()), daemon=True)
    thread.start()

    while True:
        try:
            msg_type, msg = chunk_queue.get(timeout=timeout + 10)
        except Empty:
            yield "\n[错误]: Agent 管线无响应（消费者超时）"
            break
        if msg_type == "done":
            break
        elif msg_type == "error":
            yield f"\n[错误]: {msg}"
            break
        elif msg_type == "chunk":
            yield msg

    thread.join(timeout=10)


async def call_agent_pipeline_async(
    text: str,
    action_type: str = "default",
    session_id: Optional[str] = None,
    context_source: str = "chat",
    context_meta: Optional[Dict[str, Any]] = None,
    context_envelope: Optional[Dict[str, Any]] = None,
    image_base64: Optional[str] = None,
    is_new_task: bool = True,
    enable_web_search: Optional[bool] = None,
    web_search_force: bool = False,
    timeout: float = 120.0,
) -> AsyncGenerator[str, None]:
    """
    异步生成器版 Agent Pipeline 调用器。

    供 FastAPI 应用（smart_copilot_api.py、smart_copilot_platform.py）直接 await 使用。
    调用方可以根据需要在外部添加 lane semaphore 等并发控制。

    Args:
        text: 用户输入文本
        action_type: 动作类型
        session_id: 会话 ID
        context_source: 上下文来源
        context_meta: 上下文元信息
        context_envelope: 上下文信封
        image_base64: 图片 Base64
        is_new_task: 是否新任务
        enable_web_search: 是否开启联网搜索
        web_search_force: 是否强制搜索
        timeout: 超时秒数

    Yields:
        str: SSE chunk 文本内容
    """
    ctx = _build_pipeline_context(
        text=text,
        action_type=action_type,
        session_id=session_id,
        context_source=context_source,
        context_meta=context_meta,
        context_envelope=context_envelope,
        image_base64=image_base64,
        is_new_task=is_new_task,
        enable_web_search=enable_web_search,
        web_search_force=web_search_force,
    )

    async_queue: asyncio.Queue = asyncio.Queue()
    ctx.use_async_queue(async_queue)

    pipeline = _get_pipeline()
    pipeline_task = asyncio.create_task(pipeline.execute(ctx))

    try:
        while True:
            try:
                line = await asyncio.wait_for(async_queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                yield f"\n[错误]: Agent 管线响应超时"
                break

            if line == "data: [DONE]\n\n":
                break
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                    chunk = data.get("chunk", "")
                    if chunk:
                        yield chunk
                except json.JSONDecodeError:
                    pass

        await pipeline_task

        # 修复：short_circuit 时 awrite_sse_done() 不会被调用，导致消费者永久阻塞
        if ctx.should_short_circuit and ctx.response_content:
            yield ctx.response_content

    except Exception as e:
        yield f"\n[错误]: {str(e)}"
