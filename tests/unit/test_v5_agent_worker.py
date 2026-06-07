"""V5AgentWorker 单元测试 — 不依赖实际 LLM，全部 mock。

使用 pytest + unittest.mock 测试 V5AgentWorker 的核心逻辑，
包括流式输出、think 标签过滤、异常处理、取消逻辑、埋点事件等。
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="session")
def qapp():
    """创建 session 级 QApplication（pytest-qt 要求）"""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def reset_worker_id_counter():
    """每个测试前重置 worker id 计数器，保证可预测性。"""
    from gui.v5.agent_worker import V5AgentWorker
    V5AgentWorker._next_id = 0
    yield


@pytest.fixture
def mock_telemetry():
    """提供一个 mock 的 telemetry 实例，并自动 patch gui.v5.agent_worker.telemetry。"""
    mock_t = MagicMock()
    mock_t.new_session_id.return_value = "auto-session-id"
    with patch("gui.v5.agent_worker.telemetry", return_value=mock_t):
        yield mock_t


@pytest.fixture
def mock_call_agent_pipeline_sync():
    """Patch opencopilot.agent.caller.call_agent_pipeline_sync。"""
    with patch("opencopilot.agent.caller.call_agent_pipeline_sync") as m:
        yield m


# =========================================
# 1. 正常流式输出测试
# =========================================
class TestV5AgentWorkerNormalStream:
    """测试正常流式输出场景"""

    def test_stream_multiple_chunks(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """多个 chunk 应逐条发射 text_updated，最终发射 finished_signal 和完整文本"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter(["Hello", " ", "world", "!"])

        worker = V5AgentWorker(
            prompt="say hello",
            action_type="chat",
            session_id="sess-123",
            context_source="selection",
        )

        texts = []
        finished_texts = []
        worker.text_updated.connect(lambda t: texts.append(t))
        worker.finished_signal.connect(lambda t: finished_texts.append(t))

        # Act
        worker.run()

        # Assert
        # 注意：代码中 emit 的是 _filter_think_tags(full_text).strip()
        # chunk1 "Hello" -> full_text="Hello" -> strip="Hello"
        # chunk2 " "     -> full_text="Hello " -> strip="Hello"
        # chunk3 "world" -> full_text="Hello world" -> strip="Hello world"
        # chunk4 "!"     -> full_text="Hello world!" -> strip="Hello world!"
        assert len(texts) == 4
        assert texts[0] == "Hello"
        assert texts[1] == "Hello"
        assert texts[2] == "Hello world"
        assert texts[3] == "Hello world!"
        assert len(finished_texts) == 1
        assert finished_texts[0] == "Hello world!"
        assert worker.full_text == "Hello world!"

    def test_telemetry_start_and_done(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """V5_AGENT_START 和 V5_AGENT_DONE 应携带正确的字段"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter(["A", "B"])

        worker = V5AgentWorker(
            prompt="test prompt",
            action_type="explain",
            session_id="sess-456",
            context_source="active_doc",
        )

        # Act
        worker.run()

        # Assert
        start_call = None
        done_call = None
        for call in mock_telemetry.emit.call_args_list:
            args, kwargs = call
            event_name = args[0]
            if event_name == "V5_AGENT_START":
                start_call = kwargs
            elif event_name == "V5_AGENT_DONE":
                done_call = kwargs

        assert start_call is not None
        assert start_call["action"] == "explain"
        assert start_call["session_id"] == "sess-456"
        assert start_call["text_len"] == len("test prompt")
        assert start_call["context_source"] == "active_doc"
        assert start_call["worker_id"] == worker._wid

        assert done_call is not None
        assert done_call["action"] == "explain"
        assert done_call["session_id"] == "sess-456"
        assert done_call["chunks"] == 2
        assert done_call["output_len"] == 2
        assert done_call["worker_id"] == worker._wid

    def test_started_signal_emitted(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """run() 开始时应发射 started_signal"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter(["x"])

        worker = V5AgentWorker(prompt="test", session_id="s1")
        started_flags = []
        worker.started_signal.connect(lambda: started_flags.append(True))

        # Act
        worker.run()

        # Assert
        assert len(started_flags) == 1


# =========================================
# 2. think 标签过滤测试
# =========================================
class TestV5AgentWorkerThinkFilter:
    """测试 <think>...</think> 标签过滤逻辑"""

    def test_think_tags_filtered(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """闭合的 think 标签内容应被完全过滤"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter([
            "<think>这是内部推理</think>",
            "最终答案",
        ])

        worker = V5AgentWorker(prompt="思考题", session_id="s-think")
        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))

        # Act
        worker.run()

        # Assert
        assert len(texts) == 2
        assert "<think>" not in texts[0]
        assert "内部推理" not in texts[0]
        assert texts[0] == ""
        assert "<think>" not in texts[1]
        assert "最终答案" in texts[1]

    def test_unclosed_think_tag(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """未闭合的 think 标签应截断并显示思考中提示"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter([
            "<think>正在思考",
            " 继续思考",
        ])

        worker = V5AgentWorker(prompt="思考题", session_id="s-unclosed")
        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))

        # Act
        worker.run()

        # Assert
        assert len(texts) == 2
        # 第一个 chunk 包含未闭合 think，应截断并显示提示
        assert "[AI 正在深度思考中...]" in texts[0]
        assert "<think>" not in texts[0]
        # 第二个 chunk 同样未闭合
        assert "[AI 正在深度思考中...]" in texts[1]

    def test_think_tag_closed_later(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """think 标签后续闭合后应恢复正常显示"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter([
            "<think>思考中",
            "继续思考</think>结果",
        ])

        worker = V5AgentWorker(prompt="思考题", session_id="s-later")
        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))

        # Act
        worker.run()

        # Assert
        assert len(texts) == 2
        # 第一个 chunk 未闭合，显示提示
        assert "[AI 正在深度思考中...]" in texts[0]
        # 第二个 chunk 已闭合，显示正常结果
        assert "<think>" not in texts[1]
        assert "思考中" not in texts[1]
        assert "继续思考" not in texts[1]
        assert "结果" in texts[1]


# =========================================
# 3. 异常处理测试
# =========================================
class TestV5AgentWorkerErrorHandling:
    """测试 call_agent_pipeline_sync 抛异常时的行为"""

    def test_exception_emits_error_signal(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """异常时应发射 error_signal 并附带错误信息"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.side_effect = RuntimeError("LLM service down")

        worker = V5AgentWorker(prompt="fail test", session_id="s-err")
        errors = []
        worker.error_signal.connect(lambda e: errors.append(e))

        # Act
        worker.run()

        # Assert
        assert len(errors) == 1
        assert "[错误]" in errors[0]
        assert "LLM service down" in errors[0]
        assert worker.full_text == ""

    def test_exception_emits_v5_agent_error_telemetry(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """异常时应发射 V5_AGENT_ERROR 埋点，携带 prompt_len 和 context_source"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.side_effect = ValueError("bad request")

        worker = V5AgentWorker(
            prompt="this is a longer prompt",
            action_type="fix",
            session_id="s-err-telemetry",
            context_source="browser",
        )

        # Act
        worker.run()

        # Assert
        error_call = None
        for call in mock_telemetry.emit.call_args_list:
            args, kwargs = call
            if args[0] == "V5_AGENT_ERROR":
                error_call = kwargs
                break

        assert error_call is not None
        assert error_call["action"] == "fix"
        assert error_call["session_id"] == "s-err-telemetry"
        assert error_call["error"] == "bad request"
        assert error_call["prompt_len"] == len("this is a longer prompt")
        assert error_call["context_source"] == "browser"
        assert error_call["worker_id"] == worker._wid

    def test_exception_does_not_emit_finished(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """异常时不应发射 finished_signal"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.side_effect = Exception("boom")

        worker = V5AgentWorker(prompt="x", session_id="s1")
        finished = []
        worker.finished_signal.connect(lambda t: finished.append(t))

        # Act
        worker.run()

        # Assert
        assert len(finished) == 0


# =========================================
# 4. stop() 取消逻辑测试
# =========================================
class TestV5AgentWorkerStop:
    """测试 stop() 取消 Worker 的逻辑"""

    def test_stop_sets_flags(self, qapp, qtbot, mock_telemetry):
        """stop() 应设置 _is_running=False 并设置 cancel_event"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        worker = V5AgentWorker(prompt="test", session_id="s-stop")
        assert worker._is_running is True
        assert worker._cancel_event.is_set() is False

        # Act
        worker.stop()

        # Assert
        assert worker._is_running is False
        assert worker._cancel_event.is_set() is True

    def test_stop_emits_v5_agent_stop_telemetry(self, qapp, qtbot, mock_telemetry):
        """stop() 应发射 V5_AGENT_STOP 埋点"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        worker = V5AgentWorker(
            prompt="test",
            action_type="coding",
            session_id="s-stop-tel",
        )

        # Act
        worker.stop()

        # Assert
        stop_call = None
        for call in mock_telemetry.emit.call_args_list:
            args, kwargs = call
            if args[0] == "V5_AGENT_STOP":
                stop_call = kwargs
                break

        assert stop_call is not None
        assert stop_call["action"] == "coding"
        assert stop_call["session_id"] == "s-stop-tel"
        assert stop_call["worker_id"] == worker._wid

    def test_stop_breaks_stream(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """stop() 后流式循环应在下一个 chunk 前中断"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        def chunk_generator():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
            yield "chunk4"

        mock_call_agent_pipeline_sync.return_value = chunk_generator()

        worker = V5AgentWorker(prompt="test", session_id="s-stop-stream")
        texts = []
        worker.text_updated.connect(lambda t: texts.append(t))

        # 处理 2 个 chunk 后停止
        chunk_counter = [0]

        def count_and_stop(t):
            chunk_counter[0] += 1
            if chunk_counter[0] == 2:
                worker.stop()

        worker.text_updated.connect(count_and_stop)

        # Act
        worker.run()

        # Assert: 只处理了 2 个 chunk（第 2 个处理完后 stop，第 3 个时中断）
        # 实际上：chunk1 处理完 -> counter=1；chunk2 处理完 -> counter=2 -> stop()
        # 进入第 3 次循环时 _is_running=False，break，所以只有 2 个 text_updated
        assert len(texts) == 2
        assert worker._is_running is False


# =========================================
# 5. session_id 透传一致性测试
# =========================================
class TestV5AgentWorkerSessionIdPropagation:
    """测试 session_id 在各处的透传一致性"""

    def test_session_id_passed_to_call_agent(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """session_id 应正确传递给 call_agent_pipeline_sync"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter(["ok"])

        worker = V5AgentWorker(
            prompt="test",
            action_type="chat",
            session_id="my-session-123",
            context_source="clipboard",
        )

        # Act
        worker.run()

        # Assert
        call_args = mock_call_agent_pipeline_sync.call_args
        assert call_args.kwargs["session_id"] == "my-session-123"

    def test_auto_session_id_when_empty(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """session_id 为空时应自动生成，并透传到所有位置"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter(["ok"])

        worker = V5AgentWorker(
            prompt="test",
            action_type="chat",
            session_id="",
            context_source="file",
        )

        # Act
        worker.run()

        # Assert
        assert worker.session_id == "auto-session-id"
        call_args = mock_call_agent_pipeline_sync.call_args
        assert call_args.kwargs["session_id"] == "auto-session-id"

        # 验证 telemetry 中也使用了相同的 session_id
        start_call = None
        for call in mock_telemetry.emit.call_args_list:
            args, kwargs = call
            if args[0] == "V5_AGENT_START":
                start_call = kwargs
                break
        assert start_call["session_id"] == "auto-session-id"

    def test_session_id_in_all_telemetry_events(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """所有埋点事件应使用一致的 session_id"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter(["a", "b"])

        worker = V5AgentWorker(
            prompt="test",
            session_id="consistent-sid",
            context_source="chat",
        )

        # Act
        worker.run()

        # Assert
        for call in mock_telemetry.emit.call_args_list:
            args, kwargs = call
            event_name = args[0]
            if event_name in ("V5_AGENT_START", "V5_AGENT_DONE"):
                assert kwargs["session_id"] == "consistent-sid", f"event {event_name} session_id mismatch"


# =========================================
# 6. 参数透传测试
# =========================================
class TestV5AgentWorkerParameterPassing:
    """测试构造参数正确透传给 call_agent_pipeline_sync"""

    def test_all_params_passed(self, qapp, qtbot, mock_telemetry, mock_call_agent_pipeline_sync):
        """所有构造参数应正确透传给 call_agent_pipeline_sync"""
        # Arrange
        from gui.v5.agent_worker import V5AgentWorker

        mock_call_agent_pipeline_sync.return_value = iter(["result"])

        worker = V5AgentWorker(
            prompt="explain this",
            action_type="explain",
            session_id="sess-1",
            context_source="selection",
            context_meta={"source_text": "code"},
            context_envelope={"doc": "full"},
            image_base64="base64img",
            is_new_task=False,
        )

        # Act
        worker.run()

        # Assert
        call_args = mock_call_agent_pipeline_sync.call_args
        assert call_args.args[0] == "explain this"
        assert call_args.kwargs["action_type"] == "explain"
        assert call_args.kwargs["session_id"] == "sess-1"
        assert call_args.kwargs["is_new_task"] is False
        assert call_args.kwargs["context_source"] == "selection"
        assert call_args.kwargs["context_meta"] == {"source_text": "code"}
        assert call_args.kwargs["context_envelope"] == {"doc": "full"}
        assert call_args.kwargs["image_base64"] == "base64img"
        assert call_args.kwargs["cancel_event"] is worker._cancel_event


# =========================================
# 7. _filter_think_tags 静态方法测试
# =========================================
class TestFilterThinkTags:
    """直接测试 _filter_think_tags 静态方法"""

    def test_no_think_tags(self):
        """无 think 标签时应原样返回"""
        from gui.v5.agent_worker import V5AgentWorker

        text = "这是普通文本"
        result = V5AgentWorker._filter_think_tags(text)
        assert result == text

    def test_single_think_tag(self):
        """单个闭合 think 标签应被移除"""
        from gui.v5.agent_worker import V5AgentWorker

        text = "前缀<think>内部</think>后缀"
        result = V5AgentWorker._filter_think_tags(text)
        assert result == "前缀后缀"

    def test_multiple_think_tags(self):
        """多个闭合 think 标签应全部被移除"""
        from gui.v5.agent_worker import V5AgentWorker

        text = "a<think>x</think>b<think>y</think>c"
        result = V5AgentWorker._filter_think_tags(text)
        assert result == "abc"

    def test_unclosed_think_tag_appends_hint(self):
        """未闭合 think 标签应截断并追加提示"""
        from gui.v5.agent_worker import V5AgentWorker

        text = "前缀<think>未闭合"
        result = V5AgentWorker._filter_think_tags(text)
        assert "前缀" in result
        assert "<think>" not in result
        assert "[AI 正在深度思考中...]" in result

    def test_think_tag_with_newlines(self):
        """think 标签内包含换行也应正确移除"""
        from gui.v5.agent_worker import V5AgentWorker

        text = "开始<think>第一行\n第二行\n第三行</think>结束"
        result = V5AgentWorker._filter_think_tags(text)
        assert result == "开始结束"
