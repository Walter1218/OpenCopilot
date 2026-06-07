"""
PPT 生成 & 共创调整 —— 聚焦快速测试

测试覆盖:
1. 4 种关键文档类型 PPT 生成
2. 6 种共创操作类型
"""
import sys, os, json, time, re, uuid
from pathlib import Path
from typing import List, Dict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opencopilot.capabilities.ppt.pipeline import PPTGenerationPipeline

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


def test_ppt_gen(doc_path: str, label: str):
    """单文档 PPT 生成测试"""
    full_path = project_root / doc_path
    if not full_path.exists():
        return {"status": "error", "msg": f"文件不存在: {full_path}"}

    text = full_path.read_text(encoding="utf-8")

    t0 = time.time()
    pipeline = PPTGenerationPipeline()
    result = pipeline.run(text)
    elapsed = round(time.time() - t0, 1)

    slides = result.slides
    types = {}
    layouts = {}
    has_ending = False
    has_title = False
    items_total = 0

    for s in slides:
        st = s.get("type", "unknown")
        types[st] = types.get(st, 0) + 1
        lt = s.get("layout", "unknown")
        layouts[lt] = layouts.get(lt, 0) + 1
        if st == "title": has_title = True
        if st == "ending": has_ending = True
        items_total += len(s.get("items", []))

    score = 5.0
    notes = []
    if len(slides) < 2: score -= 2; notes.append("页数过少")
    if not has_title: score -= 1.5; notes.append("缺封面")
    if not has_ending: score -= 1; notes.append("缺结尾页")
    if len(layouts) < 2: score -= 0.5; notes.append("版式单一")
    if len(layouts) >= 3: score += 0.3; notes.append("版式多样")
    if "three_columns" in layouts: score += 0.3
    score = max(0, min(5, score))

    return {
        "status": "ok", "label": label, "pages": len(slides), "time_s": elapsed,
        "types": types, "layouts": layouts,
        "ending": has_ending, "title": has_title,
        "items": items_total, "score": round(score, 1), "notes": notes
    }


def test_cocreate(label: str, prompt: str):
    """单次共创调整测试"""
    try:
        from opencopilot.agent.caller import call_agent_pipeline_sync

        context = json.dumps({
            "current_slides": SAMPLE_SLIDES,
            "instruction": prompt,
        }, ensure_ascii=False)

        full = ""
        for chunk in call_agent_pipeline_sync(
            text=context, action_type="ppt",
            context_source="ppt_editor", is_new_task=True,
            session_id=f"cc_{uuid.uuid4().hex[:8]}"
        ):
            full += chunk

        # 解析动作
        cleaned = re.sub(r'<[^>]*>', '', full)
        actions = []
        arr_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if arr_match:
            try:
                parsed = json.loads(arr_match.group(0))
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "action" in item:
                            actions.append(item)
            except json.JSONDecodeError:
                pass

        if not actions:
            # 逐行 JSON
            for line in cleaned.split('\n'):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        obj = json.loads(line)
                        if "action" in obj:
                            actions.append(obj)
                    except json.JSONDecodeError:
                        pass

        # 全局替换格式 - 尝试直接解析整个响应为 JSON 对象
        if not actions:
            try:
                obj = json.loads(cleaned.strip())
                if isinstance(obj, dict) and "slides" in obj:
                    actions.append({"action": "full_replace", "slides": obj["slides"]})
            except json.JSONDecodeError:
                # 尝试提取 {"slides": [...]} 格式
                start = cleaned.find('{"slides"')
                if start >= 0:
                    # 从 start 开始找匹配的 }
                    depth = 0
                    end = start
                    for i in range(start, len(cleaned)):
                        if cleaned[i] == '{':
                            depth += 1
                        elif cleaned[i] == '}':
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                    if end > start:
                        try:
                            obj = json.loads(cleaned[start:end])
                            if isinstance(obj, dict) and "slides" in obj:
                                actions.append({"action": "full_replace", "slides": obj["slides"]})
                        except json.JSONDecodeError:
                            pass

        action_types = [a.get("action", "?") for a in actions]
        return {
            "label": label, "status": "ok" if actions else "no_action",
            "actions": len(actions), "types": action_types,
            "raw_len": len(full)
        }

    except Exception as e:
        return {"label": label, "status": "error", "error": str(e)}


def main():
    print("=" * 60)
    print("  PPT 生成 & 共创调整 —— 聚焦测试")
    print("=" * 60)

    # ---- Part 1: PPT Generation (4 docs) ----
    print("\n📊 Part 1: PPT 生成测试 (4 种文档)")
    print("-" * 60)

    ppt_tests = [
        ("test_docs/marketing_plan.md", "营销方案(表格+策略)"),
        ("test_docs/ai_agent_whitepaper.md", "AI白皮书(代码+实验)"),
        ("test_docs/budget_report.md", "预算报告(数字密集)"),
        ("test_docs/api_spec.md", "API规格(结构化)"),
    ]

    ppt_results = []
    for path, label in ppt_tests:
        print(f"\n🔄 {label}...")
        r = test_ppt_gen(path, label)
        ppt_results.append(r)
        status = "✅" if r["status"] != "error" else "❌"
        if r.get("status") == "error":
            print(f"  ❌ {r.get('error', r.get('msg', ''))}")
        else:
            print(f"  {status} {r['pages']}页 | {r['time_s']}s | "
                  f"布局:{list(r['layouts'].keys())} | "
                  f"结尾:{'✓' if r['ending'] else '✗'} | "
                  f"评分:{r['score']}/5.0")
            if r["notes"]:
                print(f"    备注: {', '.join(r['notes'])}")

    # PPT Summary
    valid = [r for r in ppt_results if "pages" in r]
    print(f"\n{'='*60}")
    print(f"📋 PPT 生成汇总:")
    if valid:
        avg_score = sum(r["score"] for r in valid) / len(valid)
        avg_pages = sum(r["pages"] for r in valid) / len(valid)
        ending_ok = sum(1 for r in valid if r["ending"])
        print(f"  平均页数: {avg_pages:.1f} | 平均评分: {avg_score:.2f}/5.0")
        print(f"  结尾页: {ending_ok}/{len(valid)}")
        for r in valid:
            print(f"  [{r['label']}] {r['pages']}p | {r['score']}/5.0 | "
                  f"ending={'✓' if r['ending'] else '✗'} | "
                  f"layouts={list(r['layouts'].keys())}")

    # ---- Part 2: Co-creation Tests ----
    print(f"\n\n{'='*60}")
    print(f"🤝 Part 2: 共创调整测试 (6 种操作)")
    print("-" * 60)

    cc_tests = [
        ("修改标题", "把第一页标题改成「2026年度AI产品战略发布会」"),
        ("添加要点", "在产品亮点页添加一条要点：智能体协作"),
        ("修改版式", "把实施计划页面改为 image_right 版式"),
        ("删除要点", "删除产品亮点页中的「实时推理」"),
        ("全局重新生成", "全部重新生成，主题改为云计算平台发布会"),
        ("转换为表格", "把方案对比页转换为表格展示"),
    ]

    cc_results = []
    for label, prompt in cc_tests:
        print(f"\n🔄 {label}...")
        r = test_cocreate(label, prompt)
        cc_results.append(r)
        if r["status"] == "ok":
            print(f"  ✅ {r['actions']}个动作 | 类型: {r['types']}")
        elif r["status"] == "no_action":
            print(f"  ⚠️ 未解析出动作 (原始响应 {r['raw_len']} 字符)")
        else:
            print(f"  ❌ {r.get('error', '')}")

    # Co-creation Summary
    ok = sum(1 for r in cc_results if r["status"] == "ok")
    print(f"\n{'='*60}")
    print(f"📋 共创调整汇总: {ok}/{len(cc_results)} 通过")

    all_types = []
    for r in cc_results:
        all_types.extend(r.get("types", []))
    from collections import Counter
    type_dist = Counter(all_types)
    print(f"  动作类型分布: {dict(type_dist)}")

    # ---- Final ----
    print(f"\n{'='*60}")
    print(f"🏆 综合结论:")
    ppt_pass = len(valid)
    cc_pass = ok
    print(f"  PPT 生成: {ppt_pass}/{len(ppt_tests)} 有效")
    print(f"  共创调整: {cc_pass}/{len(cc_tests)} 通过")
    if valid:
        print(f"  PPT 平均评分: {avg_score:.2f}/5.0")


if __name__ == "__main__":
    main()
