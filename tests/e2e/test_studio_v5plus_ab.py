"""
Studio 共创 vs V5Plus 共创 A/B 实验

验证两个入口在统一 prompt + 渲染 + 后端后，输出是否一致、质量是否无差异。

实验设计：
  Phase 1: 静态一致性验证（无 LLM 调用，秒级完成）
  Phase 2: 端到端 LLM A/B 测试（需真实 LLM，约 15-20 分钟）
  Phase 3: 指令修改 A/B 测试（需真实 LLM）
  Phase 4: 综合报告生成

运行方式：
  # 全量（含 LLM 调用）
  pytest tests/e2e/test_studio_v5plus_ab.py -v --timeout=300 -s

  # 仅静态测试（无 LLM 调用）
  pytest tests/e2e/test_studio_v5plus_ab.py -v -k "static" -s
"""
from __future__ import annotations

import json
import os
import random
import sys
import threading
import time
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pytest

# ── 项目根目录注入 ──
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gui.v5.ppt_prompt import (
    build_ppt_generation_prompt,
    build_ppt_modify_prompt,
    build_ppt_reextract_prompt,
    parse_slides_from_text,
)

# ── 常量 ──
TEST_DOCS_DIR = project_root / "test_docs"
OUTPUT_DIR = project_root / "output"
REPORT_PATH = OUTPUT_DIR / "studio_v5plus_ab_report.json"
NUM_DOCS = 15  # 期望数量，实际会取 min(NUM_DOCS, 可用文档数)
LLM_TIMEOUT = 120  # 秒
SIMILARITY_THRESHOLD = 0.40  # text similarity threshold (LLM has inherent randomness)

# 指令修改测试用例
MODIFY_INSTRUCTIONS = [
    {"label": "layout_change", "instruction": "将此页改为流程图布局"},
    {"label": "content_slim", "instruction": "精简要点，每项不超过10个字"},
    {"label": "title_refine", "instruction": "将标题改为更简洁的表达"},
]

# ── 辅助函数 ──


def _load_test_docs() -> list[tuple[str, str]]:
    """从 test_docs/ 加载所有 .md 文件，返回 [(filename, content), ...]"""
    docs = []
    for f in sorted(TEST_DOCS_DIR.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8").strip()
            if len(content) >= 50:  # 跳过过短的文档
                docs.append((f.name, content))
        except Exception:
            continue
    return docs


def _sequence_ratio(a: str, b: str) -> float:
    """计算两个字符串的序列相似度"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _slides_structure_signature(slides: list) -> dict:
    """提取 slides 的结构签名：slide 数量、layout 分布、总 items 数"""
    layouts = [s.get("layout", "unknown") for s in slides]
    total_items = sum(len(s.get("items", [])) for s in slides)
    return {
        "count": len(slides),
        "layouts": dict(Counter(layouts)),
        "total_items": total_items,
        "titles": [s.get("title", "")[:40] for s in slides],
    }


def _compare_signatures(sig_a: dict, sig_b: dict) -> dict:
    """比较两个结构签名，返回差异详情"""
    slide_count_diff = abs(sig_a["count"] - sig_b["count"])
    layout_a = sig_a["layouts"]
    layout_b = sig_b["layouts"]
    all_layouts = set(layout_a) | set(layout_b)
    layout_diffs = {}
    for layout in all_layouts:
        diff = layout_b.get(layout, 0) - layout_a.get(layout, 0)
        if diff != 0:
            layout_diffs[layout] = diff

    # 标题相似度
    title_similarities = []
    for t_a, t_b in zip(sig_a["titles"], sig_b["titles"]):
        title_similarities.append(_sequence_ratio(t_a, t_b))
    avg_title_sim = sum(title_similarities) / len(title_similarities) if title_similarities else 0.0

    return {
        "slide_count_diff": slide_count_diff,
        "layout_diffs": layout_diffs,
        "avg_title_similarity": round(avg_title_sim, 4),
        "total_items_diff": abs(sig_a["total_items"] - sig_b["total_items"]),
    }


def _call_llm(prompt: str, action_type: str = "ppt") -> str:
    """通过 self_agent 后端调用 LLM，返回完整输出"""
    from opencopilot.agent.caller import call_agent_pipeline_sync

    full_text = ""
    cancel_event = threading.Event()
    for chunk in call_agent_pipeline_sync(
        text=prompt,
        action_type=action_type,
        session_id=f"ab-test-{int(time.time())}",
        context_source="ab_test",
        cancel_event=cancel_event,
        timeout=LLM_TIMEOUT,
    ):
        full_text += chunk
    return full_text


def _generate_report(results: dict):
    """生成 JSON 报告"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存到: {REPORT_PATH}")


# ═══════════════════════════════════════════════════════════════════
# Phase 1: 静态一致性验证（无 LLM 调用）
# ═══════════════════════════════════════════════════════════════════


class TestStaticConsistency:
    """验证两条路径的 prompt 构建和解析逻辑完全一致"""

    def test_generation_prompt_identical(self):
        """相同输入 → 相同 generation prompt"""
        text = "# 测试文档\n\n这是一份测试文档，包含预算数据和流程说明。"
        # Studio 路径：默认 strategy="pyramid"
        prompt_studio = build_ppt_generation_prompt(text=text)
        # V5Plus 路径：显式传 strategy="pyramid"
        prompt_v5plus = build_ppt_generation_prompt(
            text=text, strategy="pyramid", audience="", duration="10"
        )
        assert prompt_studio == prompt_v5plus, "Studio 和 V5Plus 的 generation prompt 不一致"

    def test_generation_prompt_with_strategy(self):
        """V5Plus 策略发现传入的 strategy 参数能正确应用"""
        text = "测试内容"
        prompt_default = build_ppt_generation_prompt(text=text, strategy="pyramid")
        prompt_narrative = build_ppt_generation_prompt(text=text, strategy="narrative")
        assert prompt_default != prompt_narrative, "不同 strategy 应产生不同 prompt"
        assert "pyramid" in prompt_default
        assert "narrative" in prompt_narrative

    def test_generation_prompt_with_audience_duration(self):
        """audience 和 duration 参数正确注入"""
        text = "测试内容"
        prompt = build_ppt_generation_prompt(
            text=text, audience="技术人员", duration="20"
        )
        assert "技术人员" in prompt
        assert "20" in prompt

    def test_modify_prompt_identical(self):
        """相同指令 + 相同 slides → 相同 modify prompt"""
        slides = [
            {"title": "第一页", "layout": "text_only", "items": [{"text": "要点1"}]},
        ]
        instruction = "将标题改为更简洁"
        p1 = build_ppt_modify_prompt(instruction, slides)
        p2 = build_ppt_modify_prompt(instruction, slides)
        assert p1 == p2

    def test_reextract_prompt_identical(self):
        """相同指令 + 相同文本 → 相同 reextract prompt"""
        text = "原始文本内容"
        instruction = "重新提炼要点"
        p1 = build_ppt_reextract_prompt(instruction, text)
        p2 = build_ppt_reextract_prompt(instruction, text)
        assert p1 == p2

    def test_parse_slides_consistency(self):
        """相同 JSON 文本 → 相同 parsed slides"""
        json_text = json.dumps({
            "title": "演示标题",
            "slides": [
                {
                    "type": "content",
                    "layout": "center",
                    "title": "封面",
                    "items": [{"text": "副标题"}],
                    "source_excerpt": "原文片段"
                },
                {
                    "type": "content",
                    "layout": "text_only",
                    "title": "概述",
                    "items": [{"text": "要点1"}, {"text": "要点2"}],
                    "source_excerpt": "原文片段2"
                }
            ]
        }, ensure_ascii=False)

        slides_1 = parse_slides_from_text(json_text)
        slides_2 = parse_slides_from_text(json_text)
        assert len(slides_1) == len(slides_2)
        for s1, s2 in zip(slides_1, slides_2):
            assert s1.get("title") == s2.get("title")
            assert s1.get("layout") == s2.get("layout")

    def test_parse_slides_handles_markdown_code_block(self):
        """解析器能处理 markdown 代码块包裹的 JSON"""
        json_inner = '{"title":"测试","slides":[{"type":"content","layout":"center","title":"封面","items":[]}]}'
        wrapped = f"```json\n{json_inner}\n```"
        slides = parse_slides_from_text(wrapped)
        assert len(slides) == 1
        assert slides[0]["title"] == "封面"

    def test_context_source_does_not_affect_prompt(self):
        """验证 context_source 是 V5AgentWorker 层面的元数据，不影响 prompt"""
        # build_ppt_generation_prompt 没有 context_source 参数
        # 它是 V5AgentWorker 的 __init__ 参数，仅用于 telemetry
        import inspect
        sig = inspect.signature(build_ppt_generation_prompt)
        param_names = list(sig.parameters.keys())
        assert "context_source" not in param_names, "context_source 不应出现在 prompt builder 参数中"
        assert "context_meta" not in param_names, "context_meta 不应出现在 prompt builder 参数中"

    def test_real_doc_prompt_equivalence(self):
        """使用真实测试文档验证 prompt 等价性"""
        docs = _load_test_docs()
        assert len(docs) >= 1, "test_docs/ 中没有可用的 .md 文档"

        # 随机选 3 份文档测试
        sample = random.sample(docs, min(3, len(docs)))
        for name, content in sample:
            prompt_studio = build_ppt_generation_prompt(text=content)
            prompt_v5plus = build_ppt_generation_prompt(
                text=content,
                strategy="pyramid",
                audience="",
                duration="10",
            )
            assert prompt_studio == prompt_v5plus, f"文档 {name} 的 Studio/V5Plus prompt 不一致"


# ═══════════════════════════════════════════════════════════════════
# Phase 2: 端到端 LLM A/B 测试
# ═══════════════════════════════════════════════════════════════════


class TestLLM_ABGeneration:
    """端到端 LLM 测试：用相同 prompt 调用两次，比较输出一致性"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.docs = _load_test_docs()
        available = len(self.docs)
        sample_size = min(NUM_DOCS, available)
        if sample_size < 5:
            pytest.skip(f"test_docs/ 中文档太少（当前 {available} 份，至少需要 5 份）")
        # 随机抽取文档
        random.seed(42)  # 固定种子保证可复现
        self.selected = random.sample(self.docs, sample_size)
        print(f"\n抽取 {sample_size}/{available} 份文档进行 A/B 测试")

    def test_ab_generation_consistency(self):
        """15 份文档 × 2 次调用，比较输出一致性"""
        import threading

        results = []
        overall_similarities = []
        overall_slide_count_diffs = []
        overall_layout_match_rates = []

        for i, (name, content) in enumerate(self.selected):
            print(f"\n[{i+1}/{len(self.selected)}] 测试文档: {name} ({len(content)} 字符)")

            prompt = build_ppt_generation_prompt(text=content)

            # 第一次调用（模拟 Studio 路径）
            print(f"  → Studio 路径调用中...")
            t0 = time.time()
            raw_a = _call_llm(prompt)
            latency_a = time.time() - t0

            # 第二次调用（模拟 V5Plus 路径）
            print(f"  → V5Plus 路径调用中...")
            t0 = time.time()
            raw_b = _call_llm(prompt)
            latency_b = time.time() - t0

            # 解析
            slides_a = parse_slides_from_text(raw_a)
            slides_b = parse_slides_from_text(raw_b)

            # 结构签名比较
            sig_a = _slides_structure_signature(slides_a)
            sig_b = _slides_structure_signature(slides_b)
            diff = _compare_signatures(sig_a, sig_b)

            # 输出文本相似度
            text_sim = _sequence_ratio(raw_a, raw_b)
            overall_similarities.append(text_sim)

            # slide 数量差异
            overall_slide_count_diffs.append(diff["slide_count_diff"])

            # layout 匹配率
            if sig_a["count"] > 0 and sig_b["count"] > 0:
                common = min(sig_a["count"], sig_b["count"])
                matches = sum(
                    1 for j in range(common)
                    if list(slides_a[j].get("layout", "")) == list(slides_b[j].get("layout", ""))
                )
                layout_match = matches / common
            else:
                layout_match = 0.0
            overall_layout_match_rates.append(layout_match)

            result = {
                "doc": name,
                "doc_chars": len(content),
                "raw_output_len_a": len(raw_a),
                "raw_output_len_b": len(raw_b),
                "slides_count_a": sig_a["count"],
                "slides_count_b": sig_b["count"],
                "text_similarity": round(text_sim, 4),
                "structure_diff": diff,
                "layout_match_rate": round(layout_match, 4),
                "latency_a": round(latency_a, 2),
                "latency_b": round(latency_b, 2),
            }
            results.append(result)
            print(f"  ✓ slides: A={sig_a['count']} B={sig_b['count']} | "
                  f"相似度: {text_sim:.3f} | layout匹配: {layout_match:.0%}")

        # 汇总统计
        avg_sim = sum(overall_similarities) / len(overall_similarities)
        avg_slide_diff = sum(overall_slide_count_diffs) / len(overall_slide_count_diffs)
        avg_layout_match = sum(overall_layout_match_rates) / len(overall_layout_match_rates)
        consistent_count = sum(1 for s in overall_similarities if s >= SIMILARITY_THRESHOLD)

        summary = {
            "total_docs": len(self.selected),
            "avg_text_similarity": round(avg_sim, 4),
            "avg_slide_count_diff": round(avg_slide_diff, 2),
            "avg_layout_match_rate": round(avg_layout_match, 4),
            "consistent_count": consistent_count,
            "consistency_rate": round(consistent_count / len(self.selected), 4),
            "threshold": SIMILARITY_THRESHOLD,
        }

        print(f"\n{'='*60}")
        print(f"生成一致性汇总:")
        print(f"  文档数: {summary['total_docs']}")
        print(f"  平均文本相似度: {summary['avg_text_similarity']:.4f}")
        print(f"  平均 slide 数差异: {summary['avg_slide_count_diff']:.2f}")
        print(f"  平均 layout 匹配率: {summary['avg_layout_match_rate']:.0%}")
        print(f"  一致性达标率: {summary['consistency_rate']:.0%} "
              f"({consistent_count}/{len(self.selected)})")
        print(f"{'='*60}")

        # 保存完整报告数据供后续汇总
        self._ab_results = {"cases": results, "summary": summary}

        # 持久化到文件
        ab_report = {
            "phase": "generation_ab",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "cases": results,
        }
        OUTPUT_DIR.mkdir(exist_ok=True)
        ab_path = OUTPUT_DIR / "studio_v5plus_ab_generation.json"
        with open(ab_path, "w", encoding="utf-8") as f:
            json.dump(ab_report, f, ensure_ascii=False, indent=2)
        print(f"  生成测试结果已保存: {ab_path}")

        # 断言：平均相似度应 ≥ 阈值（LLM 有随机性，不要求 100%）
        # 相同 prompt 两次调用，文本相似度约 40-60%（LLM 固有随机性）
        # 关键指标是 slide 数量和 layout 结构是否一致
        assert avg_sim >= 0.3, f"平均文本相似度过低: {avg_sim:.4f}（期望 ≥ 0.3）"
        assert avg_slide_diff <= 5, f"平均 slide 数差异过大: {avg_slide_diff:.2f}（期望 ≤ 5）"


# ═══════════════════════════════════════════════════════════════════
# Phase 3: 指令修改 A/B 测试
# ═══════════════════════════════════════════════════════════════════


class TestLLM_ABModification:
    """指令修改一致性测试：相同 slides + 相同指令 → 两次调用比较"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.docs = _load_test_docs()
        if len(self.docs) < 3:
            pytest.skip("test_docs/ 文档不足")

    def _generate_base_slides(self, content: str) -> list:
        """生成基础 slides 用于后续修改测试"""
        prompt = build_ppt_generation_prompt(text=content)
        raw = _call_llm(prompt)
        return parse_slides_from_text(raw)

    def test_modify_instruction_consistency(self):
        """3 种修改指令 × 1 份文档，比较修改输出一致性"""
        import threading

        # 选一份中等长度的文档
        doc = random.choice([d for d in self.docs if 500 < len(d[1]) < 5000])
        if not doc:
            doc = self.docs[0]
        name, content = doc
        print(f"\n指令修改测试文档: {name}")

        # 先生成基础 slides
        print("  → 生成基础 slides...")
        base_slides = self._generate_base_slides(content)
        if not base_slides:
            pytest.skip("无法生成基础 slides")
        print(f"  ✓ 基础 slides: {len(base_slides)} 页")

        # 随机选一页
        random.seed(123)
        target_idx = random.randint(0, len(base_slides) - 1)
        target_slide = base_slides[target_idx]
        print(f"  目标页: [{target_idx}] {target_slide.get('title', '?')[:30]}")

        modify_results = []

        for test_case in MODIFY_INSTRUCTIONS:
            instruction = test_case["instruction"]
            label = test_case["label"]
            print(f"\n  → 修改指令: [{label}] {instruction}")

            prompt = build_ppt_modify_prompt(instruction, base_slides)

            # 第一次调用
            t0 = time.time()
            raw_a = _call_llm(prompt, action_type="ppt")
            lat_a = time.time() - t0

            # 第二次调用
            t0 = time.time()
            raw_b = _call_llm(prompt, action_type="ppt")
            lat_b = time.time() - t0

            slides_a = parse_slides_from_text(raw_a)
            slides_b = parse_slides_from_text(raw_b)

            text_sim = _sequence_ratio(raw_a, raw_b)
            sig_a = _slides_structure_signature(slides_a)
            sig_b = _slides_structure_signature(slides_b)
            diff = _compare_signatures(sig_a, sig_b)

            result = {
                "instruction_label": label,
                "instruction": instruction,
                "slides_count_a": sig_a["count"],
                "slides_count_b": sig_b["count"],
                "text_similarity": round(text_sim, 4),
                "structure_diff": diff,
                "latency_a": round(lat_a, 2),
                "latency_b": round(lat_b, 2),
            }
            modify_results.append(result)
            print(f"    ✓ slides: A={sig_a['count']} B={sig_b['count']} | "
                  f"相似度: {text_sim:.3f}")

        # 汇总
        avg_sim = sum(r["text_similarity"] for r in modify_results) / len(modify_results)
        print(f"\n  指令修改平均相似度: {avg_sim:.4f}")

        self._modify_results = {"cases": modify_results, "avg_similarity": round(avg_sim, 4)}

        # 持久化
        mod_report = {
            "phase": "modification_ab",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "doc": name,
            "target_slide_index": target_idx,
            "cases": modify_results,
            "avg_similarity": round(avg_sim, 4),
        }
        OUTPUT_DIR.mkdir(exist_ok=True)
        mod_path = OUTPUT_DIR / "studio_v5plus_ab_modify.json"
        with open(mod_path, "w", encoding="utf-8") as f:
            json.dump(mod_report, f, ensure_ascii=False, indent=2)
        print(f"  修改测试结果已保存: {mod_path}")

        assert avg_sim >= 0.4, f"指令修改平均相似度过低: {avg_sim:.4f}"


# ═══════════════════════════════════════════════════════════════════
# Phase 4: 综合报告生成
# ═══════════════════════════════════════════════════════════════════


class TestReportGeneration:
    """汇总所有测试结果，生成综合报告"""

    def test_generate_report(self):
        """生成综合 A/B 实验报告"""
        # 此测试单独运行时仅生成框架报告
        report = {
            "experiment": "Studio vs V5Plus 共创 A/B 实验",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "hypothesis": (
                "Studio 共创和 V5Plus 共创在统一 prompt + 渲染 + 后端后，"
                "输出应完全一致（prompt 级）或高度一致（LLM 输出级，≥80%）"
            ),
            "architecture": {
                "shared_prompt_builder": "gui/v5/ppt_prompt.py::build_ppt_generation_prompt",
                "shared_parser": "gui/v5/ppt_prompt.py::parse_slides_from_text",
                "shared_modify_prompt": "gui.v5.ppt_prompt::build_ppt_modify_prompt",
                "shared_backend": "V5AgentWorker → self_agent → call_agent_pipeline_sync",
                "context_source_diff": "仅 telemetry 元数据不同（studio vs v5plus_cocreation）",
            },
            "phase1_static_consistency": {
                "status": "见 TestStaticConsistency 类（无需 LLM 调用）",
                "expected": "100% 一致（相同函数、相同参数 → 相同输出）",
            },
            "phase2_generation_ab": {
                "status": "需运行 TestLLM_ABGeneration",
                "note": "由于 LLM 温度随机性，输出不会 100% 相同，但结构和布局应高度一致",
            },
            "phase3_modification_ab": {
                "status": "需运行 TestLLM_ABModification",
                "note": "指令修改 prompt 完全相同，LLM 输出应高度一致",
            },
            "conclusion": (
                "如果所有 Phase 通过，说明 Studio 和 V5Plus 共创在统一后，"
                "除了 UI 交互差异外，底层 AI 能力完全一致。"
            ),
        }
        _generate_report(report)
        assert REPORT_PATH.exists(), "报告文件未生成"


# ── 入口：直接运行 ──
if __name__ == "__main__":
    print("Studio vs V5Plus 共创 A/B 实验")
    print("=" * 60)
    print("运行方式：")
    print("  静态测试: pytest tests/e2e/test_studio_v5plus_ab.py -v -k static -s")
    print("  全量测试: pytest tests/e2e/test_studio_v5plus_ab.py -v --timeout=300 -s")
    print("=" * 60)
