"""
统一 Agent Pipeline 调用器 —— OpenCopilot 唯一 AI 服务入口。

提供同步生成器和异步生成器两个接口，封装 PipelineContext 构建 +
pipeline.execute + SSE chunk 收集的完整链路。

同步版：供 QThread（AIWorker/ChatWorker）和 CLI 工具使用。
        通过全局持久化事件循环 + asyncio.run_coroutine_threadsafe 桥接异步 Pipeline。
        取消通过 task.cancel() 传播 CancelledError，无需硬超时暴力截断。
异步版：供 FastAPI 应用（smart_copilot_api.py、smart_copilot_platform.py）直接 await 使用。

架构洞察（参考 OpenClaw）：不应为每次调用创建新的 daemon 线程 + 独立 event loop，
而应使用全局持久化 event loop，配合 asyncio task 管理实现干净的生命周期控制。

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


# ═══════════════════════════════════════════════════════════════════
# 全局单例事件循环桥（替代 per-call daemon 线程）
# ═══════════════════════════════════════════════════════════════════
#
# OpenClaw 的关键设计洞察：
#   1. 使用单进程持久化 event loop（run_forever），而非 per-call daemon 线程
#   2. 会话级序列化锁确保同一 session 同时只有一个 run
#   3. 取消通过 AbortSignal（等效于 asyncio task.cancel()），干净传播 CancelledError
#   4. 全链路 async/await，无需 sync/async 桥接层
#
# OpenCopilot 的适配：
#   - PyQt QThread 是同步世界，必须架桥
#   - 全局持久化 loop + run_coroutine_threadsafe 是最小侵入的桥接方案
#   - 取消通过 threading.Event → task.cancel()，CancelledError 沿 async 栈传播
#   - 会话级 asyncio.Lock 确保同一 session 同时只有一个 pipeline（防止数据竞争/"重复回复"）

class _EventLoopBridge:
    """持久化事件循环桥 —— 全进程共享一个 event loop 线程。

    与 per-call daemon 线程方案的根本区别：
    - 旧方案：每调用创建一个 daemon 线程 + 独立 loop，旧线程靠 5s 硬超时杀死
    - 新方案：全进程一个持久化 loop，任务通过 run_coroutine_threadsafe 提交，
     取消通过 task.cancel() 传播 CancelledError，无需硬超时

    daemon=True 确保进程退出时不阻塞；run_forever 确保 loop 持续接受新任务。
    """
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _thread: Optional[threading.Thread] = None
    _lock = threading.Lock()

    @classmethod
    def get_loop(cls) -> asyncio.AbstractEventLoop:
        """获取（或创建）全局持久化 event loop。线程安全。"""
        if cls._loop is None or cls._loop.is_closed():
            with cls._lock:
                if cls._loop is None or cls._loop.is_closed():
                    cls._loop = asyncio.new_event_loop()
                    cls._thread = threading.Thread(
                        target=cls._loop.run_forever,
                        daemon=True,
                        name="pipeline-event-loop",
                    )
                    cls._thread.start()
        return cls._loop

    @classmethod
    def shutdown(cls, timeout: float = 3.0):
        """优雅关闭 event loop（进程退出时调用）。"""
        if cls._loop is not None and not cls._loop.is_closed():
            cls._loop.call_soon_threadsafe(cls._loop.stop)
            if cls._thread is not None and cls._thread.is_alive():
                cls._thread.join(timeout=timeout)
            try:
                cls._loop.close()
            except Exception:
                pass
            cls._loop = None
            cls._thread = None


# ═══════════════════════════════════════════════════════════════════
# 会话级序列化锁（OpenClaw 风格：同一 session 排队串行）
# ═══════════════════════════════════════════════════════════════════
# 防止同一 session 的多个 pipeline 并发执行导致的数据竞争（"重复回复"的根源）。
# asyncio.Lock 在 pending 时释放事件循环，不会阻塞其他 session 的 pipeline。
_session_locks: Dict[str, asyncio.Lock] = {}
_session_locks_guard = threading.Lock()
_session_locks_max_size = 500  # 上限：超限时清理最旧的条目


def _get_or_create_session_lock(session_id: str) -> asyncio.Lock:
    """获取或创建会话级 asyncio.Lock（线程安全）。内置 LRU 淘汰防止内存无限增长。"""
    with _session_locks_guard:
        if session_id not in _session_locks:
            # 超限清理：删除最旧的 N 个条目
            if len(_session_locks) >= _session_locks_max_size:
                overflow = len(_session_locks) - _session_locks_max_size + 1
                # 迭代字典取前 N 个 key（Python 3.7+ 字典保序）
                oldest_keys = list(_session_locks.keys())[:overflow]
                for key in oldest_keys:
                    del _session_locks[key]
            _session_locks[session_id] = asyncio.Lock()
        return _session_locks[session_id]


def _get_session_lock_count() -> int:
    """返回当前缓存的会话锁数量（调试用）。"""
    with _session_locks_guard:
        return len(_session_locks)


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
        "context_envelope": context_envelope or {},
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

    # 兼容旧链路：metadata 中也保留一份，便于已有中间件/调试逻辑读取
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
    cancel_event: Optional[threading.Event] = None,
) -> Generator[str, None, None]:
    """
    同步生成器版 Agent Pipeline 调用器。

    通过全局持久化事件循环 + asyncio.run_coroutine_threadsafe 桥接异步 Pipeline，
    chunk 实时 yield 保证流式输出。供 QThread（AIWorker/ChatWorker）和 CLI 工具使用。

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
        cancel_event: 取消事件，设置后通过 task.cancel() 传播 CancelledError 终止管线

    Yields:
        str: SSE chunk 文本内容
    """
    from .observability import PipelineObservability
    obs = PipelineObservability.get_instance()

    # 唯一 caller ID（进程级自增）
    if not hasattr(call_agent_pipeline_sync, '_next_caller_id'):
        call_agent_pipeline_sync._next_caller_id = 0
    call_agent_pipeline_sync._next_caller_id += 1
    caller_id = call_agent_pipeline_sync._next_caller_id

    result_session_id = session_id or str(uuid.uuid4())
    obs.caller_log(caller_id, f"SYNC_START | text={text[:40]} | action={action_type}",
                   session_id=result_session_id, event="SYNC_START")

    chunk_queue: SyncQueue = SyncQueue()
    _cancelled = cancel_event if cancel_event else threading.Event()
    # 使用可变对象存储 chunk 计数，避免闭包生命周期问题
    # 当异步协程在事件循环中执行时，外层函数可能已返回，nonlocal 变量会被垃圾回收
    _chunk_counter = [0]

    # ---- 管线协程（运行在全局持久化 event loop 中） ----
    async def _run_pipeline():
        session_lock = _get_or_create_session_lock(result_session_id)
        # 会话锁：确保同一 session 同时只有一个 pipeline，防止数据竞争和"重复回复"
        async with session_lock:
            obs.caller_log(caller_id, "PIPELINE_START", session_id=result_session_id, event="START")
            pipeline_task = None
            try:
                ctx = _build_pipeline_context(
                    text=text, action_type=action_type, session_id=session_id,
                    context_source=context_source, context_meta=context_meta,
                    context_envelope=context_envelope, image_base64=image_base64,
                    is_new_task=is_new_task,
                    enable_web_search=enable_web_search, web_search_force=web_search_force,
                )

                async_queue: asyncio.Queue = asyncio.Queue()
                ctx.use_async_queue(async_queue)

                pipeline = _get_pipeline()
                pipeline_task = asyncio.create_task(pipeline.execute(ctx))

                done_received = False
                _start_time = time.time()
                while not done_received:
                    # 检查取消信号（由 ChatWorker.stop() → cancel_event.set() 触发）
                    if _cancelled.is_set():
                        pipeline_task.cancel()
                        done_received = True
                        break

                    try:
                        line = await asyncio.wait_for(async_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # 1秒超时检查取消信号和总超时
                        if _cancelled.is_set():
                            pipeline_task.cancel()
                            done_received = True
                            break
                        if time.time() - _start_time > timeout:
                            pipeline_task.cancel()
                            chunk_queue.put(("error", "Agent 管线响应超时"))
                            chunk_queue.put(("done", None))
                            done_received = True
                            break
                        if pipeline_task.done():
                            if pipeline_task.exception():
                                chunk_queue.put(("error", str(pipeline_task.exception())))
                            elif ctx.should_short_circuit and ctx.response_content:
                                chunk_queue.put(("chunk", ctx.response_content))
                            chunk_queue.put(("done", None))
                            done_received = True
                            break
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
                                _chunk_counter[0] += 1
                                chunk_queue.put(("chunk", chunk))
                        except json.JSONDecodeError:
                            pass

                # 等待 pipeline task 完成（给清理留 1.5 秒窗口）
                if pipeline_task and not pipeline_task.done():
                    try:
                        await asyncio.wait_for(pipeline_task, timeout=1.5)
                    except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                        pass

                obs.caller_log(caller_id, f"PIPELINE_DONE | chunks={_chunk_counter[0]}",
                               session_id=result_session_id, event="DONE", chunk_count=_chunk_counter[0])

            except asyncio.CancelledError:
                obs.caller_log(caller_id, "PIPELINE_CANCELLED",
                               session_id=result_session_id, event="CANCELLED")
            except Exception as e:
                obs.caller_log(caller_id, f"PIPELINE_ERROR | {e}",
                               session_id=result_session_id, event="ERROR", level="ERROR")
                chunk_queue.put(("error", str(e)))
            finally:
                # 确保 consumer 不会永远阻塞
                chunk_queue.put(("done", None))

    # ---- 提交到全局持久化 event loop（替代 per-call daemon 线程） ----
    loop = _EventLoopBridge.get_loop()
    future = asyncio.run_coroutine_threadsafe(_run_pipeline(), loop)

    # ---- 消费者循环：从 chunk_queue 读取 chunk/error/done ----
    try:
        while True:
            if _cancelled.is_set():
                obs.caller_log(caller_id, f"SYNC_CANCELLED | chunks={_chunk_counter[0]}",
                               session_id=result_session_id, event="CANCELLED", chunk_count=_chunk_counter[0])
                future.cancel()
                break

            try:
                msg_type, msg = chunk_queue.get(timeout=0.5)
            except Empty:
                if future.done():
                    exc = future.exception()
                    if exc:
                        yield f"\n[错误]: {exc}"
                    break
                continue

            if msg_type == "done":
                break
            elif msg_type == "error":
                yield f"\n[错误]: {msg}"
                break
            elif msg_type == "chunk":
                yield msg
    finally:
        # 确保管线任务被取消（不影响已完成的任务）
        _cancelled.set()
        if not future.done():
            future.cancel()
        obs.caller_log(caller_id, f"SYNC_END | chunks={_chunk_counter[0]}",
                       session_id=result_session_id, event="SYNC_END", chunk_count=_chunk_counter[0])


async def call_agent_pipeline_async(
    text: str,
    action_type: str = "default",
    session_id: Optional[str] = None,
    context_source: str = "chat",
    context_meta: Optional[Dict[str, Any]] = None,
    context_envelope: Optional[Dict[str, Any]] = None,
    image_base64: Optional[str] = None,
    is_new_task: bool = False,
    enable_web_search: Optional[bool] = None,
    web_search_force: bool = False,
    timeout: float = 120.0,
) -> AsyncGenerator[str, None]:
    """
    异步生成器版 Agent Pipeline 调用器。

    供 FastAPI 应用（smart_copilot_api.py、smart_copilot_platform.py）直接 await 使用。
    会话锁确保同一 session 同时只有一个 pipeline 运行（防止数据竞争和"重复回复"）。

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
    from .observability import PipelineObservability
    obs = PipelineObservability.get_instance()

    # 唯一 caller ID（进程级自增）
    if not hasattr(call_agent_pipeline_async, '_next_caller_id'):
        call_agent_pipeline_async._next_caller_id = 0
    call_agent_pipeline_async._next_caller_id += 1
    caller_id = call_agent_pipeline_async._next_caller_id

    result_session_id = session_id or str(uuid.uuid4())
    obs.caller_log(caller_id, f"ASYNC_START | text={text[:40]} | action={action_type}",
                   session_id=result_session_id, event="ASYNC_START")

    _chunk_count = 0

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

    # 会话锁：确保同一 session 同时只有一个 pipeline，防止数据竞争和"重复回复"
    session_lock = _get_or_create_session_lock(result_session_id)
    async with session_lock:
        obs.caller_log(caller_id, "PIPELINE_START", session_id=result_session_id, event="START")

        pipeline = _get_pipeline()
        pipeline_task = asyncio.create_task(pipeline.execute(ctx))

        try:
            _start_time = time.time()
            while True:
                try:
                    line = await asyncio.wait_for(async_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if time.time() - _start_time > timeout:
                        pipeline_task.cancel()
                        obs.caller_log(caller_id, "PIPELINE_TIMEOUT",
                                       session_id=result_session_id, event="TIMEOUT", level="WARN")
                        yield f"\n[错误]: Agent 管线响应超时"
                        break
                    if pipeline_task.done():
                        if pipeline_task.exception():
                            obs.caller_log(caller_id, f"PIPELINE_TASK_ERROR | {pipeline_task.exception()}",
                                           session_id=result_session_id, event="ERROR", level="ERROR")
                            yield f"\n[错误]: {pipeline_task.exception()}"
                        elif ctx.should_short_circuit and ctx.response_content:
                            yield ctx.response_content
                        break
                    continue

                if line == "data: [DONE]\n\n":
                    break
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        chunk = data.get("chunk", "")
                        if chunk:
                            _chunk_count += 1
                            yield chunk
                    except json.JSONDecodeError:
                        pass

            # 等待 pipeline task 完成（给清理留 1.5 秒窗口）
            if pipeline_task and not pipeline_task.done():
                try:
                    await asyncio.wait_for(pipeline_task, timeout=1.5)
                except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                    pass

            obs.caller_log(caller_id, f"PIPELINE_DONE | chunks={_chunk_count}",
                           session_id=result_session_id, event="DONE", chunk_count=_chunk_count)

            # short_circuit 内容（在 session_lock 内 yield 确保安全）
            if ctx.should_short_circuit and ctx.response_content:
                yield ctx.response_content

        except asyncio.CancelledError:
            obs.caller_log(caller_id, "PIPELINE_CANCELLED",
                           session_id=result_session_id, event="CANCELLED")
            yield f"\n[错误]: 请求已取消"
        except Exception as e:
            obs.caller_log(caller_id, f"PIPELINE_ERROR | {e}",
                           session_id=result_session_id, event="ERROR", level="ERROR")
            yield f"\n[错误]: {str(e)}"

    obs.caller_log(caller_id, f"ASYNC_END | chunks={_chunk_count}",
                   session_id=result_session_id, event="ASYNC_END", chunk_count=_chunk_count)
