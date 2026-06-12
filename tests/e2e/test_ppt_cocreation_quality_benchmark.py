#!/usr/bin/env python3
"""
PPT 生成 + 共创自由指令 质量评测脚本

评测维度:
1. PPT 初始生成质量（4阶段管线）
2. 共创模式下自由指令执行质量（随机多指令抽样）

指令分类（可穷举）:
  A. 结构操作: 增页/减页/插入页
  B. 标题编辑: 改标题/改副标题
  C. 内容提炼: 重新聚焦/精简/提取关键结论
  D. 叙述风格: 商务正式/口语化/数据驱动/故事叙述
  E. 视觉转换: 图表/表格/流程图/图文混排
  F. 文案润色: 润色/重写/优化措辞
  G. 复合指令: 标题+图表/精简+表格
  H. 全量操作: 重新生成/换主题

随机策略: 每轮从 8 类各抽 1-2 条，共 3 轮不同随机种子
"""

import json
import os
import random
import sys
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from opencopilot.evaluation import JudgeBudget, evaluate_cocreation_output

JUDGE_BUDGET = JudgeBudget.from_env(default_max_cases=24)
FAITHFUL_REWRITE_DATASET_PATH = PROJECT_ROOT / "tests" / "test_data" / "ppt_faithful_rewrite_cases.json"


# ============================================================
# 样本文档
# ============================================================
SAMPLE_DOCS = {
    "tech_report": {
        "label": "AI Agent 技术报告",
        "text": """# 2026 年 AI Agent 发展趋势报告

## 市场规模与增长
2025年全球AI Agent市场规模达到120亿美元，同比增长85%。
中国市场占比从2024年的12%增长到2025年的18%，达到约21.6亿美元。
预计2026年全球市场将突破250亿美元。

## 技术架构演进
当前主流架构从单体大模型调用，演变为"规划-执行-反思"三阶段循环。
核心组件包括：任务分解器、工具调用链、记忆系统、多智能体协调器。
Multi-Agent 架构逐渐成为企业级应用的主流选择。

## 关键应用场景
1. 代码开发与审查：AI Agent 辅助编码效率提升 40%
2. 文档生成与处理：自动化报告、PPT、合同生成
3. 客户服务：智能客服替代率达到 65%
4. 数据分析：从自然语言到结构化查询的自动转换

## 挑战与风险
- 幻觉问题：复杂任务下仍有 15% 的错误率
- 安全合规：数据隐私和权限控制是企业最大顾虑
- 成本控制：单次复杂任务调用成本约 0.5-2 美元
- 人机协作：完全自主模式在高风险场景仍需人工审核

## 2026 展望
- 本地化小模型 + 云端大模型的混合架构将成为主流
- Agent-as-a-Service 平台快速兴起
- 标准化协议（如 MCP、A2A）推动跨平台互操作
"""
    },
    "business_proposal": {
        "label": "产品商业计划书",
        "text": """# SmartOffice 智能办公平台商业计划书

## 项目背景
传统办公软件已无法满足远程协作和智能决策的需求。
企业每年在低效办公流程上浪费超过 30% 的工作时间。
AI 驱动的办公自动化正在成为企业数字化的核心赛道。

## 产品定位
SmartOffice 定位为"AI 原生的企业办公中枢"。
核心理念：让 AI 处理 80% 的重复性工作，人专注 20% 的创造性工作。
目标用户：50-500 人的中型企业，知识工作者占比 >60%。

## 核心功能
1. 智能文档协作：AI 辅助写作、实时翻译、多格式互转
2. 自动化工作流：审批、日程、会议纪要自动生成
3. 数据看板：自然语言查询业务数据，自动生成可视化报告
4. 知识图谱：企业知识库构建与智能检索

## 商业模式
- SaaS 订阅：基础版 99元/人/月，专业版 299元/人/月
- 企业定制：按需部署，年费 50-200 万元
- API 服务：按调用量计费，0.01 元/次

## 团队与融资
核心团队 15 人，来自 BAT 和头部 AI 公司。
已完成天使轮 1000 万元，计划 2026 Q3 完成 A 轮 5000 万元。
预计 2027 年实现盈亏平衡，2028 年 ARR 突破 1 亿元。
"""
    },
}


# ============================================================
# 指令分类池（可穷举的共创自由指令）
# ============================================================
SIMPLE_INSTRUCTION_POOL: Dict[str, List[Dict[str, str]]] = {
    "A_structure": [  # 结构操作
        {"instruction": "在第2页后面新增一页，内容是团队优势分析", "label": "插入新页"},
        {"instruction": "删除第3页", "label": "删除指定页"},
        {"instruction": "添加一页目录，列出所有章节", "label": "添加目录页"},
        {"instruction": "在最后一页之前加一页总结", "label": "添加总结页"},
        {"instruction": "去掉第二页，内容太冗余了", "label": "删除冗余页"},
    ],
    "B_title": [  # 标题编辑
        {"instruction": "第1页标题改为'2026年AI智能体全景报告'", "label": "改封面标题"},
        {"instruction": "把当前页的标题改得更吸引人一些", "label": "优化标题吸引力"},
        {"instruction": "副标题改为'数据驱动的未来办公'", "label": "改副标题"},
        {"instruction": "标题用一个结论性的陈述来替代", "label": "结论型标题"},
    ],
    "C_refocus": [  # 内容提炼/重新聚焦
        {"instruction": "重新提炼这一页的核心要点，只保留最重要的3条", "label": "精简到3条"},
        {"instruction": "聚焦于数据部分，去掉描述性文字", "label": "聚焦数据"},
        {"instruction": "把当前页内容压缩为一段简洁的摘要", "label": "压缩为摘要"},
        {"instruction": "提取关键结论，用bullet point展示", "label": "提取结论"},
        {"instruction": "围绕'成本效益'重新组织这一页的内容", "label": "围绕主题重组"},
    ],
    "D_style": [  # 叙述风格调整
        {"instruction": "调整为更正式的商务汇报风格", "label": "商务正式"},
        {"instruction": "改为口语化、更亲切的表达方式", "label": "口语亲切"},
        {"instruction": "用数据驱动的方式重新表述，突出数字和对比", "label": "数据驱动"},
        {"instruction": "改为讲故事的方式，增加叙述的连贯性", "label": "故事叙述"},
        {"instruction": "用更简洁精炼的语言重写，去掉冗余", "label": "极简风格"},
    ],
    "E_visual": [  # 视觉转换
        {"instruction": "把当前页的数据转为柱状图展示", "label": "转柱状图"},
        {"instruction": "用表格展示这些对比信息", "label": "转表格"},
        {"instruction": "把流程步骤转为流程图", "label": "转流程图"},
        {"instruction": "改为图文混排的版式，右边放配图", "label": "图文混排"},
        {"instruction": "把关键数据做成饼图展示占比", "label": "转饼图"},
    ],
    "F_polish": [  # 文案润色
        {"instruction": "润色当前页的所有文字，让表达更专业", "label": "专业化润色"},
        {"instruction": "重写这些要点，每一条都用一句话概括", "label": "一句话概括"},
        {"instruction": "优化措辞，让文案更有说服力", "label": "增强说服力"},
        {"instruction": "检查并修正文案中的语法和表达问题", "label": "语法修正"},
    ],
    "G_compound": [  # 复合指令
        {"instruction": "改标题为'核心优势'，并把要点精简到4条", "label": "标题+精简"},
        {"instruction": "重新组织内容，转为表格，标题改为'对比分析'", "label": "重组+表格+标题"},
        {"instruction": "把数据提取出来做图表，文字部分精简为一句话总结", "label": "图表+总结"},
        {"instruction": "改为商务风格并重写标题，突出数据对比", "label": "风格+标题+数据"},
    ],
    "H_global": [  # 全量操作
        {"instruction": "重新生成所有页面的内容", "label": "重新生成"},
        {"instruction": "整体调整为主题色系深蓝的商务风格", "label": "换主题风格"},
        {"instruction": "所有页面的标题都改为更短的关键词形式", "label": "批量改标题"},
    ],
}

COMPLEX_INSTRUCTION_POOL: Dict[str, List[Dict[str, str]]] = {
    "A_structure": [
        {"instruction": "在第2页后面新增一页团队优势分析，并把新页做成三列结构，要求保持商务正式风格且不要改封面和结束页", "label": "新增页+风格约束"},
        {"instruction": "删除当前页里最冗余的一部分内容，如果删除后结构不完整，就自动补一页总结，但不要动最后一页", "label": "删减并补总结"},
    ],
    "B_title": [
        {"instruction": "把当前页和下一页标题都改成结论句式，要求前后呼应、每个标题不超过16字，正文内容不要改", "label": "双页结论标题"},
        {"instruction": "把当前页标题改得更像董事会汇报结论，同时保留原有专业术语，不要改变正文和版式", "label": "董事会结论标题"},
    ],
    "C_refocus": [
        {"instruction": "把当前页重构成3个关键结论，每条都必须保留一个数据事实，并删掉与结论无关的描述，保持当前版式", "label": "三结论+保数据"},
        {"instruction": "围绕'成本效益'重新组织这一页，但必须保留风险提示和一个可执行动作项，输出成三段结构", "label": "主题重组+保风险"},
    ],
    "D_style": [
        {"instruction": "把当前页改成董事会汇报风格：保留所有关键数据，减少形容词，增加一条风险提示，并把要点控制在4条以内", "label": "董事会风格+风险"},
        {"instruction": "把当前页改成更正式的商务风格，同时补一条面向高层的结论句，要求语言更克制但不能丢失关键数字", "label": "商务风格+结论"},
    ],
    "E_visual": [
        {"instruction": "先判断当前页哪些信息适合转表格、哪些适合转图表，只能二选一落地；如果数据不足就补一句结论型说明，并保留原标题", "label": "先判断再落地"},
        {"instruction": "把当前页中最适合比较的两组信息改成表格，同时保留一条文本结论，不能新增页面", "label": "表格+文本结论"},
    ],
    "F_polish": [
        {"instruction": "把当前页每条文案压缩成一句话，但必须保留数字、专有名词和因果关系，不能改变原有顺序", "label": "压缩且保关键信息"},
        {"instruction": "润色当前页文案，让表达更专业，但每条必须保留一个事实依据，不能写成空泛口号", "label": "专业化且保事实"},
    ],
    "G_compound": [
        {"instruction": "把当前页改成商务风格并重写标题，再把其中两组对比信息转成表格，最后补一句结论，且不能新增页面", "label": "风格+标题+表格+结论"},
        {"instruction": "重写标题、精简正文到4条、把可量化信息提成一个图表说明，同时保留一条风险提醒", "label": "标题+精简+图表+风险"},
    ],
    "H_global": [
        {"instruction": "从当前页开始连续优化后面两页：统一为深蓝商务风格，标题改成结论句，重复信息合并，最后一页保持不动", "label": "连续两页重构"},
        {"instruction": "重新生成当前页及下一页内容，但要保持整份 PPT 的叙事连贯，不能重复已有观点，并保留结束页不动", "label": "双页重生成+防重复"},
    ],
}


def _load_faithful_rewrite_instruction_pool() -> Dict[str, List[Dict[str, Any]]]:
    payload = json.loads(FAITHFUL_REWRITE_DATASET_PATH.read_text(encoding="utf-8"))
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for case in payload.get("cases", []):
        category = str(case.get("category", "F_polish"))
        grouped.setdefault(category, []).append(case)
    for category, cases in grouped.items():
        cases.sort(key=lambda item: str(item.get("case_id", item.get("label", ""))))
    return grouped


def _load_instruction_pool() -> tuple[str, Dict[str, List[Dict[str, Any]]]]:
    mode = os.getenv("OPEN_COPILOT_PPT_TASK_MODE", "complex").strip().lower()
    if mode == "simple":
        return "simple", SIMPLE_INSTRUCTION_POOL
    if mode == "faithful_rewrite":
        return "faithful_rewrite", _load_faithful_rewrite_instruction_pool()
    return "complex", COMPLEX_INSTRUCTION_POOL


def _build_round_samples(
    task_mode: str,
    instruction_pool: Dict[str, List[Dict[str, Any]]],
    base_slides: Dict[str, list],
    rng: random.Random | None,
    samples_per_round: int,
) -> List[tuple[str, Dict[str, Any], str, int]]:
    round_samples: List[tuple[str, Dict[str, Any], str, int]] = []

    if task_mode == "faithful_rewrite":
        for cat_key, pool in instruction_pool.items():
            for instr_def in pool:
                doc_key = str(instr_def.get("doc_key", ""))
                slides = base_slides.get(doc_key, [])
                if not slides:
                    continue
                current_index = int(instr_def.get("current_index", 0))
                current_index = max(0, min(current_index, len(slides) - 1))
                round_samples.append((cat_key, instr_def, doc_key, current_index))
        return round_samples

    assert rng is not None
    for cat_key, pool in instruction_pool.items():
        k = min(samples_per_round, len(pool))
        sampled = rng.sample(pool, k)
        for instr_def in sampled:
            doc_key = rng.choice(list(base_slides.keys()))
            slides = base_slides.get(doc_key, [])
            if not slides:
                continue
            current_index = rng.randint(0, max(0, len(slides) - 1))
            round_samples.append((cat_key, instr_def, doc_key, current_index))
    return round_samples


# ============================================================
# 数据结构
# ============================================================
@dataclass
class InstructionResult:
    category: str
    instruction: str
    label: str
    backend: str
    success: bool
    latency_ms: float
    raw_length: int
    render_command_count: int
    parse_success: bool
    current_page_hit: bool
    expected_type_hit: bool
    quality_score: float
    rule_score: float
    embedding_score: float
    semantic_score: float
    accuracy_score: float
    embedding_backend: str
    judge_score: float | None
    judge_applied: bool
    judge_summary: str
    preview: str
    error: str = ""


@dataclass
class GenerationResult:
    doc_key: str
    doc_label: str
    success: bool
    total_pages: int
    topics: list
    stage_durations: Dict[str, float]
    latency_ms: float
    slides_preview: str
    error: str = ""


@dataclass
class Evaluator:
    """PPT 共创指令质量评估器"""

    @staticmethod
    def evaluate_instruction(
        raw_output: str,
        instruction: str,
        category: str,
        current_index: int,
        slides_data: list,
        judge_budget: JudgeBudget | None = None,
    ) -> Dict[str, Any]:
        """评估单条指令的输出质量"""
        scores = {}

        # 1. 非空检查 (10%)
        has_content = len(raw_output.strip()) > 0
        scores["not_empty"] = 1.0 if has_content else 0.0

        # 2. 长度合理性 (10%)
        length = len(raw_output.strip())
        if length > 50:
            scores["length_ok"] = 1.0
        elif length > 20:
            scores["length_ok"] = 0.5
        else:
            scores["length_ok"] = 0.2

        # 3. render_commands 解析 (25%)
        render_commands = Evaluator._extract_render_commands(raw_output)
        rc_count = len(render_commands) if render_commands else 0
        scores["has_render_commands"] = 1.0 if rc_count > 0 else 0.0
        scores["rc_reasonable_count"] = min(1.0, rc_count / max(1, 2)) if rc_count > 0 else 0.3

        # 4. 当前页命中 (20%)
        page_hit = False
        if render_commands:
            for rc in render_commands:
                si = rc.get("slide_index", -1)
                if si == current_index or si == -1:
                    page_hit = True
                    break
        elif category in ("B_title", "F_polish"):
            # 简单指令可能直接返回 JSON action
            if f'"slide_index": {current_index}' in raw_output or '"slide_index": -1' in raw_output:
                page_hit = True
        scores["current_page_hit"] = 1.0 if page_hit else 0.0

        # 5. 类型/意图匹配 (20%)
        type_hit = Evaluator._check_type_match(category, render_commands, raw_output)
        scores["type_match"] = 1.0 if type_hit else 0.0

        # 6. 无错误泄漏 (15%)
        has_error_markers = any(marker in raw_output.lower() for marker in [
            "error:", "exception", "traceback", "failed", "无法", "抱歉"
        ])
        scores["no_error"] = 0.5 if has_error_markers else 1.0

        # 综合加权
        weights = {
            "not_empty": 0.10,
            "length_ok": 0.10,
            "has_render_commands": 0.15,
            "rc_reasonable_count": 0.10,
            "current_page_hit": 0.20,
            "type_match": 0.20,
            "no_error": 0.15,
        }
        total = sum(scores.get(k, 0) * w for k, w in weights.items())
        rule_quality = round(total * 100, 1)
        current_slide = {}
        if slides_data and 0 <= current_index < len(slides_data):
            current_slide = dict(slides_data[current_index])
        cocreation_eval = evaluate_cocreation_output(
            instruction=instruction,
            output=raw_output,
            current_slide={**current_slide, "slide_index": current_index},
            render_commands=render_commands,
            category=category,
            judge_budget=judge_budget,
        )
        quality_score = round(
            0.40 * rule_quality
            + 0.20 * cocreation_eval["semantic_similarity"]
            + 0.15 * cocreation_eval["description_accuracy"]
            + 0.10 * cocreation_eval["target_accuracy"]
            + 0.15 * cocreation_eval["overall_score"],
            1,
        )

        return {
            "scores": scores,
            "quality_score": quality_score,
            "rule_score": rule_quality,
            "embedding_score": cocreation_eval["embedding_similarity"],
            "semantic_score": cocreation_eval["semantic_similarity"],
            "accuracy_score": cocreation_eval["description_accuracy"],
            "embedding_backend": cocreation_eval["embedding_backend"],
            "judge_score": cocreation_eval["judge_score"],
            "judge_applied": cocreation_eval["judge_applied"],
            "judge_summary": cocreation_eval["judge_summary"],
            "render_command_count": rc_count,
            "parse_success": rc_count > 0,
            "current_page_hit": page_hit,
            "type_match": type_hit,
        }

    @staticmethod
    def _extract_render_commands(raw: str) -> List[Dict]:
        """从 LLM 输出中提取 render_commands"""
        # 尝试新格式: {"render_commands": [...]}
        try:
            import re
            # 清理 think tags
            cleaned = re.sub(r'<[^>]*>', '', raw)
            cleaned = re.sub(r'```\w*\s*', '', cleaned).replace('```', '')

            m = re.search(r'"render_commands"\s*:\s*\[', cleaned)
            if m:
                # 找到 JSON 对象
                start = cleaned.rfind('{', 0, m.start())
                if start >= 0:
                    # 从 start 开始找匹配的 }
                    brace = 0
                    for i in range(start, len(cleaned)):
                        if cleaned[i] == '{':
                            brace += 1
                        elif cleaned[i] == '}':
                            brace -= 1
                            if brace == 0:
                                try:
                                    obj = json.loads(cleaned[start:i + 1])
                                    rcs = obj.get("render_commands", [])
                                    if isinstance(rcs, list):
                                        return [r for r in rcs if isinstance(r, dict)]
                                except Exception:
                                    pass
                                break

            # 尝试旧格式: [{"action": "update", ...}]
            m2 = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if m2:
                arr = json.loads(m2.group(0))
                if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                    if any(k in arr[0] for k in ("action", "slide_index", "field", "value", "items")):
                        return arr

            # 尝试单个 JSON 对象
            m3 = re.search(r'\{.*"action".*\}', cleaned, re.DOTALL)
            if m3:
                obj = json.loads(m3.group(0))
                if isinstance(obj, dict) and "action" in obj:
                    return [obj]
        except Exception:
            pass
        return []

    @staticmethod
    def _check_type_match(category: str, render_commands: List[Dict], raw: str) -> bool:
        """检查输出类型是否匹配指令类别"""
        if not render_commands and not raw:
            return False

        raw_lower = raw.lower()

        if category == "E_visual":
            # 视觉转换 — 检查是否有 chart/table/flowchart 类型
            visual_types = {"chart", "table", "flowchart", "image_right", "image_left"}
            for rc in render_commands:
                if rc.get("render_type") in visual_types:
                    return True
                if rc.get("render_params", {}).get("chart_type"):
                    return True
            # 旧格式检查
            return any(vt in raw_lower for vt in ["chart", "table", "flowchart", "柱状图", "表格", "流程图"])

        elif category == "B_title":
            # 标题 — 检查 slot=title 或 field=title
            for rc in render_commands:
                if rc.get("slot") == "title" or rc.get("field") == "title":
                    return True
            return "title" in raw_lower or "标题" in raw

        elif category in ("C_refocus", "D_style", "F_polish"):
            # 内容改写类 — 检查是否有 text 类型或 items 更新
            if render_commands:
                return True  # 有结构化输出就算命中
            # 或者文本中有明显的内容改写痕迹
            return len(raw.strip()) > 100

        elif category == "A_structure":
            # 结构操作 — 检查 add_slide / remove_slide 等
            for rc in render_commands:
                if rc.get("action") in ("add_slide", "remove_slide", "insert_slide"):
                    return True
                if rc.get("slide_index") == -1:  # 新建页
                    return True
            return any(kw in raw_lower for kw in ["add", "remove", "insert", "添加", "删除", "新增"])

        elif category == "G_compound":
            # 复合指令 — 至少包含 2 种操作
            ops = 0
            if any(rc.get("slot") == "title" or rc.get("field") == "title" for rc in render_commands):
                ops += 1
            if len(render_commands) > 1:
                ops += 1
            if any(rc.get("render_type") in ("chart", "table", "flowchart") for rc in render_commands):
                ops += 1
            return ops >= 2 or (render_commands and len(raw) > 100)

        elif category == "H_global":
            # 全量操作
            return len(raw.strip()) > 50

        return len(raw.strip()) > 30


# ============================================================
# 执行器
# ============================================================
def run_ppt_generation(doc_key: str, doc_text: str) -> GenerationResult:
    """执行 PPT 4阶段生成管线"""
    from opencopilot.capabilities.ppt.pipeline import PPTGenerationPipeline

    label = SAMPLE_DOCS[doc_key]["label"]
    start = time.time()
    try:
        pipeline = PPTGenerationPipeline()
        result = pipeline.run(doc_text)
        elapsed = (time.time() - start) * 1000

        slides_preview = json.dumps(
            [{"title": s.get("title", ""), "type": s.get("type", ""),
              "items_count": len(s.get("items", []))} for s in result.slides],
            ensure_ascii=False,
        )[:500]

        return GenerationResult(
            doc_key=doc_key, doc_label=label, success=True,
            total_pages=result.total_pages,
            topics=[t.title for t in result.topics],
            stage_durations={k: round(v, 2) for k, v in result.stage_durations.items()},
            latency_ms=round(elapsed),
            slides_preview=slides_preview,
        )
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return GenerationResult(
            doc_key=doc_key, doc_label=label, success=False,
            total_pages=0, topics=[], stage_durations={},
            latency_ms=round(elapsed), slides_preview="",
            error=str(e),
        )


def _build_polish_guidance(current_slide: dict, original_text: str) -> str:
    items = current_slide.get("items", []) if isinstance(current_slide, dict) else []
    item_count = len(items) if isinstance(items, list) else 0
    original_excerpt = (original_text or "").strip().replace("\n", " ")[:280]
    lines = [
        "## 文案润色专项约束",
        "- 你已经拿到了当前页完整数据，不要再次请求读取页面，也不要输出 read_slide 或任何占位动作。",
        "- 仅改写当前页现有文案，不要新增事实、不要编造数据、不要改动用户未要求的标题或页面结构。",
        "- 尽量保持原有条目顺序与条目数量一致；每个原始条目压缩为一句话，不要合并多条，也不要拆分一条。",
        "- 必须保留数字、年份、百分比、金额、专有名词、产品名、人名、组织名等关键信息。",
        "- 必须保留因果、对比、转折等语义关系，避免改成空泛口号。",
        "- 输出时优先使用 render_commands，并为每个被改写条目提供可定位的 source_text。",
    ]
    if item_count:
        lines.append(f"- 当前页可见条目数约为 {item_count}，请按该粒度逐条改写。")
    if original_excerpt:
        lines.append(f"- 文档背景摘要：{original_excerpt}")
    return "\n".join(lines)


def _build_category_specific_guidance(category: str, current_slide: dict, original_text: str) -> str:
    if category == "F_polish":
        return _build_polish_guidance(current_slide, original_text)
    return ""


def _build_cocreation_message(instruction, slides_data, current_index, category="", original_text=""):
    """构造共创指令消息（两个后端共用）"""
    total = len(slides_data)
    idx = max(0, current_index) if current_index >= 0 else 0
    current_slide = slides_data[idx] if slides_data and idx < total else {}
    category_guidance = _build_category_specific_guidance(category, current_slide, original_text)

    parts = [f"PPT 总共 {total} 页，当前正在编辑第 {idx + 1} 页。"]
    parts.append(f"\n当前幻灯片数据：\n```json\n{json.dumps(current_slide, ensure_ascii=False, indent=2)}\n```")
    parts.append(f"\n用户指令：{instruction}")
    if category_guidance:
        parts.append(f"\n{category_guidance}")
    parts.append("""
## 输出格式（推荐：渲染指令）

返回 JSON 格式的渲染指令数组：

```json
{
  "render_commands": [
    {
      "source_text": "原文片段（用于定位）",
      "render_type": "chart",
      "render_params": { "chart_type": "bar", "title": "图表标题" },
      "slide_index": -1,
      "slot": "body"
    }
  ]
}
```

支持的 render_type：text | table | chart | flowchart | image_right | image_left

关键约束：
- 默认修改当前正在编辑的页，除非用户明确要求新增
- 如果是改标题，必须输出到 slot=title
- slide_index 当前页修改只能用当前页索引或 -1
""")
    return "\n".join(parts)


def run_cocreation_instruction(
    instruction: str,
    category: str,
    label: str,
    slides_data: list,
    current_index: int,
    original_text: str,
    backend: str = "self_agent",
    timeout_sec: int = 120,
) -> InstructionResult:
    """执行单条共创指令"""

    user_message = _build_cocreation_message(
        instruction,
        slides_data,
        current_index,
        category=category,
        original_text=original_text,
    )

    if backend == "self_agent":
        raw_output, error_msg, elapsed = _run_self_agent_cocreation(user_message, timeout_sec)
    elif backend == "hermes":
        raw_output, error_msg, elapsed = _run_hermes_cocreation(user_message, timeout_sec)
    else:
        raw_output, error_msg, elapsed = "", f"未知后端: {backend}", 0

    # 评估
    eval_result = Evaluator.evaluate_instruction(
        raw_output, instruction, category, current_index, slides_data, JUDGE_BUDGET
    )

    return InstructionResult(
        category=category,
        instruction=instruction,
        label=label,
        backend=backend,
        success=len(raw_output.strip()) > 0 and not error_msg,
        latency_ms=round(elapsed),
        raw_length=len(raw_output),
        render_command_count=eval_result["render_command_count"],
        parse_success=eval_result["parse_success"],
        current_page_hit=eval_result["current_page_hit"],
        expected_type_hit=eval_result["type_match"],
        quality_score=eval_result["quality_score"],
        rule_score=eval_result["rule_score"],
        embedding_score=eval_result["embedding_score"],
        semantic_score=eval_result["semantic_score"],
        accuracy_score=eval_result["accuracy_score"],
        embedding_backend=eval_result["embedding_backend"],
        judge_score=eval_result["judge_score"],
        judge_applied=eval_result["judge_applied"],
        judge_summary=eval_result["judge_summary"],
        preview=raw_output[:300].replace("\n", " "),
        error=error_msg,
    )


def _run_self_agent_cocreation(user_message: str, timeout_sec: int) -> tuple:
    """self_agent 后端：直接调用 call_agent_pipeline_sync"""
    import signal
    from opencopilot.agent.caller import call_agent_pipeline_sync

    session_id = f"bench-self-{uuid.uuid4().hex[:8]}"
    timed_out = False

    def _alarm_handler(_signum, _frame):
        nonlocal timed_out
        timed_out = True
        raise TimeoutError(f"超时 ({timeout_sec}s)")

    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(timeout_sec)

    start = time.time()
    chunks: List[str] = []
    error_msg = ""
    try:
        for chunk in call_agent_pipeline_sync(
            text=user_message, action_type="chat",
            session_id=session_id, context_source="ppt_editor",
            is_new_task=True,
        ):
            if timed_out:
                break
            chunks.append(chunk)
    except TimeoutError:
        error_msg = f"超时 ({timeout_sec}s)"
    except Exception as e:
        error_msg = str(e)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    elapsed = (time.time() - start) * 1000
    return "".join(chunks), error_msg, elapsed


def _run_hermes_cocreation(user_message: str, timeout_sec: int) -> tuple:
    """hermes 后端：通过 vnext API 调用"""
    import signal

    timed_out = False

    def _alarm_handler(_signum, _frame):
        nonlocal timed_out
        timed_out = True
        raise TimeoutError(f"超时 ({timeout_sec}s)")

    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(timeout_sec)

    start = time.time()
    raw_output = ""
    error_msg = ""
    try:
        import httpx
        from gui_next.smart_copilot.runtime import SmartCopilotApiRuntime

        api_runtime = SmartCopilotApiRuntime(preferred_base_url="http://127.0.0.1:8000")
        base_url = api_runtime.ensure_ready()
        client = httpx.Client(base_url=base_url, timeout=httpx.Timeout(10.0, read=timeout_sec))

        # 1. Create context snapshot
        snap_resp = client.post("/vnext/context/snapshots", json={
            "trigger": "ppt_cocreation_benchmark",
            "source_app": "bench_ppt_editor",
            "selection_text": user_message[:2000],
            "metadata": {"context_source": "ppt_editor"},
        })
        snap_resp.raise_for_status()
        snapshot_id = snap_resp.json()["context_snapshot_id"]

        # 2. Create task
        task_resp = client.post("/vnext/tasks", json={
            "action": "chat",
            "user_input": user_message,
            "context_snapshot_id": snapshot_id,
        })
        task_resp.raise_for_status()
        task_id = task_resp.json()["task_id"]

        # 3. Poll events
        last_seq = 0
        terminal = False
        deadline = time.time() + timeout_sec - 5
        while time.time() < deadline and not timed_out:
            ev_resp = client.get(f"/vnext/tasks/{task_id}/events")
            ev_resp.raise_for_status()
            events = ev_resp.json().get("events", [])
            for ev in events:
                seq = ev.get("sequence", 0)
                if seq <= last_seq:
                    continue
                last_seq = seq
                etype = ev.get("type", "")
                payload = ev.get("payload", {})
                if etype == "task.delta":
                    raw_output += payload.get("delta", "")
                elif etype == "task.completed":
                    summary = payload.get("summary", "")
                    if summary:
                        raw_output = summary
                    terminal = True
                elif etype == "task.failed":
                    error_msg = payload.get("error", "Hermes task failed")
                    terminal = True
            if terminal:
                break
            time.sleep(0.3)

        if not terminal and not error_msg:
            error_msg = f"超时 ({timeout_sec}s)"

        client.close()
    except TimeoutError:
        error_msg = f"超时 ({timeout_sec}s)"
    except Exception as e:
        error_msg = str(e)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    elapsed = (time.time() - start) * 1000
    return raw_output, error_msg, elapsed


# ============================================================
# 报告生成器
# ============================================================
def generate_report(
    gen_results: List[GenerationResult],
    inst_results: List[InstructionResult],
    seeds: List[int],
    task_mode: str,
    output_path: Path,
):
    """生成评测报告（按后端自适应）"""
    # 按后端分组
    by_backend = {}
    for ir in inst_results:
        by_backend.setdefault(ir.backend, []).append(ir)

    backend_labels = {"self_agent": "self_agent(mimo)", "hermes": "hermes(vnext)"}
    backend_order = [be for be in ("self_agent", "hermes") if be in by_backend] + [be for be in by_backend if be not in {"self_agent", "hermes"}]
    report_title = "# PPT 生成 + 共创自由指令 质量评测报告"
    if backend_order == ["self_agent"]:
        report_title = "# PPT 生成 + 共创自由指令 质量评测报告（self_agent）"
    elif len(backend_order) > 1:
        report_title = "# PPT 生成 + 共创自由指令 质量评测报告（多后端对照）"
    backend_summary = " / ".join(f"{backend_labels.get(be, be)}: {len(by_backend.get(be, []))}" for be in backend_order) or "无共创样本"

    lines = [
        report_title,
        "",
        f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**随机种子**: {seeds}  ",
        f"**Task Mode**: {task_mode}  ",
        f"**指令总数**: {len(inst_results)}（{backend_summary}）  ",
        f"**LLM Judge**: {'enabled' if JUDGE_BUDGET.enabled else 'disabled'} / max_cases={JUDGE_BUDGET.max_cases} / used={JUDGE_BUDGET.used_cases}  ",
        f"**Embedding Backend**: {os.getenv('OPEN_COPILOT_EMBEDDING_BACKEND', 'auto')}  ",
        "",
        "---",
        "",
        "## 1. PPT 初始生成质量",
        "",
        "| 文档 | 状态 | 页数 | 主题数 | 延迟 | 各阶段耗时 |",
        "|------|------|------|--------|------|-----------|",
    ]

    for gr in gen_results:
        status = "✅" if gr.success else f"❌ {gr.error}"
        stages = ", ".join(f"{k}:{v}s" for k, v in gr.stage_durations.items()) if gr.stage_durations else "-"
        lines.append(
            f"| {gr.doc_label} | {status} | {gr.total_pages} | {len(gr.topics)} | {gr.latency_ms}ms | {stages} |"
        )

    for gr in gen_results:
        if gr.success:
            lines.extend([
                "", f"### {gr.doc_label} 生成详情",
                f"- **主题**: {', '.join(gr.topics)}",
                f"- **页面结构**:",
                f"```json", gr.slides_preview, f"```",
            ])

    def _calc_stats(items):
        n = len(items)
        if n == 0:
            return {
                "n": 0, "success_rate": 0, "avg_quality": 0, "avg_rule": 0, "avg_semantic": 0,
                "avg_embedding": 0, "avg_accuracy": 0, "judge_coverage": 0, "avg_latency": 0, "page_hit": 0, "type_hit": 0
            }
        return {
            "n": n,
            "success_rate": sum(1 for x in items if x.success) / n * 100,
            "avg_quality": sum(x.quality_score for x in items) / n,
            "avg_rule": sum(x.rule_score for x in items) / n,
            "avg_embedding": sum(x.embedding_score for x in items) / n,
            "avg_semantic": sum(x.semantic_score for x in items) / n,
            "avg_accuracy": sum(x.accuracy_score for x in items) / n,
            "judge_coverage": sum(1 for x in items if x.judge_applied) / n * 100,
            "avg_latency": sum(x.latency_ms for x in items) / n,
            "page_hit": sum(1 for x in items if x.current_page_hit) / n * 100,
            "type_hit": sum(1 for x in items if x.expected_type_hit) / n * 100,
        }

    lines.extend(["", "---", "", "## 2. 后端总览", ""])
    lines.extend([
        "| 后端 | 测试数 | 成功率 | 平均质量 | 规则分 | Embedding | 语义分 | 准确性 | Judge覆盖 | 平均延迟 | 当前页命中 | 类型匹配 |",
        "|------|--------|--------|---------|-------|-----------|-------|--------|----------|---------|-----------|----------|",
    ])
    backend_stats = {be: _calc_stats(by_backend.get(be, [])) for be in backend_order}
    for be in backend_order:
        stats = backend_stats[be]
        lines.append(
            f"| {backend_labels.get(be, be)} | {stats['n']} | {stats['success_rate']:.0f}% | **{stats['avg_quality']:.1f}** | "
            f"{stats['avg_rule']:.1f} | {stats['avg_embedding']:.1f} | {stats['avg_semantic']:.1f} | {stats['avg_accuracy']:.1f} | "
            f"{stats['judge_coverage']:.0f}% | {stats['avg_latency']:.0f}ms | {stats['page_hit']:.0f}% | {stats['type_hit']:.0f}% |"
        )

    if len(backend_order) >= 2:
        base = backend_order[0]
        lines.extend(["", "### 关键差值", ""])
        base_stats = backend_stats[base]
        for other in backend_order[1:]:
            other_stats = backend_stats[other]
            lines.append(
                f"- `{backend_labels.get(base, base)}` 相对 `{backend_labels.get(other, other)}`: "
                f"质量 {base_stats['avg_quality'] - other_stats['avg_quality']:+.1f} / "
                f"Embedding {base_stats['avg_embedding'] - other_stats['avg_embedding']:+.1f} / "
                f"准确性 {base_stats['avg_accuracy'] - other_stats['avg_accuracy']:+.1f}"
            )

    # ---- 分类别对比 ----
    cat_names = {
        "A_structure": "A. 结构操作", "B_title": "B. 标题编辑",
        "C_refocus": "C. 内容提炼", "D_style": "D. 风格调整",
        "E_visual": "E. 视觉转换", "F_polish": "F. 文案润色",
        "G_compound": "G. 复合指令", "H_global": "H. 全量操作",
    }

    lines.extend(["", "---", "", "## 3. 分类别对比", ""])
    lines.extend([
        "| 类别 | 后端 | 测试数 | 平均质量 | 规则分 | Embedding | 语义分 | 准确性 | Judge覆盖 | 平均延迟 |",
        "|------|------|--------|---------|-------|-----------|-------|--------|----------|---------|",
    ])

    cat_by_backend = {}
    for ir in inst_results:
        key = (ir.category, ir.backend)
        cat_by_backend.setdefault(key, []).append(ir)

    for cat_key in sorted(set(ir.category for ir in inst_results)):
        for be in backend_order:
            items = cat_by_backend.get((cat_key, be), [])
            if not items:
                continue
            s = _calc_stats(items)
            cat_label = cat_names.get(cat_key, cat_key)
            be_label = backend_labels.get(be, be)
            lines.append(
                f"| {cat_label} | {be_label} | {s['n']} | **{s['avg_quality']:.1f}** | "
                f"{s['avg_rule']:.1f} | {s['avg_embedding']:.1f} | {s['avg_semantic']:.1f} | {s['avg_accuracy']:.1f} | {s['judge_coverage']:.0f}% | {s['avg_latency']:.0f}ms |"
            )

    # ---- 逐条详情 ----
    lines.extend(["", "---", "", "## 4. 逐条指令详情", ""])

    # 按类别分组，每类里两个后端并排
    categories_all = {}
    for ir in inst_results:
        categories_all.setdefault(ir.category, []).append(ir)

    lines.extend([
        "| 类别 | 后端 | 指令 | 标签 | 状态 | 延迟 | RC数 | **质量** | Embed | 语义 | 准确性 | Judge |",
        "|------|------|------|------|------|------|------|---------|-------|------|--------|-------|",
    ])

    for cat_key in sorted(categories_all.keys()):
        cat_label = cat_names.get(cat_key, cat_key)
        for be in backend_order:
            items = [x for x in categories_all[cat_key] if x.backend == be]
            for ir in items:
                status = "✅" if ir.success else f"❌"
                lines.append(
                    f"| {cat_label} | {backend_labels.get(be, be)[:12]} | {ir.instruction[:25]} | {ir.label} | "
                    f"{status} | {ir.latency_ms}ms | {ir.render_command_count} | "
                    f"**{ir.quality_score}** | {ir.embedding_score:.1f} | {ir.semantic_score:.1f} | {ir.accuracy_score:.1f} | "
                    f"{'-' if ir.judge_score is None else f'{ir.judge_score:.1f}'} |"
                )

    # ---- 输出样本 ----
    lines.extend(["", "---", "", "## 5. 输出样本（每类每后端第一条）", ""])
    shown = set()
    for ir in inst_results:
        k = (ir.category, ir.backend)
        if k not in shown:
            shown.add(k)
            lines.extend([
                f"### [{backend_labels.get(ir.backend, ir.backend)}] {ir.category}/{ir.label}",
                f"- **指令**: `{ir.instruction}`",
                f"- **延迟**: {ir.latency_ms}ms / **长度**: {ir.raw_length}字符 / **质量**: {ir.quality_score}",
                f"- **规则分/Embedding/语义分/准确性**: {ir.rule_score:.1f} / {ir.embedding_score:.1f} / {ir.semantic_score:.1f} / {ir.accuracy_score:.1f}",
                f"- **Embedding Backend**: {ir.embedding_backend}",
                f"- **Judge**: {ir.judge_score if ir.judge_score is not None else '未执行'} {('/ ' + ir.judge_summary) if ir.judge_summary else ''}",
                f"- **输出预览**:",
                f"```", ir.preview[:500], f"```", "",
            ])

    # ---- 关键发现 ----
    lines.extend(["", "---", "", "## 6. 关键发现", ""])

    # 找最弱/最强
    per_backend_cat_scores: dict[str, dict[str, float]] = {}
    for cat_key, items_list in cat_by_backend.items():
        cat, be = cat_key
        per_backend_cat_scores.setdefault(be, {})[cat] = sum(x.quality_score for x in items_list) / len(items_list)

    note_index = 1
    for be in backend_order:
        cat_scores = per_backend_cat_scores.get(be, {})
        if not cat_scores:
            continue
        weakest = min(cat_scores, key=cat_scores.get)
        strongest = max(cat_scores, key=cat_scores.get)
        lines.append(f"{note_index}. **{backend_labels.get(be, be)} 最强**: {cat_names.get(strongest, strongest)} ({cat_scores[strongest]:.1f}分)")
        note_index += 1
        lines.append(f"{note_index}. **{backend_labels.get(be, be)} 最弱**: {cat_names.get(weakest, weakest)} ({cat_scores[weakest]:.1f}分)")
        note_index += 1

    if len(backend_order) >= 2:
        base = backend_order[0]
        for other in backend_order[1:]:
            common_cats = set(per_backend_cat_scores.get(base, {}).keys()) & set(per_backend_cat_scores.get(other, {}).keys())
            if common_cats:
                max_diff_cat = max(common_cats, key=lambda c: abs(per_backend_cat_scores[base][c] - per_backend_cat_scores[other][c]))
                diff_val = per_backend_cat_scores[base][max_diff_cat] - per_backend_cat_scores[other][max_diff_cat]
                lines.append(
                    f"{note_index}. **质量差距最大**: {cat_names.get(max_diff_cat, max_diff_cat)} "
                    f"({backend_labels.get(base, base)} {per_backend_cat_scores[base][max_diff_cat]:.1f} vs "
                    f"{backend_labels.get(other, other)} {per_backend_cat_scores[other][max_diff_cat]:.1f}, 差 {diff_val:+.1f})"
                )
                note_index += 1

    if "self_agent" in backend_stats and "hermes" in backend_stats and backend_stats["self_agent"]["avg_latency"] > 0:
        lines.append(f"{note_index}. **延迟比**: hermes / self_agent = {backend_stats['hermes']['avg_latency'] / backend_stats['self_agent']['avg_latency']:.1f}x")
        note_index += 1
    lines.append(f"{note_index}. **PPT 生成**: {'全部成功' if all(g.success for g in gen_results) else '存在失败'}")

    lines.extend(["", "> 报告由 test_ppt_cocreation_quality_benchmark.py 自动生成"])

    report_text = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    return report_text


# ============================================================
# 主入口
# ============================================================
def main():
    print("=" * 70)
    print("PPT 生成 + 共创自由指令 质量评测")
    print("=" * 70)

    task_mode, instruction_pool = _load_instruction_pool()
    seed_values = os.getenv("OPEN_COPILOT_PPT_BENCH_SEEDS", "42,137,256")
    seeds = [int(part.strip()) for part in seed_values.split(",") if part.strip()]
    samples_per_round = max(1, int(os.getenv("OPEN_COPILOT_PPT_SAMPLES_PER_ROUND", "3")))
    all_gen_results: List[GenerationResult] = []
    all_inst_results: List[InstructionResult] = []

    # ---- Phase 1: PPT 初始生成 ----
    print("\n━━━ Phase 1: PPT 初始生成 (4阶段管线) ━━━")
    base_slides = {}
    for doc_key, doc_info in SAMPLE_DOCS.items():
        print(f"\n  生成 [{doc_info['label']}] ...")
        gr = run_ppt_generation(doc_key, doc_info["text"])
        all_gen_results.append(gr)
        if gr.success:
            print(f"  ✅ {gr.total_pages} 页 | 延迟 {gr.latency_ms}ms")
            print(f"     主题: {', '.join(gr.topics)}")
            print(f"     阶段耗时: {gr.stage_durations}")
            # 保存 slides 数据供共创测试使用
            try:
                # 直接重新获取完整 slides，避免使用截断 preview 造成解析失败
                from opencopilot.capabilities.ppt.pipeline import PPTGenerationPipeline
                pipeline = PPTGenerationPipeline()
                result = pipeline.run(doc_info["text"])
                base_slides[doc_key] = result.slides
            except Exception as e:
                print(f"  ⚠️  slides 缓存失败: {e}")
                base_slides[doc_key] = []
        else:
            print(f"  ❌ 失败: {gr.error}")
            base_slides[doc_key] = []

    # ---- Phase 2: 共创自由指令评测 ----
    phase2_title = "共创忠实改写专项评测 (固定数据集)" if task_mode == "faithful_rewrite" else "共创自由指令评测 (随机抽样)"
    print(f"\n━━━ Phase 2: {phase2_title} ━━━")

    backend_values = os.getenv("OPEN_COPILOT_PPT_BENCH_BACKENDS", "self_agent")
    backends = [part.strip() for part in backend_values.split(",") if part.strip()]
    seed_rounds = seeds if task_mode != "faithful_rewrite" else [0]
    for seed in seed_rounds:
        rng = random.Random(seed) if task_mode != "faithful_rewrite" else None
        if task_mode == "faithful_rewrite":
            print("\n  ── 固定数据集 round ──")
        else:
            print(f"\n  ── 随机种子 {seed} ──")

        round_samples = _build_round_samples(
            task_mode=task_mode,
            instruction_pool=instruction_pool,
            base_slides=base_slides,
            rng=rng,
            samples_per_round=samples_per_round,
        )

        total_per_backend = len(seed_rounds) * len(round_samples)

        for backend in backends:
            backend_label = "self_agent(mimo)" if backend == "self_agent" else "hermes(vnext)"
            print(f"\n  ▸ 后端: {backend_label}")
            cat_names_short = {
                "A_structure": "结构操作", "B_title": "标题编辑",
                "C_refocus": "内容提炼", "D_style": "风格调整",
                "E_visual": "视觉转换", "F_polish": "文案润色",
                "G_compound": "复合指令", "H_global": "全量操作",
            }

            for cat_key, instr_def, doc_key, current_index in round_samples:
                cat_label = cat_names_short.get(cat_key, cat_key)
                slides = base_slides.get(doc_key, [])

                idx = sum(1 for x in all_inst_results if x.backend == backend) + 1
                label = instr_def.get("label", "")
                print(f"  [{idx}/{total_per_backend}] {cat_label}: {label} ...", end=" ", flush=True)

                ir = run_cocreation_instruction(
                    instruction=instr_def["instruction"],
                    category=cat_key,
                    label=label,
                    slides_data=deepcopy(slides),
                    current_index=current_index,
                    original_text=SAMPLE_DOCS[doc_key]["text"],
                    backend=backend,
                    timeout_sec=120,
                )
                all_inst_results.append(ir)

                status = "✅" if ir.success else f"❌{ir.error[:20]}"
                print(f"{status} | {ir.latency_ms}ms | {ir.raw_length}c | 质量={ir.quality_score}")

    # ---- Phase 3: 生成报告 ----
    print("\n━━━ Phase 3: 生成评测报告 ━━━")
    report_path = PROJECT_ROOT / "tests" / "e2e" / "ppt_cocreation_quality_report.md"
    generate_report(all_gen_results, all_inst_results, seeds, task_mode, report_path)
    print(f"\n  报告已生成: {report_path}")

    # 打印摘要（按后端分组）
    print(f"\n━━━ 摘要 ━━━")
    print(f"  PPT 生成: {sum(1 for g in all_gen_results if g.success)}/{len(all_gen_results)} 成功")

    by_be = {}
    for x in all_inst_results:
        by_be.setdefault(x.backend, []).append(x)

    for be, items in by_be.items():
        n = len(items)
        s = sum(1 for x in items if x.success)
        q = sum(x.quality_score for x in items) / max(n, 1)
        l = sum(x.latency_ms for x in items) / max(n, 1)
        p = sum(1 for x in items if x.current_page_hit)
        print(f"  [{be}] 成功:{s}/{n} | 质量:{q:.1f} | 延迟:{l:.0f}ms | 当前页命中:{p}/{n}({p/max(n,1)*100:.0f}%)")

    print(f"\n完成！")


if __name__ == "__main__":
    main()
