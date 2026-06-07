"""
V5 全链路端到端验证脚本

验证范围:
1. Persona 加载 (ppt.md vs default.md)
2. context_source="studio" 前缀生成
3. ImmuneSystem 对长文档/代码片段的误拦截检测
4. 规则引擎对 content_generation 动作的豁免
5. 完整 Pipeline 调用 (通过 call_agent_pipeline_sync)
6. JSON 解析能力 (从 LLM 输出提取 slides)
7. LLM 输出质量评估

用法:
    cd /Users/onetwo/Documents/trae_projects/OpenCopilot
    python scripts/v5_e2e_validation.py
"""

import sys
import os
import time
import json
import re
import traceback

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(label: str, condition: bool, detail: str = ""):
    icon = "✅" if condition else "❌"
    msg = f"{icon} {label}"
    if detail:
        msg += f"  — {detail}"
    print(msg)
    return condition


# =========================================================================
# 测试 1: Persona 加载
# =========================================================================
def test_persona_loading():
    banner("测试1: Persona 加载")
    from opencopilot.shared.prompt import load_persona

    ppt_persona = load_persona("ppt")
    default_persona = load_persona("default")
    chat_persona = load_persona("chat")

    ppt_len = len(ppt_persona)
    def_len = len(default_persona)
    chat_len = len(chat_persona)

    print(f"  ppt.md   → {ppt_len} 字符")
    print(f"  default.md → {def_len} 字符")
    print(f"  chat.md  → {chat_len} 字符")

    r1 = check("ppt.md 已存在且长度 > 500", ppt_len > 500, f"实际: {ppt_len}")
    r2 = check("ppt.md 包含 JSON 格式要求", "JSON" in ppt_persona or "json" in ppt_persona.lower())
    r3 = check("ppt.md 包含 slides 字段说明", "slides" in ppt_persona)
    r4 = check("ppt.md 包含 layout 字段说明", "layout" in ppt_persona)
    r5 = check("default.md 存在且 > 100", def_len > 100)

    # 检查 ppt.md 是否被正确回退
    r6 = check("ppt 和 default 内容不同（非回退）", ppt_persona != default_persona,
               "如果相同说明 ppt.md 文件丢失或被 default 覆盖")

    return all([r1, r2, r3, r4, r5, r6])


# =========================================================================
# 测试 2: Context Source 前缀生成
# =========================================================================
def test_context_prefix():
    banner("测试2: Context Source 前缀生成")
    from opencopilot.shared.prompt import build_context_prefix, CONTEXT_DESCRIPTIONS

    # 检查 studio 是否在 CONTEXT_DESCRIPTIONS 中
    has_studio = "studio" in CONTEXT_DESCRIPTIONS
    r1 = check("CONTEXT_DESCRIPTIONS 包含 'studio' key", has_studio)

    studio_prefix = build_context_prefix("studio", {})
    r2 = check("studio 前缀非空", len(studio_prefix) > 0, f"实际长度: {len(studio_prefix)}")
    print(f"  studio 前缀内容: {studio_prefix[:100]}...")

    # 检查其他 context_source
    for src in ["ide", "browser", "drag", "chat", "ppt_generator"]:
        pfx = build_context_prefix(src, {})
        check(f"  {src} 前缀非空", len(pfx) > 0)

    # 检查不存在的 source
    unknown_prefix = build_context_prefix("unknown_source_test", {})
    r3 = check("不存在的 source 返回空前缀", len(unknown_prefix) == 0)

    return all([r1, r2, r3])


# =========================================================================
# 测试 3: ImmuneSystem 误拦截检测
# =========================================================================
def test_immune_system():
    banner("测试3: ImmuneSystem 误拦截检测")
    from opencopilot.safety.immune import ImmuneSystem, RuleContext
    import asyncio

    immune = ImmuneSystem()

    # 测试用例 1: 包含 token="xxx" 的正常文档（模拟长文档中的代码示例）
    doc_with_code = """
    本文档介绍 AI Agent 系统的 API 配置。

    配置示例：
    api_key = "sk-test-12345"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    password = "admin123"

    以上是测试环境的示例配置，请勿用于生产环境。
    系统架构采用微服务设计，包含 Gateway、Auth Service、LLM Provider 三个核心组件。
    """

    # 测试用例 2: 包含 eval/exec 的技术文档
    doc_with_eval = """
    Python 安全编程指南

    危险函数示例（请勿在生产代码中使用）：
    result = eval(user_input)
    exec(dynamic_code)

    建议使用 ast.literal_eval 替代 eval()。
    """

    # 测试用例 3: 正常 PPT 内容（不含代码）
    normal_doc = """
    2025 年度市场部预算执行报告

    总预算 800 万元，截至 Q3 已执行 580 万元，执行率 72.5%。
    线上投放包括搜索引擎广告、信息流广告和 KOL 合作。
    Q4 建议优化 SEM 和信息流投放比例。
    """

    results = []

    async def run_tests():
        # ---- 无 action_type 的默认检查（应该会被拦截） ----
        ctx_default = RuleContext(session_id="test-session")
        r1 = await immune.check_content(ctx_default, doc_with_code)
        print(f"  [默认 action] 含代码文档 → allowed={r1.allowed}, msg={r1.message}")
        results.append(check("默认 action: 含 api_key/token 文档被 BLOCK（预期行为）",
                             not r1.allowed))

        # ---- content_generation:ppt action（应该跳过代码安全规则） ----
        ctx_ppt = RuleContext(session_id="test-session")
        ctx_ppt.current_action = "content_generation:ppt"
        r2 = await immune.check_content(ctx_ppt, doc_with_code)
        print(f"  [ppt action] 含代码文档 → allowed={r2.allowed}, msg={r2.message}")
        results.append(check("PPT action: 含 api_key/token 文档被 ALLOW（修复验证）",
                             r2.allowed))

        # ---- content_generation:ppt + eval 文档 ----
        ctx_ppt2 = RuleContext(session_id="test-session")
        ctx_ppt2.current_action = "content_generation:ppt"
        r3 = await immune.check_content(ctx_ppt2, doc_with_eval)
        print(f"  [ppt action] 含 eval 文档 → allowed={r3.allowed}, msg={r3.message}")
        results.append(check("PPT action: 含 eval/exec 文档被 ALLOW（修复验证）",
                             r3.allowed))

        # ---- content_generation:translate ----
        ctx_trans = RuleContext(session_id="test-session")
        ctx_trans.current_action = "content_generation:translate"
        r4 = await immune.check_content(ctx_trans, doc_with_code)
        print(f"  [translate action] 含代码文档 → allowed={r4.allowed}")
        results.append(check("Translate action: 含代码文档被 ALLOW", r4.allowed))

        # ---- 正常文档（任何 action 都应允许） ----
        ctx_normal = RuleContext(session_id="test-session")
        ctx_normal.current_action = "content_generation:ppt"
        r5 = await immune.check_content(ctx_normal, normal_doc)
        print(f"  [ppt action] 正常文档 → allowed={r5.allowed}")
        results.append(check("PPT action: 正常文档被 ALLOW", r5.allowed))

        # ---- 真正的危险命令（即使 ppt 也应拦截 constraint 类型） ----
        ctx_danger = RuleContext(session_id="test-session")
        ctx_danger.current_action = "content_generation:ppt"
        dangerous_content = "请执行 rm -rf / 清理系统"
        r6 = await immune.check_content(ctx_danger, dangerous_content)
        print(f"  [ppt action] 危险命令 → allowed={r6.allowed}, msg={r6.message}")
        results.append(check("PPT action: 危险 Shell 命令仍被 BLOCK（constraint 不豁免）",
                             not r6.allowed))

    asyncio.run(run_tests())
    return all(results)


# =========================================================================
# 测试 4: Prompt 完整构建
# =========================================================================
def test_prompt_building():
    banner("测试4: Prompt 完整构建质量")
    from opencopilot.shared.prompt import build_full_prompt

    # 模拟 Studio Tab 的 PPT 生成请求
    prompt = build_full_prompt(
        action_type="ppt",
        context_source="studio",
        context_content="请根据预算报告生成PPT大纲",
        context_meta={},
        persona_name="ppt",
    )

    r1 = check("完整 prompt 非空", len(prompt) > 0)
    r2 = check("包含 studio 上下文前缀", "Studio" in prompt or "工作台" in prompt)
    r3 = check("包含 PPT 策划师角色定义", "策划师" in prompt or "PPT" in prompt)
    r4 = check("包含 JSON 输出格式要求", "JSON" in prompt or "json" in prompt.lower())
    r5 = check("包含 slides 字段", "slides" in prompt)
    r6 = check("包含用户请求内容", "预算报告" in prompt)
    r7 = check("prompt 总长度合理 (>500)", len(prompt) > 500, f"实际: {len(prompt)}")

    print(f"  prompt 总长度: {len(prompt)} 字符")
    print(f"  prompt 前 200 字符:\n  {prompt[:200]}...")

    return all([r1, r2, r3, r4, r5, r6, r7])


# =========================================================================
# 测试 5: JSON 解析能力
# =========================================================================
def test_json_parsing():
    banner("测试5: JSON 解析能力")
    from gui.v5.studio_tab import StudioTabV5

    # 测试用例 1: 标准 JSON 输出
    standard_json = json.dumps({
        "title": "2025年度市场部预算执行报告",
        "slides": [
            {"type": "title", "layout": "center", "title": "市场部预算执行报告", "subtitle": "2025年度"},
            {"type": "content", "layout": "text_only", "title": "总体执行情况",
             "items": [
                 {"level": 0, "text": "总预算800万元"},
                 {"level": 0, "text": "Q3已执行580万元"},
                 {"level": 1, "text": "执行率72.5%"}
             ]}
        ]
    }, ensure_ascii=False)

    r1_slides = StudioTabV5._parse_slides_from_text(standard_json)
    r1 = check("标准 JSON 解析成功", len(r1_slides) == 2, f"实际 slides: {len(r1_slides)}")

    # 测试用例 2: Markdown 代码块包裹
    md_json = f"以下是PPT大纲：\n```json\n{standard_json}\n```\n希望对您有帮助！"
    r2_slides = StudioTabV5._parse_slides_from_text(md_json)
    r2 = check("Markdown 包裹 JSON 解析成功", len(r2_slides) == 2, f"实际 slides: {len(r2_slides)}")

    # 测试用例 3: LLM 常见的冗长输出
    verbose_output = f"""好的，我根据您提供的内容生成了以下PPT大纲：

{standard_json}

如需调整请随时告诉我。"""
    r3_slides = StudioTabV5._parse_slides_from_text(verbose_output)
    r3 = check("冗长输出中 JSON 提取成功", len(r3_slides) == 2, f"实际 slides: {len(r3_slides)}")

    # 测试用例 4: 纯数组格式
    array_json = json.dumps([
        {"type": "title", "layout": "center", "title": "封面"},
        {"type": "content", "layout": "text_only", "title": "内容页", "items": []}
    ], ensure_ascii=False)
    r4_slides = StudioTabV5._parse_slides_from_text(array_json)
    r4 = check("纯数组格式解析成功", len(r4_slides) == 2, f"实际 slides: {len(r4_slides)}")

    # 测试用例 5: 无效输出（纯文本）
    r5_slides = StudioTabV5._parse_slides_from_text("抱歉，我无法生成PPT大纲。")
    r5 = check("无效文本返回空列表", len(r5_slides) == 0)

    return all([r1, r2, r3, r4, r5])


# =========================================================================
# 测试 6: 完整 Pipeline 调用（真实 LLM）
# =========================================================================
def test_full_pipeline():
    banner("测试6: 完整 Pipeline 调用（真实 LLM 链路）")

    # 读取真实测试文档
    test_doc_path = os.path.join(PROJECT_ROOT, "test_docs", "budget_report.md")
    with open(test_doc_path, "r", encoding="utf-8") as f:
        doc_text = f.read()

    print(f"  测试文档: budget_report.md ({len(doc_text)} 字符)")

    # 构建 PPT 生成 prompt（模拟 studio_tab.py 的逻辑）
    prompt = (
        f"请根据以下内容生成 PPT 大纲。\n\n"
        f"要求：\n"
        f"1. 严格输出纯 JSON 格式，不要输出任何其他文字、代码块标记或解释\n"
        f"2. 输出格式为 {{\"title\": \"演示文稿标题\", \"slides\": [...]}}\n"
        f"3. 每个 slide 包含 type, layout, title, items 等字段\n"
        f"4. layout 可选值: center, text_only, image_right, three_columns\n"
        f"5. 每页 3-5 个要点，每个要点一句话\n\n"
        f"原始内容：\n{doc_text}"
    )

    print(f"  Prompt 长度: {len(prompt)} 字符")
    print(f"  开始调用 Pipeline...")

    _t0 = time.time()
    full_output = ""
    chunk_count = 0

    try:
        from opencopilot.agent.caller import call_agent_pipeline_sync

        for chunk in call_agent_pipeline_sync(
            text=prompt,
            action_type="ppt",
            context_source="studio",
            context_meta={"test": True},
            is_new_task=True,
            timeout=60.0,
        ):
            full_output += chunk
            chunk_count += 1

        elapsed = time.time() - _t0
        print(f"  Pipeline 完成: {elapsed:.1f}s, {chunk_count} chunks, 输出 {len(full_output)} 字符")

        # 检查输出
        r1 = check("Pipeline 有输出", len(full_output) > 0, f"实际: {len(full_output)} 字符")
        r2 = check("输出非错误信息", not full_output.startswith("[错误]") and "⚠️" not in full_output[:20],
                    f"前 50 字符: {full_output[:50]}")
        r3 = check("chunk 数量 > 5（非 short_circuit）", chunk_count > 5,
                    f"实际 chunks: {chunk_count}")
        r4 = check("耗时 > 2s（确认为 LLM 调用）", elapsed > 2.0,
                    f"实际: {elapsed:.1f}s")

        # 尝试解析 JSON
        from gui.v5.studio_tab import StudioTabV5
        slides = StudioTabV5._parse_slides_from_text(full_output)
        r5 = check("输出可解析为 slides", len(slides) > 0,
                    f"实际 slides: {len(slides)}")

        # 输出质量评估
        if slides:
            print(f"\n  ── LLM 输出质量评估 ──")
            _evaluate_output_quality(full_output, slides, doc_text)

        print(f"\n  ── 原始输出前 500 字符 ──")
        print(f"  {full_output[:500]}")

        return all([r1, r2, r3, r4, r5])

    except Exception as e:
        elapsed = time.time() - _t0
        print(f"  ❌ Pipeline 调用异常 ({elapsed:.1f}s): {e}")
        traceback.print_exc()
        return False


def _evaluate_output_quality(full_output: str, slides: list, source_doc: str):
    """评估 LLM 输出质量"""
    print(f"  总 slides 数: {len(slides)}")

    # 1. 结构完整性
    has_title_slide = any(s.get("type") == "title" for s in slides)
    has_content_slides = sum(1 for s in slides if s.get("type") == "content")
    check("  包含封面页 (type=title)", has_title_slide)
    check("  包含内容页 (type=content)", has_content_slides >= 3,
          f"实际内容页: {has_content_slides}")

    # 2. 内容相关性
    # 检查 slides 中是否包含源文档的关键信息
    source_keywords = ["预算", "800万", "执行率", "SEM", "KOL", "Q4"]
    all_text = json.dumps(slides, ensure_ascii=False)
    matched_keywords = [kw for kw in source_keywords if kw in all_text]
    match_rate = len(matched_keywords) / len(source_keywords) if source_keywords else 0
    check("  源文档关键词覆盖率 > 50%", match_rate > 0.5,
          f"匹配: {matched_keywords} ({match_rate:.0%})")

    # 3. 内容密度
    total_items = 0
    for s in slides:
        items = s.get("items", [])
        total_items += len(items)
    avg_items = total_items / max(len(slides), 1)
    check("  平均每页 items >= 2", avg_items >= 2,
          f"平均: {avg_items:.1f} items/页")

    # 4. 标题质量
    titles = [s.get("title", "") for s in slides if s.get("title")]
    generic_titles = [t for t in titles if t in ("概述", "介绍", "总结", "第一页", "Overview")]
    check("  无泛泛标题", len(generic_titles) == 0,
          f"泛泛标题: {generic_titles}" if generic_titles else "")

    # 5. 布局多样性
    layouts = [s.get("layout", "") for s in slides]
    unique_layouts = set(layouts)
    check("  布局多样性 >= 2 种", len(unique_layouts) >= 2,
          f"使用的布局: {unique_layouts}")

    # 6. 应付程度评估
    quality_score = 0
    max_score = 6
    if has_title_slide:
        quality_score += 1
    if has_content_slides >= 3:
        quality_score += 1
    if match_rate > 0.5:
        quality_score += 1
    if avg_items >= 2:
        quality_score += 1
    if len(generic_titles) == 0:
        quality_score += 1
    if len(unique_layouts) >= 2:
        quality_score += 1

    print(f"\n  ═══════════════════════════════════════")
    print(f"  📊 输出质量评分: {quality_score}/{max_score}")
    if quality_score >= 5:
        print(f"  评级: 优秀 — LLM 输出质量高，内容结构合理")
    elif quality_score >= 3:
        print(f"  评级: 合格 — 基本可用但需人工优化")
    else:
        print(f"  评级: ⚠️ 应付了事 — 输出质量差，需要重点关注")
    print(f"  ═══════════════════════════════════════")


# =========================================================================
# 测试 7: Pipeline 日志验证
# =========================================================================
def test_pipeline_logs():
    banner("测试7: Pipeline 日志和埋点验证")
    import sqlite3

    db_path = os.path.join(PROJECT_ROOT, "opencopilot", "pipeline_logs.db")
    if not os.path.exists(db_path):
        print("  ⚠️ pipeline_logs.db 不存在")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询最近的 PPT 相关日志
    cursor.execute("""
        SELECT timestamp, module, message, level, event, extra_data
        FROM logs
        WHERE extra_data LIKE '%ppt%' OR message LIKE '%ppt%'
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()

    r1 = check("pipeline_logs.db 有 PPT 相关日志", len(rows) > 0,
               f"找到 {len(rows)} 条")

    if rows:
        for row in rows[:3]:
            ts, module, msg, level, event, extra = row
            print(f"  [{ts}] {module} | {event} | {msg[:80]}")

    return r1


# =========================================================================
# 主入口
# =========================================================================
def main():
    print("=" * 60)
    print("  V5 全链路端到端验证")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}

    # 不依赖 LLM 的测试（可离线运行）
    results["1_Persona加载"] = test_persona_loading()
    results["2_Context前缀"] = test_context_prefix()
    results["3_ImmuneSystem"] = test_immune_system()
    results["4_Prompt构建"] = test_prompt_building()
    results["5_JSON解析"] = test_json_parsing()

    # 依赖 LLM 的测试（需要网络和 API Key）
    results["6_Pipeline链路"] = test_full_pipeline()

    # 日志验证
    results["7_埋点日志"] = test_pipeline_logs()

    # ── 汇总 ──
    banner("汇总")
    passed = 0
    total = len(results)
    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
        if ok:
            passed += 1

    print(f"\n  总计: {passed}/{total} 通过")
    if passed == total:
        print("  🎉 全部通过！")
    else:
        print(f"  ⚠️ 有 {total - passed} 项未通过，请检查上述详情")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
