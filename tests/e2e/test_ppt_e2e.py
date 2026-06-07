"""
PPT 生成端到端集成测试

验证完整的 PPT 生成流程：
  persona 加载 → action_type 映射 → Pipeline 调用 → LLM 输出 → JSON 解析

覆盖场景：
  1. Persona 文件完整性与映射表验证（离线）
  2. Studio Tab PPT 生成全链路（真实 LLM）
  3. LLM 输出质量评估（结构化校验）

注意：标记为 @pytest.mark.slow 的用例消耗真实 LLM token。
运行方式：
  pytest tests/e2e/test_ppt_e2e.py -v --timeout=120
  # 仅离线测试：pytest tests/e2e/test_ppt_e2e.py -v -m "not slow"
"""

from __future__ import annotations

import os
import re
import sys
import json
import uuid
import signal
import threading
from pathlib import Path
from typing import List, Dict, Any

import pytest

# ── 项目根目录注入 ──
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ── 常量 ──
LLM_TIMEOUT_SECONDS = 90
COLLECT_TIMEOUT_SECONDS = 80
MIN_PPT_OUTPUT_LENGTH = 100
REQUIRED_PERSONAS = ["default", "chat", "code", "ppt", "translate", "polish"]
EXPECTED_ACTION_MAPPING = {
    "coding": "code",
    "code_review": "code",
    "translation": "translate",
}

# 测试用文档素材
TEST_DOCUMENT = """# 2025年度预算报告

## 一、总体概况

2025年公司总预算为5000万元，较2024年增长15%。主要投入方向：
- 研发投入：2000万元（占40%）
- 市场推广：1200万元（占24%）
- 人力资源：1000万元（占20%）
- 运营支出：800万元（占16%）

## 二、研发投入明细

| 项目 | 预算（万元） | 占比 |
|------|-------------|------|
| AI平台 | 800 | 40% |
| 云服务 | 600 | 30% |
| 数据中台 | 400 | 20% |
| 安全合规 | 200 | 10% |

## 三、关键里程碑

1. Q1：AI平台 v2.0 上线
2. Q2：完成B轮融资
3. Q3：海外市场拓展启动
4. Q4：年度营收突破1亿元

## 四、风险与应对

- 技术风险：AI模型迭代速度加快，需持续投入研发
- 市场风险：竞争加剧，需差异化定位
- 人才风险：核心技术人才流失风险，需完善激励机制
"""


# ═══════════════════════════════════════════════════
# Part 1: 离线测试（不依赖 LLM）
# ═══════════════════════════════════════════════════

class TestPersonaIntegrity:
    """Persona 文件完整性与映射表验证"""

    def test_required_persona_files_exist(self):
        """所有必需的 persona 文件应存在且非空"""
        personas_dir = project_root / "personas"
        for name in REQUIRED_PERSONAS:
            path = personas_dir / f"{name}.md"
            assert path.exists(), f"Missing persona file: {path}"
            size = path.stat().st_size
            assert size > 50, f"Persona file too small ({size} bytes): {path}"

    def test_ppt_persona_content_quality(self):
        """ppt.md 应包含 PPT 生成相关指令"""
        personas_dir = project_root / "personas"
        content = (personas_dir / "ppt.md").read_text(encoding="utf-8")
        assert len(content) > 200, f"ppt.md 内容过短 ({len(content)} chars)"
        # 应包含 JSON 输出格式要求
        assert "json" in content.lower() or "JSON" in content, "ppt.md 应包含 JSON 输出格式要求"
        # 应包含幻灯片结构相关指令
        assert any(kw in content for kw in ["幻灯片", "slide", "大纲", "layout"]), \
            "ppt.md 应包含幻灯片结构相关指令"

    def test_persona_mapping_in_config(self):
        """ConfigManager 应提供 persona_mapping"""
        from config_manager import ConfigManager, DEFAULT_PERSONA_MAPPING

        cfg = ConfigManager.get_instance()
        mapping = cfg.get_persona_mapping()

        assert isinstance(mapping, dict), "persona_mapping 应为 dict"
        # 验证默认映射包含关键条目
        for action_type, expected_persona in EXPECTED_ACTION_MAPPING.items():
            assert mapping.get(action_type) == expected_persona, \
                f"映射 {action_type} → {expected_persona} 缺失，实际: {mapping.get(action_type)}"

    def test_persona_mapping_coding_to_code(self):
        """action_type='coding' 应映射到 'code' persona"""
        from config_manager import ConfigManager
        mapping = ConfigManager.get_instance().get_persona_mapping()
        assert mapping.get("coding") == "code"

    def test_load_persona_with_mapping(self):
        """load_persona('coding') 应通过映射加载 personas/code.md"""
        from opencopilot.shared.prompt import load_persona

        # "coding" 没有 personas/coding.md，但映射到 "code" → personas/code.md
        result = load_persona("coding")
        assert len(result) > 20, f"coding persona 过短 ({len(result)} chars)，可能回退到 default"
        # code.md 应包含代码相关内容
        assert any(kw in result for kw in ["代码", "code", "编程", "程序"]), \
            "coding → code persona 应包含代码相关内容"

    def test_load_persona_direct_match(self):
        """load_persona('ppt') 应直接匹配 personas/ppt.md"""
        from opencopilot.shared.prompt import load_persona

        result = load_persona("ppt")
        assert len(result) > 200, f"ppt persona 过短 ({len(result)} chars)"

    def test_load_persona_subdirectory(self):
        """load_persona 应支持子目录路径格式"""
        from opencopilot.shared.prompt import load_persona

        # personas/office/business/presentation.md 存在
        result = load_persona("office/business/presentation")
        assert len(result) > 50, f"子目录 persona 过短 ({len(result)} chars)，可能回退到 default"
        # 应包含演示相关指令
        assert any(kw in result for kw in ["演示", "presentation", "幻灯片", "slide"]), \
            "office/business/presentation 应包含演示相关内容"

    def test_load_persona_fallback_to_default(self):
        """不存在的 persona 应回退到 default.md"""
        from opencopilot.shared.prompt import load_persona

        result = load_persona("nonexistent_persona_xyz")
        default = load_persona("default")
        assert result == default, "不存在的 persona 应回退到 default"

    def test_context_source_studio_defined(self):
        """'studio' context_source 应有定义"""
        from opencopilot.shared.prompt import CONTEXT_DESCRIPTIONS, CONTEXT_SOURCE_PRIORITY

        assert "studio" in CONTEXT_DESCRIPTIONS, "CONTEXT_DESCRIPTIONS 缺少 'studio'"
        assert "studio" in CONTEXT_SOURCE_PRIORITY, "CONTEXT_SOURCE_PRIORITY 缺少 'studio'"
        assert CONTEXT_SOURCE_PRIORITY["studio"] == "medium"


# ═══════════════════════════════════════════════════
# Part 2: PPT Prompt 构建验证（离线）
# ═══════════════════════════════════════════════════

class TestPPTPromptConstruction:
    """验证 PPT 生成的 Prompt 构建质量"""

    def test_full_prompt_with_studio_context(self):
        """Studio 上下文的完整 prompt 应包含所有必要部分"""
        from opencopilot.shared.prompt import build_full_prompt

        prompt = build_full_prompt(
            action_type="ppt",
            context_source="studio",
            context_content=TEST_DOCUMENT[:500],
            context_meta={},
            persona_name="ppt",
        )

        assert len(prompt) > 500, f"prompt 过短 ({len(prompt)} chars)"
        # 应包含 Studio 上下文描述
        assert "Studio" in prompt or "工作台" in prompt, "缺少 Studio 上下文描述"
        # 应包含 PPT persona 内容
        assert "json" in prompt.lower() or "JSON" in prompt, "缺少 JSON 输出格式要求"
        # 应包含用户输入
        assert "预算" in prompt or "2025" in prompt, "缺少用户输入内容"

    def test_prompt_length_with_long_document(self):
        """长文档输入应生成合理长度的 prompt"""
        from opencopilot.shared.prompt import build_full_prompt

        prompt = build_full_prompt(
            action_type="ppt",
            context_source="studio",
            context_content=TEST_DOCUMENT,
            context_meta={},
            persona_name="ppt",
        )

        # prompt 应合理长
        assert len(prompt) > 1000, f"长文档 prompt 过短 ({len(prompt)} chars)"
        # 但不应过长（超过 100K 字符可能有问题）
        assert len(prompt) < 100000, f"prompt 过长 ({len(prompt)} chars)"


# ═══════════════════════════════════════════════════
# Part 3: PPT JSON 解析验证（离线）
# ═══════════════════════════════════════════════════

class TestPPTJsonParsing:
    """验证 LLM 输出的 JSON 解析鲁棒性"""

    def _extract_json_array(self, text: str) -> list | None:
        """从 LLM 输出中提取 JSON 数组"""
        # 尝试直接解析
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        match = re.search(r'```(?:json)?\s*\n?(\[.*?\])\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试查找首个 [ 到最后一个 ]
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        return None

    def test_parse_clean_json(self):
        """直接 JSON 数组输出"""
        text = '[{"type":"title","layout":"center","title":"测试","subtitle":"副标题"}]'
        result = self._extract_json_array(text)
        assert result is not None
        assert len(result) == 1
        assert result[0]["type"] == "title"

    def test_parse_markdown_wrapped_json(self):
        """```json 包裹的 JSON 输出"""
        text = '```json\n[{"type":"title","layout":"center","title":"测试","subtitle":"2025"}]\n```'
        result = self._extract_json_array(text)
        assert result is not None
        assert result[0]["title"] == "测试"

    def test_parse_json_with_preamble(self):
        """带前言文字的 JSON 输出"""
        text = '以下是生成的PPT大纲：\n[{"type":"title","layout":"center","title":"预算报告","subtitle":"2025"}]'
        result = self._extract_json_array(text)
        assert result is not None
        assert result[0]["title"] == "预算报告"

    def test_validate_slide_structure(self):
        """验证幻灯片结构完整性"""
        slides = [
            {"type": "title", "layout": "center", "title": "封面", "subtitle": "2025"},
            {"type": "content", "layout": "text_only", "title": "概况", "items": [
                {"level": 0, "text": "总预算5000万"}
            ]},
        ]

        for slide in slides:
            assert "type" in slide, "每个 slide 应有 type 字段"
            assert slide["type"] in ("title", "content"), f"不支持的 type: {slide['type']}"
            assert "layout" in slide, "每个 slide 应有 layout 字段"
            assert "title" in slide, "每个 slide 应有 title 字段"

        # title 页的 layout 应为 center
        assert slides[0]["layout"] == "center"
        # content 页的 layout 应为有效值
        valid_layouts = {"text_only", "image_right", "three_columns", "two_columns", "center"}
        assert slides[1]["layout"] in valid_layouts


# ═══════════════════════════════════════════════════
# Part 4: 真实 LLM 端到端测试
# ═══════════════════════════════════════════════════

def _check_llm_available() -> tuple:
    """检查 LLM 服务是否可用"""
    try:
        from llm_provider import load_config
        cfg = load_config()
        provider_type = cfg.get("provider_type", "mimo")
        if provider_type in ("mimo", "minimax"):
            api_key = cfg.get(f"{provider_type}_api_key") or os.environ.get(
                "XIAOMI_API_KEY" if provider_type == "mimo" else "MINIMAX_API_KEY"
            )
            if not api_key:
                return False, f"{provider_type} API key 未配置"
        elif provider_type == "local":
            return True, f"Local provider ({cfg.get('local_api_base', 'localhost')})"
        return True, f"{provider_type} provider 已配置"
    except Exception as e:
        return False, f"检查 LLM 配置出错: {e}"


def _collect_pipeline_output(
    prompt: str,
    action_type: str,
    context_source: str = "studio",
    context_meta: dict | None = None,
    timeout: int = COLLECT_TIMEOUT_SECONDS,
) -> tuple:
    """调用 pipeline 并收集全部输出"""
    from opencopilot.agent.caller import call_agent_pipeline_sync

    full_text = ""
    chunk_count = 0
    cancel_event = threading.Event()

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
            session_id=f"e2e-ppt-{uuid.uuid4().hex[:8]}",
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

        signal.alarm(0)
    except TimeoutError:
        raise RuntimeError(f"LLM 调用超时（>{timeout}秒）")
    finally:
        if old_handler is not None:
            signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

    return full_text, chunk_count


def _extract_json_array(text: str) -> list | None:
    """从 LLM 输出中提取 JSON 数组"""
    # 过滤 think 标签
    display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in display:
        display = display.split("<think>")[0]

    try:
        result = json.loads(display)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    match = re.search(r'```(?:json)?\s*\n?(\[.*?\])\s*```', display, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    start = display.find('[')
    end = display.rfind(']')
    if start != -1 and end > start:
        try:
            return json.loads(display[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


@pytest.mark.slow
class TestPPTEndToEnd:
    """PPT 生成端到端测试（真实 LLM 调用）"""

    @pytest.fixture(scope="class")
    def ppt_output(self):
        """Fixture: 调用 PPT 生成获取真实 LLM 输出"""
        available, msg = _check_llm_available()
        if not available:
            pytest.skip(f"LLM 服务不可用: {msg}")

        prompt = f"请根据以下文档内容生成PPT大纲：\n\n{TEST_DOCUMENT}"

        try:
            full_text, chunk_count = _collect_pipeline_output(
                prompt=prompt,
                action_type="ppt",
                context_source="studio",
                context_meta={},
            )
        except RuntimeError as e:
            pytest.fail(f"LLM 调用失败: {e}")

        return {"text": full_text, "chunks": chunk_count}

    def test_output_not_empty(self, ppt_output):
        """输出不应为空"""
        assert ppt_output["text"], "LLM 输出不应为空"
        assert len(ppt_output["text"]) >= MIN_PPT_OUTPUT_LENGTH, \
            f"输出过短 ({len(ppt_output['text'])} chars)"

    def test_output_has_chunks(self, ppt_output):
        """应有多个 streaming chunks"""
        assert ppt_output["chunks"] > 5, f"chunks 过少 ({ppt_output['chunks']})"

    def test_output_parseable_as_json(self, ppt_output):
        """输出应能解析为 JSON 数组"""
        slides = _extract_json_array(ppt_output["text"])
        assert slides is not None, f"无法解析为 JSON 数组。输出前 500 字符:\n{ppt_output['text'][:500]}"
        assert len(slides) >= 2, f"幻灯片数不足（至少2页），实际: {len(slides)}"

    def test_slides_have_title_page(self, ppt_output):
        """应包含封面页（type=title）"""
        slides = _extract_json_array(ppt_output["text"])
        if slides is None:
            pytest.skip("JSON 解析失败")

        title_slides = [s for s in slides if s.get("type") == "title"]
        assert len(title_slides) >= 1, "应包含至少一个封面页"

    def test_slides_have_content_pages(self, ppt_output):
        """应包含内容页（type=content）"""
        slides = _extract_json_array(ppt_output["text"])
        if slides is None:
            pytest.skip("JSON 解析失败")

        content_slides = [s for s in slides if s.get("type") == "content"]
        assert len(content_slides) >= 1, "应包含至少一个内容页"

    def test_slides_layout_diversity(self, ppt_output):
        """应使用多种版式"""
        slides = _extract_json_array(ppt_output["text"])
        if slides is None:
            pytest.skip("JSON 解析失败")

        layouts = set(s.get("layout", "") for s in slides)
        assert len(layouts) >= 2, f"版式种类不足（至少2种），实际: {layouts}"

    def test_slides_content_relevance(self, ppt_output):
        """内容应与原文档相关"""
        slides = _extract_json_array(ppt_output["text"])
        if slides is None:
            pytest.skip("JSON 解析失败")

        all_text = json.dumps(slides, ensure_ascii=False)
        # 应包含文档中的关键信息
        keywords = ["预算", "2025", "5000"]
        hits = sum(1 for kw in keywords if kw in all_text)
        assert hits >= 2, f"关键信息命中不足 ({hits}/3)，关键词: {keywords}"

    def test_no_think_tags_in_display(self, ppt_output):
        """过滤 think 标签后应能正常解析"""
        text = ppt_output["text"]
        display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        if "<think>" in display:
            display = display.split("<think>")[0]

        # 过滤后应仍有有效内容
        assert len(display.strip()) > 50, "过滤 think 标签后内容过短"


# ═══════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════

class TestPPTESummary:
    """测试汇总"""

    def test_summary(self):
        """输出测试覆盖摘要"""
        summary = """
╔══════════════════════════════════════════════════════════════╗
║  PPT 生成端到端集成测试覆盖                                    ║
╠══════════════════════════════════════════════════════════════╣
║  Part 1 - 离线: Persona 完整性 + 映射表 + 子目录路径           ║
║  Part 2 - 离线: Prompt 构建质量验证                           ║
║  Part 3 - 离线: JSON 解析鲁棒性                               ║
║  Part 4 - LLM:  全链路 PPT 生成 + 质量评估                    ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(summary)
        assert True
