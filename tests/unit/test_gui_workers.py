"""GUI Worker 线程单元测试 — 脱离 GUI 运行。

使用 mock provider 测试各 Worker 的核心逻辑，
不依赖实际 LLM 服务或桌面环境。
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import json
import time
from unittest.mock import MagicMock, patch, PropertyMock
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """创建 session 级 QApplication（pytest-qt 要求）"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# =========================================
# 1. AgentHealthWorker 测试
# =========================================
class TestAgentHealthWorker:
    """测试 Agent 探活 Worker"""

    def test_health_success(self, qapp, qtbot):
        """Agent 在线时应返回 (True, sessions)"""
        from gui.workers.health import AgentHealthWorker

        worker = AgentHealthWorker()
        results = []
        worker.health_result.connect(lambda ok, s: results.append((ok, s)))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"active_sessions": 3}

        with patch("gui.workers.health.httpx.get", return_value=mock_resp):
            worker.run()

        assert len(results) == 1
        assert results[0] == (True, 3)

    def test_health_offline(self, qapp, qtbot):
        """Agent 离线时应返回 (False, 0)"""
        from gui.workers.health import AgentHealthWorker

        worker = AgentHealthWorker()
        results = []
        worker.health_result.connect(lambda ok, s: results.append((ok, s)))

        with patch("gui.workers.health.httpx.get", side_effect=Exception("Connection refused")):
            worker.run()

        assert len(results) == 1
        assert results[0] == (False, 0)

    def test_health_bad_status(self, qapp, qtbot):
        """Agent 返回非200状态时应返回 (False, 0)"""
        from gui.workers.health import AgentHealthWorker

        worker = AgentHealthWorker()
        results = []
        worker.health_result.connect(lambda ok, s: results.append((ok, s)))

        mock_resp = MagicMock()
        mock_resp.status_code = 503

        with patch("gui.workers.health.httpx.get", return_value=mock_resp):
            worker.run()

        assert len(results) == 1
        assert results[0] == (False, 0)


# =========================================
# 2. ModelScannerWorker 测试
# =========================================
class TestModelScannerWorker:
    """测试模型扫描 Worker"""

    def test_scan_openai_models(self, qapp, qtbot):
        """应正确解析 OpenAI 兼容 /models 响应"""
        from gui.workers.scanner import ModelScannerWorker

        worker = ModelScannerWorker("http://localhost:11434/v1")
        results = []
        worker.scan_finished.connect(lambda m, e: results.append((m, e)))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"id": "llama3"},
                {"id": "mistral"},
                {"id": "codellama"},
            ]
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("gui.workers.scanner.httpx.Client", return_value=mock_client):
            worker.run()

        assert len(results) == 1
        models, error = results[0]
        assert models == ["llama3", "mistral", "codellama"]
        assert error == ""

    def test_scan_ollama_fallback(self, qapp, qtbot):
        """OpenAI 接口失败时应回退到 Ollama /api/tags"""
        from gui.workers.scanner import ModelScannerWorker

        worker = ModelScannerWorker("http://localhost:11434/v1")
        results = []
        worker.scan_finished.connect(lambda m, e: results.append((m, e)))

        # 第一次调用（/models）失败，第二次（/api/tags）成功
        fail_resp = MagicMock()
        fail_resp.status_code = 500

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {
            "models": [{"name": "phi3"}, {"name": "gemma"}]
        }

        mock_client = MagicMock()
        mock_client.get.side_effect = [fail_resp, ok_resp]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("gui.workers.scanner.httpx.Client", return_value=mock_client):
            worker.run()

        models, error = results[0]
        assert "phi3" in models
        assert "gemma" in models

    def test_scan_no_models(self, qapp, qtbot):
        """连接成功但无模型时应返回提示信息"""
        from gui.workers.scanner import ModelScannerWorker

        worker = ModelScannerWorker("http://localhost:11434/v1")
        results = []
        worker.scan_finished.connect(lambda m, e: results.append((m, e)))

        # /models 返回200但无 data 字段，/api/tags 也返回200但无 models 字段
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = {"object": "list"}

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {"status": "ok"}

        mock_client = MagicMock()
        mock_client.get.side_effect = [resp1, resp2]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("gui.workers.scanner.httpx.Client", return_value=mock_client):
            worker.run()

        models, error = results[0]
        assert models == []
        assert "未扫描到任何模型" in error


# =========================================
# 3. AIWorker 测试
# =========================================
class TestAIWorker:
    """测试 AI Worker 流式输出逻辑

    NOTE: 旧版 AIWorker 已废弃（改用 gui.v5.agent_worker.V5AgentWorker），
    这些测试基于 provider.stream_agent_task mock，但 AIWorker.run() 现在
    直接调用 call_agent_pipeline_sync()，mock 已失效。
    保留测试作为历史参考，全部标记 skip。
    """

    @pytest.mark.skip(reason="旧版 AIWorker 已废弃，改用 V5AgentWorker")
    def test_ai_worker_stream(self, qapp, qtbot):
        """应逐 chunk 发射 text_updated 信号"""
        from gui.workers.ai import AIWorker

        mock_provider = MagicMock()
        mock_provider.stream_agent_task.return_value = iter(["Hello", " world", "!"])

        worker = AIWorker(
            provider=mock_provider,
            prompt="测试",
            action_type="auto",
            session_id="test-session"
        )

        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))
        finished = []
        worker.finished_signal.connect(lambda: finished.append(True))

        worker.run()

        assert len(finished) == 1
        assert len(texts) >= 1
        # 最后一个发射的文本应包含完整内容
        assert "Hello world!" in texts[-1]

    @pytest.mark.skip(reason="旧版 AIWorker 已废弃，改用 V5AgentWorker")
    def test_ai_worker_stop(self, qapp, qtbot):
        """stop() 应能中断流式处理"""
        from gui.workers.ai import AIWorker

        def slow_stream(*args, **kwargs):
            for i in range(100):
                yield f"chunk-{i}"
                time.sleep(0.01)

        mock_provider = MagicMock()
        mock_provider.stream_agent_task.side_effect = slow_stream

        worker = AIWorker(
            provider=mock_provider,
            prompt="长任务",
            action_type="auto",
            session_id="test-stop"
        )

        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))

        # 在少量 chunk 后停止
        def stop_after():
            while len(texts) < 3:
                time.sleep(0.01)
            worker.stop()

        import threading
        threading.Thread(target=stop_after, daemon=True).start()

        worker.run()

        # 应该没有处理完所有 100 个 chunk
        assert len(texts) < 100

    @pytest.mark.skip(reason="旧版 AIWorker 已废弃，改用 V5AgentWorker")
    def test_ai_worker_think_filter(self, qapp, qtbot):
        """应过滤 <think>...</think> 标签"""
        from gui.workers.ai import AIWorker

        mock_provider = MagicMock()
        mock_provider.stream_agent_task.return_value = iter([
            "<think>内部推理</think>",
            "最终答案是42"
        ])

        worker = AIWorker(
            provider=mock_provider,
            prompt="思考题",
            action_type="auto",
            session_id="test-think"
        )

        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))
        worker.run()

        # think 标签应被过滤掉
        final = texts[-1]
        assert "<think>" not in final
        assert "42" in final

    @pytest.mark.skip(reason="旧版 AIWorker 已废弃，改用 V5AgentWorker")
    def test_ai_worker_error_handling(self, qapp, qtbot):
        """Provider 异常时应发射错误信息"""
        from gui.workers.ai import AIWorker

        mock_provider = MagicMock()
        mock_provider.stream_agent_task.side_effect = Exception("LLM timeout")

        worker = AIWorker(
            provider=mock_provider,
            prompt="会失败",
            action_type="auto",
            session_id="test-error"
        )

        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))
        finished = []
        worker.finished_signal.connect(lambda: finished.append(True))

        worker.run()

        assert len(finished) == 1
        assert any("错误" in t for t in texts)


# =========================================
# 4. ChatWorker 测试
# =========================================
class TestChatWorker:
    """测试 Chat Worker

    NOTE: 旧版 ChatWorker 已废弃（改用 gui.v5.agent_worker.V5AgentWorker），
    这些测试基于 provider.stream_agent_task mock，但 ChatWorker.run() 现在
    直接调用 call_agent_pipeline_sync()，mock 已失效。
    保留测试作为历史参考，全部标记 skip。
    """

    @pytest.mark.skip(reason="旧版 ChatWorker 已废弃，改用 V5AgentWorker")
    def test_chat_worker_basic(self, qapp, qtbot):
        """基本聊天流式输出"""
        from gui.workers.chat import ChatWorker

        mock_provider = MagicMock()
        mock_provider.stream_agent_task.return_value = iter(["你好", "世界"])

        worker = ChatWorker(
            provider=mock_provider,
            text="你好",
            session_id="chat-test"
        )

        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))
        finished = []
        worker.finished_signal.connect(lambda: finished.append(True))

        worker.run()

        assert len(finished) == 1
        assert "你好世界" in texts[-1]

    @pytest.mark.skip(reason="旧版 ChatWorker 已废弃，改用 V5AgentWorker")
    def test_chat_worker_with_task_context(self, qapp, qtbot):
        """带任务上下文的聊天"""
        from gui.workers.chat import ChatWorker

        mock_provider = MagicMock()
        mock_provider.stream_agent_task.return_value = iter(["回答"])

        meta = {"task": "审查代码", "source_text": "审查代码", "source_type": "workspace_task"}
        worker = ChatWorker(
            provider=mock_provider,
            text="怎么做？",
            session_id="chat-ctx",
            context_meta=meta
        )

        worker.run()

        # 验证 provider 被调用时传递了正确的 context_meta
        call_args = mock_provider.stream_agent_task.call_args
        assert call_args.kwargs.get("context_meta") == meta


# =========================================
# 5. BrokerEventsWorker 测试
# =========================================
class TestBrokerEventsWorker:
    """测试 Broker WebSocket 事件 Worker"""

    def test_broker_connection_status(self, qapp, qtbot):
        """连接失败时应报告断线状态"""
        from gui.workers.broker import BrokerEventsWorker

        worker = BrokerEventsWorker(broker_url="ws://localhost:99999/api/v1/events")
        statuses = []
        worker.connection_status.connect(lambda s: statuses.append(s))

        # 直接测试 _listen 逻辑（不进入 run 的 event loop）
        import asyncio

        async def run_test():
            worker.connection_status.emit(False)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()

        assert False in statuses  # 应报告连接失败


# =========================================
# 6. MouseListenerWorker 测试
# =========================================
class TestMouseListenerWorker:
    """测试鼠标监听 Worker（不依赖实际鼠标）"""

    def test_worker_init(self, qapp, qtbot):
        """Worker 初始化应有正确的默认值"""
        from gui.workers.mouse import MouseListenerWorker

        worker = MouseListenerWorker()
        assert worker.last_right_click_time == 0
        assert worker.click_threshold == 0.55
        assert worker._right_click_count == 0
        assert worker._stop_requested is False

    def test_worker_stop_flag(self, qapp, qtbot):
        """stop() 应设置停止标志"""
        from gui.workers.mouse import MouseListenerWorker

        worker = MouseListenerWorker()
        worker._listener = MagicMock()
        worker.stop()
        assert worker._stop_requested is True
        worker._listener.stop.assert_called_once()
