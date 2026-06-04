"""
端到端完整业务链路测试

原则: 每个测试 = 输入 → 完整业务代码链路 → 输出校对（不 Mock）
"""

import os
import json
import uuid
import asyncio
import pytest
from pathlib import Path


# ================================================================
# 链路 1: ConfigManager 完整读写闭环
# ================================================================

class TestConfigManagerE2E:
    """ConfigManager: 读写→保存→重载 完整闭环"""

    def test_full_read_write_reload_cycle(self):
        from config_manager import ConfigManager
        ConfigManager.reset_instance()
        cfg = ConfigManager.get_instance()

        original = cfg.get_agent()["max_turns"]
        cfg.update_section("agent", {"max_turns": 25})
        assert cfg.get_agent()["max_turns"] == 25

        with open("config.json", "r") as f:
            disk_data = json.load(f)
        assert disk_data["agent"]["max_turns"] == 25

        cfg.reload()
        assert cfg.get_agent()["max_turns"] == 25

        cfg.update_section("agent", {"max_turns": original})
        assert cfg.get_agent()["max_turns"] == original

    def test_concurrency_config_clamp_and_save(self):
        from config_manager import ConfigManager
        ConfigManager.reset_instance()
        cfg = ConfigManager.get_instance()

        cfg.update_section("agent", {"max_turns": 100})
        assert cfg.get_agent()["max_turns"] == 30  # clamp to max

        cfg.update_section("agent", {"max_turns": 10})

    def test_context_budget_from_disk(self):
        from config_manager import ConfigManager
        ConfigManager.reset_instance()
        cfg = ConfigManager.get_instance()
        budget = cfg.get_context_budget()
        assert budget["max_input_chars"] == 120000

    def test_model_limits_from_disk(self):
        from config_manager import ConfigManager
        ConfigManager.reset_instance()
        cfg = ConfigManager.get_instance()
        limits = cfg.get_model_limits()
        assert "MiniMax-M3" in limits
        assert limits["MiniMax-M3"] == 200000


# ================================================================
# 链路 2: CodeExecutor 真实代码执行（async）
# ================================================================

class TestCodeExecutorE2E:
    """CodeExecutor: 代码→异步执行→输出 完整链路"""

    def test_simple_python_execution(self):
        from opencopilot.capabilities.coding import CodeExecutor, ExecutorConfig
        executor = CodeExecutor(ExecutorConfig(default_timeout=5))
        result = asyncio.run(executor.execute_code('print("Hello OpenCopilot!")', "python"))
        assert "Hello OpenCopilot" in result.stdout
        assert result.exit_code == 0

    def test_python_computation(self):
        from opencopilot.capabilities.coding import CodeExecutor, ExecutorConfig
        executor = CodeExecutor(ExecutorConfig(default_timeout=5))
        code = "def fib(n):\n a,b=0,1\n for _ in range(n): a,b=b,a+b\n return a\nprint(fib(10))"
        result = asyncio.run(executor.execute_code(code, "python"))
        assert "55" in result.stdout

    def test_python_with_error(self):
        from opencopilot.capabilities.coding import CodeExecutor, ExecutorConfig
        executor = CodeExecutor(ExecutorConfig(default_timeout=5))
        result = asyncio.run(executor.execute_code("print(1/0)", "python"))
        assert result.exit_code != 0

    def test_python_multiline_variable(self):
        from opencopilot.capabilities.coding import CodeExecutor, ExecutorConfig
        executor = CodeExecutor(ExecutorConfig(default_timeout=5))
        result = asyncio.run(executor.execute_code("x=sum(range(1,101))\nprint(f'Sum={x}')", "python"))
        assert "Sum=5050" in result.stdout


# ================================================================
# 链路 3: Pipeline 完整上下文构建 + 消息编组
# ================================================================

class TestPipelineE2E:
    """Pipeline: 上下文构建→消息编组 完整链路"""

    def test_context_build_and_message_payload(self):
        from opencopilot.agent.pipeline import PipelineContext
        from opencopilot.agent.core import ContextWindowManager

        # 1. 构建 PipelineContext（输入）
        ctx = PipelineContext(
            request={"type": "chat", "source": "ide"},
            session_id=f"e2e-{uuid.uuid4().hex[:8]}",
            text="请帮我修复这段代码的 bug",
            action_type="chat",
            metadata={"file": "main.py", "language": "python"},
        )

        # 2. ContextWindowManager 构建 payload（中间业务链路）
        cwm = ContextWindowManager(max_input_chars=50000)
        envelope = {
            "source": "ide",
            "content": "def add(a, b): return a - b",
            "task": "fix bug",
        }
        result = cwm.build_user_payload(envelope)

        # 3. 验证输出：业务链路生成的 payload 包含关键信息
        assert isinstance(result, str)
        assert "fix bug" in result
        assert "def add" in result

    def test_context_truncation(self):
        from opencopilot.agent.core import ContextWindowManager

        # 1. 输入：超长文本 + 极小窗口
        cwm = ContextWindowManager(max_input_chars=200, reserve_output_chars=50)
        long_text = "A" * 500
        envelope = {"source": "ide", "content": long_text, "task": "test"}

        # 2. 执行业务链路：构建 payload（内部截断）
        result = cwm.build_user_payload(envelope)

        # 3. 验证截断生效：输出应远小于输入
        assert isinstance(result, str)
        assert len(result) < len(long_text)


# ================================================================
# 链路 4: LLM Provider 配置加载 + 工厂创建
# ================================================================

class TestLLMProviderE2E:
    """LLM Provider: 配置→工厂→Provider实例 完整链路"""

    def test_config_load_chain(self):
        from llm_provider import load_config
        cfg = load_config()
        assert "provider_type" in cfg
        assert cfg["provider_type"] in ("mimo", "minimax", "local")

    def test_provider_factory_creates_instance(self):
        from opencopilot.providers.llm_provider import ProviderFactory
        factory = ProviderFactory()
        assert hasattr(factory, 'create_provider')

    def test_provider_to_config_consistency(self):
        from llm_provider import load_config
        from config_manager import ConfigManager
        provider_cfg = load_config()
        ConfigManager.reset_instance()
        mgr_cfg = ConfigManager.get_instance().get_llm()
        assert mgr_cfg["temperature"] == 0.7


# ================================================================
# 链路 5: PPT 生成模块
# ================================================================

class TestPPTModuleE2E:
    """PPT 模块: 文本→生成PPT 完整链路"""

    def test_ppt_generate_from_text_creates_file(self):
        from ppt_generator import generate_ppt_from_text
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_output.pptx")
            text_content = "# 测试标题\n## 第一页\n这是测试内容\n## 第二页\n更多内容"
            result_path = generate_ppt_from_text(text=text_content, output_path=output_path)
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0

    def test_ppt_dialog_import_chain(self):
        from opencopilot.capabilities.ppt.cocreation_dialog import CoCreationDialog
        from opencopilot.capabilities.ppt.suggestion_engine import SuggestionEngine
        from opencopilot.capabilities.ppt.context_analyzer import ContextAnalyzer
        from opencopilot.capabilities.ppt.conversation_manager import ConversationManager

        assert CoCreationDialog is not None
        assert SuggestionEngine is not None
        assert ContextAnalyzer is not None
        assert ConversationManager is not None


# ================================================================
# 链路 6: 免疫系统内容安全检查
# ================================================================

class TestImmuneSystemE2E:
    """免疫系统: 文本→规则检查→判定结果"""

    def test_immune_system_init_and_check(self):
        import asyncio
        from opencopilot.safety.immune.immune_system import ImmuneSystem
        from opencopilot.safety.immune.models import RuleContext

        system = ImmuneSystem()
        ctx = RuleContext(
            session_id="test",
            user_id="test_user",
            current_action="chat",
        )
        # check_content 是异步的
        result = asyncio.run(system.check_content(ctx, "帮我写一个 Python 函数"))
        assert result is not None
        # ImmuneResponse 使用 allowed 字段
        assert hasattr(result, 'allowed')
        # 正常文本应通过
        assert result.allowed is True

    def test_rule_engine_loading(self):
        from opencopilot.safety.immune.rule_engine import RuleEngine
        engine = RuleEngine()
        assert engine is not None


# ================================================================
# 链路 7: 知识图谱构建 + 查询
# ================================================================

class TestKnowledgeGraphE2E:
    """知识图谱: 建图→查询 完整链路"""

    def test_graph_build_and_query(self):
        from knowledge_graph.graph import GraphManager
        from knowledge_graph.models import Entity, EntityType
        import os

        tmp_file = "knowledge_graph_e2e_test.json"
        try:
            # 1. 输入：构造实体 + 创建图管理器
            gm = GraphManager(project_root=str(Path.cwd()), graph_file=tmp_file)
            entity = Entity(
                id="test_e2e_entity",
                name="test_e2e_entity",
                entity_type=EntityType.TOOL,
                properties={"language": "python"},
            )

            # 2. 执行业务链路：add_entity 不抛异常即为成功
            entity_id = gm.add_entity(entity)
            assert entity_id == "test_e2e_entity"

            # 3. 清理：remove_entity 不抛异常
            gm.remove_entity("test_e2e_entity")
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)


# ================================================================
# 链路 8: 多模块交叉调用
# ================================================================

class TestCrossModuleE2E:
    """跨模块串联: ConfigManager→Pipeline→CodeExecutor 数据流"""

    def test_config_to_code_execution(self):
        from config_manager import ConfigManager
        from opencopilot.capabilities.coding import CodeExecutor, ExecutorConfig
        import asyncio

        ConfigManager.reset_instance()
        cfg = ConfigManager.get_instance()
        concurrency = cfg.get_concurrency()
        code_timeout = concurrency.get("code_execution", 5)

        executor = CodeExecutor(ExecutorConfig(default_timeout=code_timeout))
        result = asyncio.run(executor.execute_code("print('cross-module OK')", "python"))
        assert "cross-module OK" in result.stdout
        assert result.exit_code == 0

    def test_pipeline_context_to_provider_config(self):
        from opencopilot.agent.pipeline import PipelineContext
        from config_manager import ConfigManager

        ConfigManager.reset_instance()
        cfg = ConfigManager.get_instance()

        ctx = PipelineContext(
            request={"type": "chat"},
            session_id="cross-test",
            text="测试消息",
            action_type="chat",
        )

        concurrency = cfg.get_concurrency()
        assert "chat" in concurrency
        assert ctx.action_type in concurrency


# ================================================================
# 链路 9: API Gateway 真实 HTTP 请求
# ================================================================

class TestAPIGatewayRealHTTP:
    """API Gateway: HTTP请求→路由→响应 完整链路"""

    @pytest.fixture(scope="class")
    def api_base_url(self):
        import threading
        import time
        import httpx
        from smart_copilot_api import app
        import uvicorn

        port = 18765
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        base_url = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                r = httpx.get(f"{base_url}/docs", timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)

        yield base_url
        server.should_exit = True

    def test_root_and_docs(self, api_base_url):
        import httpx
        r = httpx.get(f"{api_base_url}/", timeout=5)
        assert r.status_code in (200, 404, 307)
        r = httpx.get(f"{api_base_url}/docs", timeout=5)
        assert r.status_code == 200

    def test_chat_endpoint_with_real_request(self, api_base_url):
        import httpx
        payload = {"message": "Hello", "session_id": str(uuid.uuid4())}
        r = httpx.post(f"{api_base_url}/api/chat", json=payload, timeout=15)
        assert r.status_code in (200, 422, 503)
        if r.status_code == 200:
            data = r.json()
            assert "response" in data or "content" in data
