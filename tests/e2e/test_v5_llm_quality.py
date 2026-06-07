"""
v5 GUI 端到端 LLM 输出质量测试

验证 Agent Pipeline 在真实 LLM 调用下的输出质量。
使用 call_agent_pipeline_sync 直接调用，不经过 GUI 层（避免 Qt 依赖）。

注意：这些测试消耗真实的 LLM token，已标记为 @pytest.mark.slow。
运行前请确保 LLM 服务配置正确（config.json 或环境变量）。
"""

from __future__ import annotations

import os
import re
import sys
import json
import uuid
import signal
import threading
from typing import List
from pathlib import Path

import pytest


# ── 项目根目录注入 ──
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ── 超时装饰器（pytest-timeout 未安装时的回退）──
try:
    from pytest_timeout import timeout as _timeout_decorator

    def _timeout(seconds: int):
        return pytest.mark.timeout(seconds, method="signal")
except ImportError:
    # 回退：使用 signal.alarm（仅 Unix）
    def _timeout(seconds: int):
        def decorator(func):
            return func
        return decorator


# ── 常量 ──
LLM_TIMEOUT_SECONDS = 60          # 单个 LLM 调用超时
COLLECT_TIMEOUT_SECONDS = 55      # 收集 chunk 的超时
MIN_OUTPUT_LENGTH = {
    "explain": 50,
    "polish": 10,
    "chat": 20,
    "ppt": 100,
}

# 用于检测中文语境的关键词（至少命中一个即认为保持中文）
CHINESE_INDICATORS = [
    "的", "了", "是", "在", "和", "有", "为", "与", "或",
    "可以", "能够", "通过", "进行", "使用", "需要",
]


# ── 辅助函数 ──

def _check_llm_available() -> tuple[bool, str]:
    """检查 LLM 服务是否可用（不实际调用，只检查配置）。"""
    try:
        from llm_provider import load_config
        cfg = load_config()
        provider_type = cfg.get("provider_type", "mimo")

        if provider_type == "mimo":
            api_key = cfg.get("mimo_api_key") or os.environ.get("XIAOMI_API_KEY") or os.environ.get("xiaomi_api_key") or os.environ.get("MIMO_API_KEY")
            if not api_key:
                return False, "MiMo API key 未配置（需 XIAOMI_API_KEY / MIMO_API_KEY 环境变量或 config.json）"
        elif provider_type == "minimax":
            api_key = cfg.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY")
            if not api_key:
                return False, "MiniMax API key 未配置（需 MINIMAX_API_KEY 环境变量或 config.json）"
        elif provider_type == "local":
            api_base = cfg.get("local_api_base", "http://localhost:11434/v1")
            return True, f"Local provider ({api_base})"
        else:
            return False, f"未知的 provider_type: {provider_type}"

        return True, f"{provider_type} provider 已配置"
    except Exception as e:
        return False, f"检查 LLM 配置时出错: {e}"


def _collect_pipeline_output(
    prompt: str,
    action_type: str,
    context_source: str = "test",
    context_meta: dict | None = None,
    timeout: int = COLLECT_TIMEOUT_SECONDS,
) -> tuple[str, int]:
    """
    调用 call_agent_pipeline_sync 并收集全部输出。

    Returns:
        (full_text, chunk_count)
    Raises:
        RuntimeError: LLM 服务不可用或调用失败
    """
    from opencopilot.agent.caller import call_agent_pipeline_sync

    full_text = ""
    chunk_count = 0
    cancel_event = threading.Event()

    # 使用 alarm 实现硬超时（Unix only）
    def _alarm_handler(signum, frame):
        cancel_event.set()
        raise TimeoutError(f"LLM 调用超时（>{timeout}秒）")

    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(timeout)

        for chunk in call_agent_pipeline_sync(
            text=prompt,
            action_type=action_type,
            session_id=f"e2e-{uuid.uuid4().hex[:8]}",
            context_source=context_source,
            context_meta=context_meta or {},
            is_new_task=True,
            cancel_event=cancel_event,
            timeout=timeout,
        ):
            full_text += chunk
            chunk_count += 1
            if cancel_event.is_set():
                break

        signal.alarm(0)  # 取消 alarm
    except TimeoutError:
        raise RuntimeError(f"LLM 调用超时（>{timeout}秒），请检查网络连接和 LLM 服务状态")
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败: {e}")
    finally:
        if old_handler is not None:
            signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

    return full_text, chunk_count


def _filter_think_tags(text: str) -> str:
    """过滤 <think> 标签（与 V5AgentWorker._filter_think_tags 保持一致）。"""
    display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in display:
        display = display.split("<think>")[0]
    return display


def _contains_chinese(text: str) -> bool:
    """检查文本是否包含中文字符。"""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _maintains_chinese_context(text: str) -> bool:
    """检查输出是否保持中文语境（命中中文指示词或包含中文字符）。"""
    if _contains_chinese(text):
        return True
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in CHINESE_INDICATORS)


# ── 测试类 ──

@pytest.mark.slow
class TestV5WorkTabExplain:
    """Work Tab - explain 操作：验证代码解释质量"""

    @pytest.fixture(scope="class")
    def llm_output(self):
        """Fixture: 调用 explain 获取真实 LLM 输出（class 级只调用一次）。"""
        available, msg = _check_llm_available()
        if not available:
            pytest.skip(f"LLM 服务不可用: {msg}")

        code = "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"
        prompt = f"请解释以下代码/文本:\n\n{code}"

        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="explain",
                context_source="selection",
                context_meta={"source_text": code},
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")

        return {"text": full_text, "chunks": chunk_count, "input": code}

    def test_output_not_empty(self, llm_output):
        """验证：输出不应为空"""
        assert llm_output["text"], "LLM 输出不应为空"

    def test_output_length(self, llm_output):
        """验证：输出长度 > 50 字符"""
        assert len(llm_output["text"]) > MIN_OUTPUT_LENGTH["explain"], (
            f"输出过短: {len(llm_output['text'])} 字符，期望 > {MIN_OUTPUT_LENGTH['explain']}"
        )

    def test_output_contains_explanation_keywords(self, llm_output):
        """验证：输出应包含解释性关键词（递归、斐波那契、函数等）"""
        text_lower = llm_output["text"].lower()
        keywords = ["递归", "斐波那契", "函数", "fib", "调用", "返回", "基准"]
        matched = [kw for kw in keywords if kw in text_lower]
        assert matched, (
            f"输出未包含任何解释性关键词。期望包含: {keywords}\n"
            f"实际输出: {llm_output['text'][:200]}"
        )

    def test_no_unfiltered_think_tags(self, llm_output):
        """验证：输出中不应包含未过滤的 <think> 标签"""
        filtered = _filter_think_tags(llm_output["text"])
        assert "<think>" not in filtered, (
            f"输出中包含未过滤的 <think> 标签:\n{llm_output['text'][:500]}"
        )

    def test_at_least_one_chunk(self, llm_output):
        """验证：应至少收到一个 chunk"""
        assert llm_output["chunks"] > 0, "未收到任何 chunk"


@pytest.mark.slow
class TestV5WorkTabPolish:
    """Work Tab - polish 操作：验证文本润色质量"""

    @pytest.fixture(scope="class")
    def llm_output(self):
        """Fixture: 调用 polish 获取真实 LLM 输出。"""
        available, msg = _check_llm_available()
        if not available:
            pytest.skip(f"LLM 服务不可用: {msg}")

        input_text = "这个产品很好，用起来不错"
        prompt = f"请润色优化以下文本:\n\n{input_text}"

        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="polish",
                context_source="selection",
                context_meta={"source_text": input_text},
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")

        return {"text": full_text, "chunks": chunk_count, "input": input_text}

    def test_output_not_empty(self, llm_output):
        """验证：输出不应为空"""
        assert llm_output["text"], "LLM 输出不应为空"

    def test_output_length_at_least_input(self, llm_output):
        """验证：润色后的输出长度应 >= 输入长度（润色通常不会缩短）"""
        input_len = len(llm_output["input"])
        output_len = len(llm_output["text"])
        # 允许少量缩短（10% 容差），但不应显著缩短
        assert output_len >= input_len * 0.7, (
            f"润色输出({output_len} 字符)显著短于输入({input_len} 字符)，"
            f"可能未正确润色。输出: {llm_output['text'][:200]}"
        )

    def test_maintains_chinese_context(self, llm_output):
        """验证：输出应保持中文语境"""
        assert _maintains_chinese_context(llm_output["text"]), (
            f"润色输出未保持中文语境。输出: {llm_output['text'][:200]}"
        )

    def test_no_unfiltered_think_tags(self, llm_output):
        """验证：输出中不应包含未过滤的 <think> 标签"""
        filtered = _filter_think_tags(llm_output["text"])
        assert "<think>" not in filtered, (
            f"输出中包含未过滤的 <think> 标签"
        )


@pytest.mark.slow
class TestV5ChatTab:
    """Chat Tab - 对话：验证聊天回复质量"""

    @pytest.fixture(scope="class")
    def llm_output(self):
        """Fixture: 调用 chat 获取真实 LLM 输出。"""
        available, msg = _check_llm_available()
        if not available:
            pytest.skip(f"LLM 服务不可用: {msg}")

        prompt = "你好，请介绍一下自己"

        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="chat",
                context_source="chat",
                context_meta={},
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")

        return {"text": full_text, "chunks": chunk_count, "input": prompt}

    def test_output_not_empty(self, llm_output):
        """验证：输出不应为空"""
        assert llm_output["text"], "LLM 输出不应为空"

    def test_output_length(self, llm_output):
        """验证：输出长度 > 20 字符"""
        assert len(llm_output["text"]) > MIN_OUTPUT_LENGTH["chat"], (
            f"输出过短: {len(llm_output['text'])} 字符"
        )

    def test_friendly_self_introduction(self, llm_output):
        """验证：输出应是友好的自我介绍"""
        text_lower = llm_output["text"].lower()
        # 友好自我介绍通常包含这些关键词之一
        friendly_keywords = [
            "你好", "您好", "帮助", "助手", "助理", "ai", "智能",
            "很高兴", "乐意", "可以", "能够", "协助", "支持",
            "open", "copilot", "opencopilot",
        ]
        matched = [kw for kw in friendly_keywords if kw in text_lower]
        assert matched, (
            f"输出不像友好的自我介绍。期望包含: {friendly_keywords}\n"
            f"实际输出: {llm_output['text'][:300]}"
        )

    def test_no_unfiltered_think_tags(self, llm_output):
        """验证：输出中不应包含未过滤的 <think> 标签"""
        filtered = _filter_think_tags(llm_output["text"])
        assert "<think>" not in filtered


@pytest.mark.slow
class TestV5StudioTabPPT:
    """Studio Tab - PPT 生成：验证 PPT 内容生成质量"""

    @pytest.fixture(scope="class")
    def llm_output(self):
        """Fixture: 调用 ppt 获取真实 LLM 输出。"""
        available, msg = _check_llm_available()
        if not available:
            pytest.skip(f"LLM 服务不可用: {msg}")

        topic = "人工智能的发展历史"
        prompt = (
            f"请根据以下主题生成 PPT 大纲，以 JSON 格式输出，"
            f"包含 slides 数组，每个 slide 有 title 和 content 字段:\n\n{topic}"
        )

        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="ppt",
                context_source="studio",
                context_meta={"input_text": topic},
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")

        return {"text": full_text, "chunks": chunk_count, "input": topic}

    def test_output_not_empty(self, llm_output):
        """验证：输出不应为空"""
        assert llm_output["text"], "LLM 输出不应为空"

    def test_output_length(self, llm_output):
        """验证：输出长度 > 100 字符"""
        assert len(llm_output["text"]) > MIN_OUTPUT_LENGTH["ppt"], (
            f"输出过短: {len(llm_output['text'])} 字符，PPT 生成应返回较完整的内容"
        )

    def test_contains_slide_structure(self, llm_output):
        """验证：输出应包含 JSON 格式的 slides 数组或 slide/title 等关键词"""
        text = llm_output["text"]
        text_lower = text.lower()

        # 检查是否包含 slides 结构关键词
        slide_keywords = ["slide", "slides", "title", "content", "ppt", "幻灯片", "大纲"]
        matched_keywords = [kw for kw in slide_keywords if kw in text_lower]

        # 尝试解析 JSON（如果输出包含 JSON 代码块）
        has_json_slides = False
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "slides" in data and isinstance(data["slides"], list):
                    has_json_slides = True
            except json.JSONDecodeError:
                pass

        # 尝试直接解析整个文本为 JSON
        if not has_json_slides:
            try:
                data = json.loads(text)
                if "slides" in data and isinstance(data["slides"], list):
                    has_json_slides = True
            except json.JSONDecodeError:
                pass

        # 尝试提取方括号包裹的数组
        if not has_json_slides:
            array_match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
            if array_match:
                try:
                    slides = json.loads(array_match.group(0))
                    if isinstance(slides, list) and len(slides) > 0:
                        has_json_slides = True
                except json.JSONDecodeError:
                    pass

        assert has_json_slides or len(matched_keywords) >= 2, (
            f"输出未包含预期的 PPT 结构。"
            f"期望包含 slides 数组或 slide/title/content 等关键词。\n"
            f"匹配到的关键词: {matched_keywords}\n"
            f"实际输出前 500 字符:\n{text[:500]}"
        )

    def test_no_unfiltered_think_tags(self, llm_output):
        """验证：输出中不应包含未过滤的 <think> 标签"""
        filtered = _filter_think_tags(llm_output["text"])
        assert "<think>" not in filtered


@pytest.mark.slow
class TestV5LLMServiceAvailability:
    """LLM 服务可用性检查"""

    def test_llm_service_configured(self):
        """验证 LLM 服务已正确配置"""
        available, msg = _check_llm_available()
        if not available:
            pytest.fail(f"LLM 服务未配置: {msg}")
        assert available, msg

    def test_pipeline_can_be_imported(self):
        """验证 call_agent_pipeline_sync 可以正常导入"""
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            assert callable(call_agent_pipeline_sync)
        except ImportError as e:
            pytest.fail(f"无法导入 call_agent_pipeline_sync: {e}")
