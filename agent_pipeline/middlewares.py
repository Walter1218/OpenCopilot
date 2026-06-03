import json
import time
import os
import traceback
from typing import Dict, Any, Optional, Callable

from .pipeline import BaseMiddleware, PipelineContext

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


class SessionSetupMiddleware(BaseMiddleware):

    def __init__(
        self,
        memory,
        window_manager,
        normalize_context_envelope: Callable,
        load_persona: Callable,
        build_context_prefix: Callable,
        sanitize_persona_for_context: Callable,
    ):
        self._memory = memory
        self._window_manager = window_manager
        self._normalize_context_envelope = normalize_context_envelope
        self._load_persona = load_persona
        self._build_context_prefix = build_context_prefix
        self._sanitize_persona_for_context = sanitize_persona_for_context

    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        _t0 = time.time()
        try:
            req = ctx.request
            text = ctx.text
            session_id = ctx.session_id
            is_new_task = ctx.is_new_task

            _t1 = time.time()
            context_source = req.get("context_source", "drag")
            context_meta = req.get("context_meta", {})
            envelope = self._normalize_context_envelope(req, text, context_source, context_meta)
            _t_norm = time.time() - _t1

            _t2 = time.time()
            if is_new_task:
                self._memory.clear(session_id)
                self._memory.set_persona(session_id, ctx.action_type)

            # 当 action_type 非 default 时，更新 persona 以确保正确的角色切换
            chat_ctx = self._memory.get_context(session_id)
            if ctx.action_type != "default" and chat_ctx.get("persona") != ctx.action_type:
                self._memory.set_persona(session_id, ctx.action_type)
                chat_ctx = self._memory.get_context(session_id)
            _t_mem = time.time() - _t2

            _t3 = time.time()
            ctx.persona = chat_ctx["persona"]
            persona_prompt = self._load_persona(ctx.persona)
            _t_persona = time.time() - _t3

            _t4 = time.time()
            source = envelope.get("source", "drag")
            context_prefix = self._build_context_prefix(source, envelope.get("meta", {}))
            persona_prompt = self._sanitize_persona_for_context(persona_prompt, source)

            if context_prefix:
                ctx.enriched_system = f"{context_prefix}\n\n{persona_prompt}"
            else:
                ctx.enriched_system = persona_prompt
            _t_prefix = time.time() - _t4

            _t5 = time.time()
            ctx.messages = self._window_manager.build_messages(
                system_prompt=ctx.enriched_system,
                envelope=envelope,
                history_messages=chat_ctx["messages"],
            )
            _t_build = time.time() - _t5

            image_base64 = req.get("image_base64")
            if image_base64:
                ctx.image_base64 = image_base64
                last_msg = ctx.messages[-1]
                last_msg["content"] = [
                    {"type": "text", "text": last_msg["content"]},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                ]

            user_content = envelope.get("content", text)
            user_message_content = []
            if user_content:
                user_message_content.append({"type": "text", "text": user_content})
            if image_base64:
                user_message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                })
            if not user_message_content:
                user_message_content.append({"type": "text", "text": "你好"})

            ctx.user_message_content = (
                json.dumps(user_message_content, ensure_ascii=False)
                if len(user_message_content) > 1
                else user_message_content[0]["text"]
            )

            self._memory.add_message(session_id, "user", ctx.user_message_content)

            _timer_log(f"[Timer] SessionSetup: total={time.time()-_t0:.3f}s | norm={_t_norm:.3f} mem={_t_mem:.3f} persona={_t_persona:.3f} prefix={_t_prefix:.3f} build={_t_build:.3f}")
        except Exception as e:
            print(f"[Pipeline] SessionSetup error: {e}", flush=True)
            traceback.print_exc()

        next_fn()


class SecurityGuardMiddleware(BaseMiddleware):

    def __init__(self, security_module):
        self._security = security_module
        self._initialized_users = set()

    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        _t0 = time.time()
        try:
            import asyncio

            _t1 = time.time()
            allowed = asyncio.run(
                self._security.check_permission(
                    user_id=ctx.session_id,
                    resource="agent.chat",
                    action="execute",
                )
            )
            _t_perm = time.time() - _t1

            if not allowed:
                if ctx.session_id not in self._initialized_users:
                    self._init_user(ctx.session_id)
                    _t2 = time.time()
                    allowed = asyncio.run(
                        self._security.check_permission(
                            user_id=ctx.session_id,
                            resource="agent.chat",
                            action="execute",
                        )
                    )
                    _t_perm2 = time.time() - _t2
            if not allowed:
                ctx.short_circuit("❌ 权限不足，请求被拦截。")
                _timer_log(f"[Timer] SecurityGuard: total={time.time()-_t0:.3f}s | perm={_t_perm:.3f} (BLOCKED)")
                return

            _t3 = time.time()
            has_quota, reason = asyncio.run(
                self._security.check_rate_limit(
                    user_id=ctx.session_id,
                    resource="agent.chat",
                    action="execute",
                )
            )
            _t_quota = time.time() - _t3

            if not has_quota:
                ctx.short_circuit(f"⚠️ 请求过于频繁: {reason}")
                _timer_log(f"[Timer] SecurityGuard: total={time.time()-_t0:.3f}s | perm={_t_perm:.3f} quota={_t_quota:.3f} (RATE LIMITED)")
                return

            _timer_log(f"[Timer] SecurityGuard: total={time.time()-_t0:.3f}s | perm={_t_perm:.3f} quota={_t_quota:.3f}")
        except Exception as e:
            print(f"[Pipeline] Security check error, allowing pass: {e}", flush=True)
            _timer_log(f"[Timer] SecurityGuard: total={time.time()-_t0:.3f}s (ERROR, pass-through)")

        next_fn()

    def _init_user(self, session_id):
        try:
            from security_module.models import Permission
            self._security.permission_manager.add_permission(
                Permission(
                    permission_id="agent.chat",
                    resource="agent.chat",
                    action="execute",
                    description="Agent chat permission (auto-created)",
                )
            )
            self._security.permission_manager.create_role("user", "Default User (auto-created)")
            self._security.permission_manager.assign_permission_to_role("agent.chat", "user")
            self._security.permission_manager.assign_role_to_user(session_id, "user")
            self._initialized_users.add(session_id)
            print(f"[Pipeline] Auto-registered user {session_id} with agent.chat permissions", flush=True)
        except Exception as e:
            print(f"[Pipeline] Failed to auto-register user: {e}", flush=True)


class ImmuneSystemMiddleware(BaseMiddleware):

    def __init__(self, immune_system):
        self._immune = immune_system

    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        _t0 = time.time()
        try:
            import asyncio
            from agents_md_module import RuleContext

            rule_ctx = RuleContext(session_id=ctx.session_id)
            result = asyncio.run(self._immune.check_content(rule_ctx, ctx.text))
            _t_check = time.time() - _t0
            if result and not result.allowed:
                ctx.short_circuit(f"⚠️ 规则检查发现违规: {result.message}\n\n请调整您的请求。")
                _timer_log(f"[Timer] ImmuneSystem: total={_t_check:.3f}s (BLOCKED)")
                return
            _timer_log(f"[Timer] ImmuneSystem: total={_t_check:.3f}s")
        except Exception as e:
            print(f"[Pipeline] Immune check error, allowing pass: {e}", flush=True)
            _timer_log(f"[Timer] ImmuneSystem: total={time.time()-_t0:.3f}s (ERROR, pass-through)")

        next_fn()


class PlannerMiddleware(BaseMiddleware):

    def __init__(self, planner):
        self._planner = planner

    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        _t0 = time.time()
        try:
            if self._is_complex_task(ctx.text):
                import asyncio
                _t1 = time.time()
                plan = asyncio.run(
                    self._planner.create_plan(
                        task=ctx.text,
                        context={"session_id": ctx.session_id},
                    )
                )
                _t_plan = time.time() - _t1
                if plan and plan.steps:
                    ctx.metadata["plan"] = {
                        "plan_id": plan.plan_id,
                        "task": plan.task,
                        "steps": [
                            {"description": s.description, "type": s.step_type.value}
                            for s in plan.steps
                        ],
                    }
                    plan_text = self._format_plan_for_system(ctx.metadata["plan"])
                    ctx.enriched_system = ctx.enriched_system + plan_text
                _timer_log(f"[Timer] Planner: total={time.time()-_t0:.3f}s | create_plan={_t_plan:.3f}s (complex)")
            else:
                _timer_log(f"[Timer] Planner: total={time.time()-_t0:.3f}s (skipped, not complex)")
        except Exception as e:
            print(f"[Pipeline] Planner error, skipping: {e}", flush=True)
            _timer_log(f"[Timer] Planner: total={time.time()-_t0:.3f}s (ERROR)")

        next_fn()

    def _is_complex_task(self, text: str) -> bool:
        complexity_indicators = [
            "步骤", "流程", "方案", "规划",
            "设计", "架构", "分析并", "多个",
            "首先", "然后", "接着", "最后",
            "实现一个", "开发一个", "帮我做",
        ]
        text_lower = text.lower()
        score = sum(1 for kw in complexity_indicators if kw in text_lower)
        return score >= 2

    def _format_plan_for_system(self, plan: dict) -> str:
        lines = ["\n\n[Task Plan - Auto-generated]"]
        lines.append(f"Task: {plan['task']}")
        lines.append("Steps:")
        for i, s in enumerate(plan["steps"], 1):
            lines.append(f"  {i}. [{s['type']}] {s['description']}")
        return "\n".join(lines)


class StateTrackingMiddleware(BaseMiddleware):

    def __init__(self, state_manager):
        self._state = state_manager

    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        _t0 = time.time()
        try:
            self._state.add_message(ctx.session_id, "user", ctx.user_message_content)
            if ctx.metadata.get("plan"):
                import asyncio
                asyncio.run(
                    self._state.create_task(
                        session_id=ctx.session_id,
                        task_id=ctx.metadata["plan"]["plan_id"],
                        task_type="agent_request",
                        description=ctx.metadata["plan"]["task"],
                    )
                )
        except Exception as e:
            print(f"[Pipeline] State tracking error: {e}", flush=True)

        _timer_log(f"[Timer] StateTracking: total={time.time()-_t0:.3f}s")
        next_fn()


class CapabilityRouterMiddleware(BaseMiddleware):

    def __init__(
        self,
        code_executor,
        knowledge_retrieval,
        search_capability,
        skill_executor,
        skill_registry,
        skill_router,
        detect_request_type: Callable,
    ):
        self._code_executor = code_executor
        self._knowledge_retrieval = knowledge_retrieval
        self._search_capability = search_capability
        self._skill_executor = skill_executor
        self._skill_registry = skill_registry
        self._skill_router = skill_router
        self._detect_request_type = detect_request_type

    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        _t0 = time.time()
        request_type = self._detect_request_type(ctx.text)
        _t_detect = time.time() - _t0

        # 这些类型需要走 LLM（使用特定 persona），不做能力路由短路
        llm_types = {"chat", "ppt", "coding", "evaluation", "planning", "skill", "translate"}
        if request_type in llm_types:
            _timer_log(f"[Timer] CapabilityRouter: total={time.time()-_t0:.3f}s | detect={_t_detect:.3f}s type={request_type} → LLM")
            next_fn()
            return

        result = None
        try:
            _t1 = time.time()
            if request_type == "code_execution":
                result = self._handle_code_execution(ctx)
            elif request_type == "knowledge_query":
                result = self._handle_knowledge_query(ctx)
            elif request_type == "search":
                result = self._handle_search(ctx)
            elif request_type == "security":
                result = self._handle_security_status(ctx)
            else:
                _timer_log(f"[Timer] CapabilityRouter: total={time.time()-_t0:.3f}s | detect={_t_detect:.3f}s type={request_type} → passthrough")
                next_fn()
                return
            _t_handle = time.time() - _t1
            _timer_log(f"[Timer] CapabilityRouter: total={time.time()-_t0:.3f}s | detect={_t_detect:.3f}s handle={_t_handle:.3f}s type={request_type}")
        except Exception as e:
            print(f"[Pipeline] Capability error: {e}", flush=True)
            traceback.print_exc()
            _timer_log(f"[Timer] CapabilityRouter: total={time.time()-_t0:.3f}s (ERROR)")
            next_fn()
            return

        if result:
            ctx.short_circuit(result)
        else:
            next_fn()

    def _handle_code_execution(self, ctx: PipelineContext) -> Optional[str]:
        import asyncio
        code = self._generate_code(ctx.text)
        result = asyncio.run(
            self._code_executor.execute_code(
                code=code,
                language="python",
                timeout=30,
                working_directory=".",
                use_sandbox=True,
            )
        )
        if result.success:
            return f"✅ 代码执行成功:\n```\n{result.output}\n```"
        else:
            return f"❌ 代码执行失败:\n```\n{result.error}\n```"

    def _generate_code(self, task: str) -> str:
        import os
        try:
            lines = []
            if "tushare" in task.lower():
                lines.append("import tushare as ts")
                token = os.getenv("TUSHARE_TOKEN", "")
                if token:
                    lines.append(f'ts.set_token("{token}")')
                lines.append("pro = ts.pro_api()")
            lines.append("# Generated code for: " + task)
            lines.append(task)
            return "\n".join(lines)
        except Exception:
            return "# Failed to generate code\n" + task

    def _handle_knowledge_query(self, ctx: PipelineContext) -> str:
        if not self._knowledge_retrieval._initialized:
            self._knowledge_retrieval.initialize()
        result = self._knowledge_retrieval.query(ctx.text)
        if result:
            return f"🔍 知识检索结果:\n\n{json.dumps(result, ensure_ascii=False, indent=2)}"
        return "❌ 未找到相关知识"

    def _handle_search(self, ctx: PipelineContext) -> str:
        from search_capability import SearchType
        results = self._search_capability.search(ctx.text, search_type=SearchType.ALL, count=5)
        if results:
            lines = ["🔍 搜索结果:\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r.title}")
                lines.append(f"   {r.content[:200]}...\n")
            return "\n".join(lines)
        return "❌ 未找到相关搜索结果"

    def _handle_security_status(self, ctx: PipelineContext) -> str:
        try:
            import asyncio
            from security_module import SecurityModule
            return "🔒 安全模块已启用"
        except Exception:
            return "🔒 安全模块状态: 正常"


class LLMProviderMiddleware(BaseMiddleware):

    def __init__(self, memory, get_base_llm: Callable):
        self._memory = memory
        self._get_base_llm = get_base_llm

    def process(self, ctx: PipelineContext, next_fn: Callable[[], None]) -> None:
        _t0 = time.time()
        try:
            _t1 = time.time()
            llm = self._get_base_llm()
            _t_init = time.time() - _t1

            # 构建 web search 参数
            ws_kwargs = {}
            if ctx.enable_web_search:
                ws_kwargs = {
                    "enable_web_search": True,
                    "force_search": ctx.web_search_force,
                    "max_keyword": ctx.web_search_max_keyword,
                    "limit": ctx.web_search_limit,
                    "user_location": ctx.web_search_user_location,
                }
                print(f"[Pipeline] Web search enabled (force={ctx.web_search_force})", flush=True)

            _t_first_chunk = None
            _chunk_count = 0
            full_reply = ""
            for chunk in llm.stream_chat_with_history(ctx.messages, **ws_kwargs):
                if _t_first_chunk is None:
                    _t_first_chunk = time.time()
                # 处理 annotations（搜索来源引用，增量到达）
                if isinstance(chunk, tuple) and chunk[0] == "__annotations__":
                    annotations = chunk[1]
                    ctx.web_search_annotations.extend(annotations)
                    ctx.write_sse_annotations(annotations)
                    print(f"[Pipeline] Web search annotations: +{len(annotations)} sources (total: {len(ctx.web_search_annotations)})", flush=True)
                    continue
                full_reply += chunk
                _chunk_count += 1
                ctx.write_sse(chunk)
                ctx.stream_writer.flush()

            _t_llm = time.time() - _t1
            _t_ttfb = (_t_first_chunk - _t1) if _t_first_chunk else _t_llm

            self._memory.add_message(ctx.session_id, "assistant", full_reply)
            ctx.write_sse_done()
            if ctx.stream_writer:
                ctx.stream_writer.flush()

            _timer_log(f"[Timer] LLMProvider: total={time.time()-_t0:.3f}s | init={_t_init:.3f} ttfb={_t_ttfb:.3f} stream={_t_llm-_t_ttfb:.3f} chunks={_chunk_count} chars={len(full_reply)}")
        except Exception as e:
            print(f"[Pipeline] LLM error: {e}", flush=True)
            traceback.print_exc()
            _timer_log(f"[Timer] LLMProvider: total={time.time()-_t0:.3f}s (ERROR: {e})")
            ctx.write_sse(f"\n[Agent Error]: {str(e)}")
            ctx.write_sse_done()
            if ctx.stream_writer:
                ctx.stream_writer.flush()
