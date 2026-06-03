"""
Skill 层 LLM 统一验证测试

验证所有 AI 类端点都通过 Agent 管线调用 LLM，
不再有直接调用 provider.stream_chat() 的路径。

测试策略：
1. 代码静态分析：确认 smart_copilot_api.py 中不再有直接的 LLM 调用
2. 管线集成验证：确认 coding 端点通过 _call_agent_pipeline() 调用
3. 非AI端点验证：确认非AI端点（文件/格式/人设/知识）不需要走管线
"""

import os
import sys
import re
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestSkillLLMUnification(unittest.TestCase):
    """验证 Skill 层 LLM 调用已统一到 Agent 管线"""

    def test_no_direct_llm_calls_in_api(self):
        """验证 smart_copilot_api.py 中不再有直接 LLM 调用"""
        with open("smart_copilot_api.py", "r") as f:
            content = f.read()

        # 不应出现以下模式（直接调用 LLM 的特征）
        forbidden_patterns = [
            r"provider\.stream_chat\s*\(",  # 直接调用 provider
            r"ProviderFactory\.create_provider\s*\(",  # 直接创建 provider
            r"llm_adapter\.generate\s*\(",  # 通过 adapter 直接调 LLM
            r"coding_skill\.execute\s*\(",   # coding skill 直接执行（已改走管线）
        ]

        for pattern in forbidden_patterns:
            matches = re.findall(pattern, content)
            self.assertEqual(len(matches), 0,
                             f"发现禁用模式 '{pattern}'，共 {len(matches)} 处。"
                             f"所有 AI 请求应通过 _call_agent_pipeline() 调用。")

    def test_coding_endpoints_use_pipeline(self):
        """验证 Coding 端点都通过 _call_agent_pipeline() 调用"""
        with open("smart_copilot_api.py", "r") as f:
            content = f.read()

        # 查找 coding 端点函数
        coding_endpoints = [
            "code_review", "bug_fix", "code_explain",
            "code_refactor", "enhance_api", "code_analyze"
        ]

        for endpoint in coding_endpoints:
            # 每个端点应该包含 _call_agent_pipeline 调用
            # 找到端点函数定义
            pattern = rf'@app\.post\("/api/coding/[^"]+"\)\s*async def {endpoint}'
            match = re.search(pattern, content)
            self.assertIsNotNone(match, f"未找到端点: {endpoint}")

            # 找到函数体的结束位置（下一个端点或类定义）
            func_start = match.end()
            next_endpoint = re.search(r'\n@app\.|class\s+\w+', content[func_start:])
            func_body = content[func_start:func_start + next_endpoint.start()] if next_endpoint else content[func_start:]

            # 验证包含 _call_agent_pipeline
            self.assertIn("_call_agent_pipeline", func_body,
                          f"端点 {endpoint} 未使用 _call_agent_pipeline()")

            # 验证 action_type 为 coding
            self.assertIn('"coding"', func_body,
                          f"端点 {endpoint} 未设置 action_type='coding'")

    def test_coding_endpoints_have_coding_prompt_builder(self):
        """验证 Coding 端点使用 _build_coding_prompt() 构建 prompt"""
        with open("smart_copilot_api.py", "r") as f:
            content = f.read()

        coding_intents = ["code_review", "bug_fix", "explain", "refactor", "enhance_api", "analyze"]

        for intent in coding_intents:
            self.assertIn(f'_build_coding_prompt("{intent}"', content,
                          f"未找到 intent '{intent}' 的 _build_coding_prompt 调用")

    def test_non_ai_endpoints_dont_need_pipeline(self):
        """验证非 AI 端点（文件/格式/人设/知识）不走管线"""
        with open("smart_copilot_api.py", "r") as f:
            content = f.read()

        # 这些端点是纯计算/管理，不调 LLM，不需要走管线
        non_ai_endpoints = [
            "/api/file/read", "/api/file/write", "/api/file/convert",
            "/api/format/md-to-docx", "/api/format/md-to-pptx",
            "/api/persona/list", "/api/persona/get", "/api/persona/save",
            "/api/knowledge/query", "/api/knowledge/export",
            "/api/evaluation/evaluate", "/api/evaluation/score",
        ]

        for endpoint in non_ai_endpoints:
            # 找到端点定义
            pattern = rf'@app\.post\("{re.escape(endpoint)}"\)'
            match = re.search(pattern, content)
            if match:
                # 获取端点函数体
                func_start = match.end()
                next_def = re.search(r'\n@app\.|class\s+\w+', content[func_start:])
                func_body = content[func_start:func_start + next_def.start()] if next_def else content[func_start:]

                # 验证不包含 _call_agent_pipeline
                self.assertNotIn("_call_agent_pipeline", func_body,
                                 f"非 AI 端点 {endpoint} 不应使用 _call_agent_pipeline()")

    def test_ai_endpoints_use_pipeline(self):
        """验证所有 AI 端点（PPT/Text/Chat/Coding）都走管线"""
        with open("smart_copilot_api.py", "r") as f:
            content = f.read()

        # 这些端点涉及 AI，应该走管线
        ai_endpoints = [
            "/api/ppt/extract-from-text",
            "/api/ppt/cocreation",
            "/api/text/process",
            "/api/ppt/suggest",
            "/api/coding/review",
            "/api/coding/bug-fix",
            "/api/coding/explain",
            "/api/coding/refactor",
            "/api/coding/enhance-api",
            "/api/coding/analyze",
        ]

        for endpoint in ai_endpoints:
            pattern = rf'@app\.(?:post|websocket)\("{re.escape(endpoint)}"\)'
            match = re.search(pattern, content)
            if match:
                func_start = match.end()
                next_def = re.search(r'\n@app\.|class\s+\w+', content[func_start:])
                func_body = content[func_start:func_start + next_def.start()] if next_def else content[func_start:]

                self.assertIn("_call_agent_pipeline", func_body,
                              f"AI 端点 {endpoint} 应使用 _call_agent_pipeline()")

    def test_pipeline_has_tracer(self):
        """验证管线已集成追踪器"""
        with open("asu_custom_agent.py", "r") as f:
            content = f.read()

        self.assertIn("DistributedTracer", content, "Agent 应导入 DistributedTracer")
        self.assertIn("tracer = DistributedTracer", content, "Agent 应创建 tracer 实例")
        self.assertIn("MiddlewarePipeline(tracer=tracer)", content,
                       "Agent 应将 tracer 注入到管线")

    def test_pipeline_tracing_works(self):
        """验证管线追踪功能正常工作"""
        from observability_module.tracer import DistributedTracer
        from observability_module import ObservabilityConfig
        from agent_pipeline import PipelineContext, MiddlewarePipeline, BaseMiddleware

        config = ObservabilityConfig(enable_tracing=True)
        tracer = DistributedTracer(config)
        pipeline = MiddlewarePipeline(tracer=tracer)

        class TestMiddleware(BaseMiddleware):
            def process(self, ctx, next_fn):
                ctx.metadata["test"] = True
                next_fn()

        pipeline.use(TestMiddleware())

        ctx = PipelineContext(
            request={"text": "test"},
            session_id="test_tracing",
            text="test",
            action_type="coding",
        )
        pipeline.execute(ctx)

        # 验证 trace 已创建
        traces = tracer.get_traces()
        self.assertEqual(len(traces), 1)

        # 验证 span 已创建
        trace = traces[0]
        self.assertEqual(len(trace.spans), 1)
        self.assertEqual(trace.spans[0].operation, "middleware.TestMiddleware")

        # 验证 trace_id 注入到 ctx
        self.assertIsNotNone(ctx.trace_id)

        # 验证 span duration
        self.assertIsNotNone(trace.spans[0].duration_ms)

        # 验证 trace tags 包含 action_type
        self.assertIn("action_type", trace.tags)
        self.assertEqual(trace.tags["action_type"], "coding")


class TestCodingPromptBuilder(unittest.TestCase):
    """验证 Coding prompt 构建器"""

    def setUp(self):
        # 导入 _build_coding_prompt 函数
        # 由于它在 smart_copilot_api.py 中，我们直接测试逻辑
        pass

    def test_code_review_prompt(self):
        """验证代码审查 prompt 包含关键信息"""
        from smart_copilot_api import _build_coding_prompt

        prompt = _build_coding_prompt("code_review", {
            "code": "def hello(): pass",
            "language": "python",
            "context": "test context",
        })

        self.assertIn("审查", prompt)
        self.assertIn("python", prompt)
        self.assertIn("def hello(): pass", prompt)
        self.assertIn("test context", prompt)

    def test_bug_fix_prompt(self):
        """验证 Bug 修复 prompt 包含错误信息"""
        from smart_copilot_api import _build_coding_prompt

        prompt = _build_coding_prompt("bug_fix", {
            "code": "def hello(): pass",
            "error_message": "NameError: name 'x' is not defined",
            "language": "python",
        })

        self.assertIn("修复", prompt)
        self.assertIn("NameError", prompt)

    def test_explain_prompt(self):
        """验证代码解释 prompt 包含详细程度"""
        from smart_copilot_api import _build_coding_prompt

        prompt = _build_coding_prompt("explain", {
            "code": "def hello(): pass",
            "language": "python",
            "detail_level": "detailed",
        })

        self.assertIn("详细", prompt)
        self.assertIn("解释", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
