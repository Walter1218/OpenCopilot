"""
PPT 生成 & 共创调整 —— 综合质量测试

测试覆盖:
1. 多类型文档 PPT 生成（9 种文档）
2. 共创模式内容调整（6 种操作类型）
3. 质量评分与问题汇总
"""
import sys, os, json, time, re, uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# 注入项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opencopilot.capabilities.ppt.pipeline import PPTGenerationPipeline, PipelineResult


# ═══════════════════════════════════════════════════
# Part 1: PPT 生成测试
# ═══════════════════════════════════════════════════

TEST_DOCS = {
    "marketing_plan": "test_docs/marketing_plan.md",       # 营销方案（表格+策略）
    "ai_agent_whitepaper": "test_docs/ai_agent_whitepaper.md",  # 技术白皮书（代码+实验数据）
    "annual_strategy": "test_docs/annual_strategy_report.md",   # 年度战略报告（长文档）
    "combined_long": "test_docs/combined_long_doc.md",     # 组合长文档
    "api_spec": "test_docs/api_spec.md",                   # API 规格
    "meeting_notes": "test_docs/meeting_notes.md",         # 会议纪要
    "product_spec": "test_docs/product_spec.md",           # 产品规格
    "project_plan": "test_docs/project_plan.md",           # 项目计划
    "budget_report": "test_docs/budget_report.md",         # 预算报告
    "tech_spec": "test_docs/tech_spec.md",                 # 技术规格
    "tiny_doc": "test_docs/tiny_doc.md",                   # 超短文档
}


@dataclass
class PPTTestResult:
    doc_name: str
    doc_size: int
    total_pages: int = 0
    slide_types: Dict[str, int] = field(default_factory=dict)
    layout_types: Dict[str, int] = field(default_factory=dict)
    has_ending: bool = False
    has_title: bool = False
    has_table_slide: bool = False
    total_items: int = 0
    duration_s: float = 0
    error: Optional[str] = None
    score: float = 0.0
    notes: List[str] = field(default_factory=list)

    def evaluate(self):
        """自动评分"""
        score = 5.0
        # 基础检查
        if self.total_pages < 2:
            score -= 2.0
            self.notes.append("页数过少")
        if not self.has_title:
            score -= 1.5
            self.notes.append("缺少封面页")
        if not self.has_ending:
            score -= 1.0
            self.notes.append("缺少结尾页")
        # 覆盖度检查
        if self.total_items < 3:
            score -= 1.0
            self.notes.append("内容过于精简")
        # 版式多样性
        layout_count = len(self.layout_types)
        if layout_count < 2:
            score -= 0.5
            self.notes.append("版式单一")
        if layout_count >= 3:
            score += 0.5
            self.notes.append("版式多样")
        # 表格处理
        if "table" in str(self.doc_name).lower() or "budget" in str(self.doc_name).lower():
            if not self.has_table_slide:
                score -= 0.5
                self.notes.append("表格文档缺少表格页")
        # 特殊内容处理
        if "three_columns" in self.layout_types:
            score += 0.3
        if "image_right" in self.layout_types:
            score += 0.3
        self.score = max(0, min(5, score))
        return self.score


def run_ppt_test(doc_name: str, doc_path: str) -> PPTTestResult:
    """运行单次 PPT 生成测试"""
    result = PPTTestResult(doc_name=doc_name, doc_size=0)
    try:
        full_path = project_root / doc_path
        if not full_path.exists():
            result.error = f"文件不存在: {full_path}"
            return result

        text = full_path.read_text(encoding="utf-8")
        result.doc_size = len(text)

        t0 = time.time()
        pipeline = PPTGenerationPipeline()
        pipeline_result = pipeline.run(text)
        result.duration_s = round(time.time() - t0, 1)

        result.total_pages = pipeline_result.total_pages

        # 分析 slides
        for slide in pipeline_result.slides:
            st = slide.get("type", "unknown")
            result.slide_types[st] = result.slide_types.get(st, 0) + 1
            layout = slide.get("layout", "unknown")
            result.layout_types[layout] = result.layout_types.get(layout, 0) + 1

            if st == "title":
                result.has_title = True
            if st == "ending":
                result.has_ending = True
            if st == "table" or slide.get("layout") == "table":
                result.has_table_slide = True

            items = slide.get("items", [])
            result.total_items += len(items)

        result.evaluate()

    except Exception as e:
        result.error = str(e)

    return result


# ═══════════════════════════════════════════════════
# Part 2: 共创调整测试
# ═══════════════════════════════════════════════════

SAMPLE_SLIDES = [
    {"type": "title", "layout": "center", "title": "AI 产品发布会", "subtitle": "2026"},
    {"type": "content", "layout": "text_only", "title": "产品亮点",
     "items": [{"level": 0, "text": "多模态感知", "content_type": "text"},
               {"level": 0, "text": "超长上下文", "content_type": "text"},
               {"level": 0, "text": "实时推理", "content_type": "text"}]},
    {"type": "content", "layout": "three_columns", "title": "方案对比",
     "items": [{"level": 0, "text": "方案A", "content_type": "text"},
               {"level": 0, "text": "方案B", "content_type": "text"},
               {"level": 0, "text": "方案C", "content_type": "text"}]},
    {"type": "content", "layout": "text_only", "title": "实施计划",
     "items": [{"level": 0, "text": "第一阶段：研发", "content_type": "text"},
               {"level": 0, "text": "第二阶段：测试", "content_type": "text"}]},
    {"type": "ending", "layout": "center", "title": "谢谢", "subtitle": "Q & A"},
]


@dataclass
class CocreationTestResult:
    test_name: str
    action_type: str
    prompt: str
    response_raw: str = ""
    parsed_actions: List[dict] = field(default_factory=list)
    valid: bool = False
    slides_after: list = field(default_factory=list)
    error: Optional[str] = None

    def evaluate(self) -> bool:
        """验证调整是否有效"""
        if self.error:
            return False
        if not self.parsed_actions:
            return False
        self.valid = True
        return True


def parse_cocreate_actions(text: str) -> List[dict]:
    """从 LLM 响应中解析共创操作"""
    actions = []
    # 尝试 JSON 解析
    try:
        # 清理 think 标签
        cleaned = re.sub(r'<[^>]*>', '', text)
        # 尝试找 JSON 数组
        arr_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if arr_match:
            parsed = json.loads(arr_match.group(0))
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "action" in item:
                        actions.append(item)
        # 尝试逐行 JSON
        if not actions:
            for line in cleaned.split('\n'):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        obj = json.loads(line)
                        if "action" in obj:
                            actions.append(obj)
                    except json.JSONDecodeError:
                        pass
        # 尝试完整 JSON 对象（slides 格式）
        if not actions:
            obj_match = re.search(r'\{.*"slides".*\}', cleaned, re.DOTALL)
            if obj_match:
                obj = json.loads(obj_match.group(0))
                if "slides" in obj:
                    actions.append({"action": "full_replace", "slides": obj["slides"]})
    except Exception as e:
        pass
    return actions


def apply_cocreate_action(slides: List[dict], action: dict) -> List[dict]:
    """在本地应用共创操作"""
    import copy
    slides = copy.deepcopy(slides)
    act = action.get("action", "")

    if act == "update":
        idx = action.get("slide_index", 0)
        if 0 <= idx < len(slides):
            field = action.get("field", "")
            value = action.get("value", "")
            if field in ("title", "subtitle", "layout"):
                slides[idx][field] = value

    elif act == "add_item":
        idx = action.get("slide_index", 0)
        if 0 <= idx < len(slides):
            item = action.get("item", {})
            if item:
                slides[idx].setdefault("items", []).append(item)

    elif act == "remove_item":
        idx = action.get("slide_index", 0)
        item_idx = action.get("item_index", -1)
        if 0 <= idx < len(slides) and "items" in slides[idx]:
            items = slides[idx]["items"]
            if 0 <= item_idx < len(items):
                items.pop(item_idx)

    elif act == "update_item":
        idx = action.get("slide_index", 0)
        item_idx = action.get("item_index", -1)
        if 0 <= idx < len(slides) and "items" in slides[idx]:
            items = slides[idx]["items"]
            if 0 <= item_idx < len(items):
                field = action.get("field", "")
                value = action.get("value", "")
                if field in ("text", "level", "content_type"):
                    items[item_idx][field] = value

    elif act == "add_slide":
        insert_idx = action.get("index", len(slides))
        slide = action.get("slide", {})
        if slide:
            slides.insert(min(insert_idx, len(slides)), slide)

    elif act == "remove_slide":
        idx = action.get("index", -1)
        if 0 <= idx < len(slides):
            slides.pop(idx)

    elif act == "full_replace":
        new_slides = action.get("slides", [])
        if new_slides:
            slides = new_slides

    return slides


COCREATION_TESTS = [
    {
        "name": "修改标题",
        "prompt": "把第一页的标题改成「2026 年度 AI 产品战略发布会」",
    },
    {
        "name": "添加要点",
        "prompt": "在「产品亮点」页面添加一条要点：智能体协作",
    },
    {
        "name": "修改版式",
        "prompt": "把「实施计划」页面改为 image_right 版式",
    },
    {
        "name": "删除要点",
        "prompt": "删除「产品亮点」页面中的「实时推理」这条",
    },
    {
        "name": "全局重新生成",
        "prompt": "全部重新生成，主题改为「云计算平台发布会」",
    },
    {
        "name": "转换为表格",
        "prompt": "把「方案对比」页面转换为表格展示",
    },
]


def run_cocreate_test(test_case: dict) -> CocreationTestResult:
    """运行单次共创调整测试（本地模拟）"""
    import copy
    result = CocreationTestResult(
        test_name=test_case["name"],
        action_type="unknown",
        prompt=test_case["prompt"],
    )

    try:
        from opencopilot.agent.caller import call_agent_pipeline_sync

        # 构建上下文（当前 slides JSON + 用户指令）
        context = json.dumps({
            "current_slides": SAMPLE_SLIDES,
            "instruction": test_case["prompt"],
        }, ensure_ascii=False)

        full = ""
        for chunk in call_agent_pipeline_sync(
            text=context, action_type="ppt",
            context_source="ppt_editor", is_new_task=True,
            session_id=f"cocreate_test_{uuid.uuid4().hex[:8]}"
        ):
            full += chunk

        result.response_raw = full
        actions = parse_cocreate_actions(full)
        result.parsed_actions = actions

        if actions:
            slides = SAMPLE_SLIDES
            for action in actions:
                result.action_type = action.get("action", "unknown")
                slides = apply_cocreate_action(slides, action)
            result.slides_after = slides
            result.valid = True
        else:
            result.error = "未能解析出有效操作"

    except Exception as e:
        result.error = str(e)

    return result


# ═══════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  OpenCopilot PPT 生成 & 共创调整 —— 综合质量测试")
    print("=" * 70)

    # ---- Part 1: PPT Generation Tests ----
    print("\n📊 Part 1: PPT 生成测试 (多文档类型)")
    print("-" * 70)

    ppt_results: List[PPTTestResult] = []

    for name, path in TEST_DOCS.items():
        print(f"\n🔄 测试文档: {name} ({path})")
        result = run_ppt_test(name, path)
        ppt_results.append(result)

        if result.error:
            print(f"  ❌ 错误: {result.error}")
        else:
            print(f"  📄 {result.total_pages} 页 | ⏱ {result.duration_s}s")
            print(f"  📐 类型: {dict(result.slide_types)}")
            print(f"  🎨 版式: {dict(result.layout_types)}")
            print(f"  🏁 结尾页: {'✅' if result.has_ending else '❌'} | "
                  f"封面页: {'✅' if result.has_title else '❌'}")
            print(f"  ⭐ 评分: {result.score:.1f}/5.0")

    # ---- Summary ----
    print("\n" + "=" * 70)
    print("📋 PPT 生成测试汇总")
    print("=" * 70)

    valid_results = [r for r in ppt_results if not r.error]
    if valid_results:
        avg_score = sum(r.score for r in valid_results) / len(valid_results)
        avg_pages = sum(r.total_pages for r in valid_results) / len(valid_results)
        ending_count = sum(1 for r in valid_results if r.has_ending)

        print(f"  有效测试: {len(valid_results)}/{len(ppt_results)}")
        print(f"  平均页数: {avg_pages:.1f}")
        print(f"  平均评分: {avg_score:.2f}/5.0")
        print(f"  结尾页覆盖率: {ending_count}/{len(valid_results)} ({ending_count/len(valid_results)*100:.0f}%)")

        print(f"\n{'文档':<25} {'页数':<6} {'评分':<6} {'结尾':<6} {'版式'}")
        print("-" * 70)
        for r in valid_results:
            layouts = ",".join(r.layout_types.keys())
            print(f"  {r.doc_name:<23} {r.total_pages:<6} {r.score:<6.1f} "
                  f"{'✅' if r.has_ending else '❌':<6} {layouts}")

        # 问题汇总
        print(f"\n⚠️ 发现问题:")
        issues = [r for r in valid_results if r.notes]
        if issues:
            for r in issues:
                for note in r.notes:
                    print(f"  - [{r.doc_name}] {note}")
        else:
            print("  ✅ 无显著问题")

        if ending_count < len(valid_results):
            missing = [r.doc_name for r in valid_results if not r.has_ending]
            print(f"\n🔴 缺少结尾页的文档: {missing}")

    # 错误汇总
    errors = [r for r in ppt_results if r.error]
    if errors:
        print(f"\n❌ 错误汇总:")
        for r in errors:
            print(f"  - [{r.doc_name}] {r.error}")

    # ---- Part 2: Co-creation Tests ----
    print("\n\n" + "=" * 70)
    print("🤝 Part 2: 共创模式内容调整测试")
    print("=" * 70)

    cocreation_results: List[CocreationTestResult] = []
    for tc in COCREATION_TESTS:
        print(f"\n🔄 测试: {tc['name']}")
        print(f"  💬 Prompt: {tc['prompt'][:60]}...")

        result = run_cocreate_test(tc)
        cocreation_results.append(result)

        if result.error:
            print(f"  ❌ 错误: {result.error}")
        elif result.valid:
            print(f"  ✅ 有效动作: {len(result.parsed_actions)}")
            for act in result.parsed_actions:
                print(f"     - action={act.get('action')}, "
                      f"slide_index={act.get('slide_index', 'N/A')}")
            if result.slides_after:
                print(f"  📄 调整后 slides 数: {len(result.slides_after)}")
        else:
            print(f"  ❌ 未解析出有效操作")

    # ---- Co-creation Summary ----
    print("\n" + "=" * 70)
    print("📋 共创调整测试汇总")
    print("=" * 70)

    valid_cc = [r for r in cocreation_results if r.valid]
    invalid_cc = [r for r in cocreation_results if r.error or not r.valid]
    print(f"  通过: {len(valid_cc)}/{len(cocreation_results)}")
    if invalid_cc:
        print(f"  失败:")
        for r in invalid_cc:
            print(f"    - [{r.test_name}] {r.error or '无有效操作'}")

    action_types = {}
    for r in valid_cc:
        for act in r.parsed_actions:
            t = act.get("action", "unknown")
            action_types[t] = action_types.get(t, 0) + 1
    if action_types:
        print(f"  动作类型分布: {action_types}")

    # ---- Final Score ----
    print("\n" + "=" * 70)
    print("🏆 综合测试结果")
    print("=" * 70)

    ppt_pass = len(valid_results)
    ppt_total = len(ppt_results)
    cc_pass = len(valid_cc)
    cc_total = len(cocreation_results)

    print(f"  PPT 生成: {ppt_pass}/{ppt_total} 有效, 平均评分 {avg_score:.2f}/5.0"
          if valid_results else "  PPT 生成: 无有效结果")
    print(f"  共创调整: {cc_pass}/{cc_total} 通过")
    print(f"  结尾页覆盖: {ending_count}/{len(valid_results)}" if valid_results else "")


if __name__ == "__main__":
    main()
