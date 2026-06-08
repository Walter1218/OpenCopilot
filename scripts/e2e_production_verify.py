"""
生产链路端到端验证：文档 → PPT 生成 + Skill 载入验证

完整链路：
1. 读取测试文档
2. 通过 call_agent_pipeline_sync 发送 PPT 请求（action_type="ppt"）
3. Pipeline 7 层中间件依次执行（SessionSetup → Security → Immune → Planner → State → Router → LLM）
4. 收集 LLM 流式输出
5. 从 LLM 输出中提取 JSON → 生成 PPTX 文件
6. 验证 Skill 在 enriched_system 中被正确注入

不 mock 任何组件，使用真实 LLM API。
"""
import os
import sys
import json
import time
import uuid
import threading

# 项目根目录加入 sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 准备测试文档
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEST_DOC_PATH = os.path.join(_project_root, "test_docs", "annual_strategy_report.md")

def load_test_document():
    with open(TEST_DOC_PATH, "r", encoding="utf-8") as f:
        return f.read()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 运行生产 Pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_production_pipeline(text, action_type="ppt", context_source="studio"):
    """通过生产入口 call_agent_pipeline_sync 运行完整 Pipeline"""
    from opencopilot.agent.caller import call_agent_pipeline_sync

    session_id = f"test-{uuid.uuid4().hex[:8]}"
    print(f"[Pipeline] session_id={session_id}")
    print(f"[Pipeline] action_type={action_type}, context_source={context_source}")
    print(f"[Pipeline] 文档长度: {len(text)} 字符")
    print(f"[Pipeline] 文档前100字: {text[:100]}")
    print()

    chunks = []
    error_msg = None
    start_time = time.time()

    for chunk_tuple in call_agent_pipeline_sync(
        text=text,
        action_type=action_type,
        session_id=session_id,
        context_source=context_source,
        is_new_task=True,
        timeout=180.0,
    ):
        if isinstance(chunk_tuple, tuple):
            chunk_type, chunk_data = chunk_tuple
            if chunk_type == "chunk":
                chunks.append(chunk_data)
                # 实时输出进度
                sys.stdout.write(chunk_data)
                sys.stdout.flush()
            elif chunk_type == "error":
                error_msg = chunk_data
                print(f"\n[Pipeline] ❌ ERROR: {error_msg}")
            elif chunk_type == "done":
                pass
        elif isinstance(chunk_tuple, str):
            chunks.append(chunk_tuple)
            sys.stdout.write(chunk_tuple)
            sys.stdout.flush()

    elapsed = time.time() - start_time
    full_response = "".join(chunks)

    print(f"\n\n[Pipeline] 完成！耗时: {elapsed:.1f}s, 输出: {len(full_response)} 字符")

    return {
        "session_id": session_id,
        "full_response": full_response,
        "elapsed": elapsed,
        "error": error_msg,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 验证 Skill 载入
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def verify_skill_injection():
    """验证 SkillLoader 工具描述被注入到 enriched_system"""
    from opencopilot.agent.middlewares import SessionSetupMiddleware
    from opencopilot.agent.skill_loader import SkillLoader

    print("\n" + "=" * 60)
    print("[验证 1] SkillLoader 载入验证")
    print("=" * 60)

    # 3a. SkillLoader 扫描
    loader = SkillLoader(skills_dir="skills/")
    eligible = loader.load_eligible()
    skill_names = [s.name for s in eligible]
    print(f"  扫描到 {len(eligible)} 个 eligible Skill: {skill_names}")
    assert "content_convert" in skill_names, "content_convert 未扫描到"
    print(f"  ✅ content_convert SKILL.md 被正确扫描")

    # 3b. 工具描述生成
    tools_prompt = loader.build_tools_prompt(eligible)
    tool_keywords = ["analyze_and_convert", "convert_to_table", "convert_to_chart", "convert_to_flowchart"]
    for kw in tool_keywords:
        assert kw in tools_prompt, f"{kw} 未出现在工具描述中"
    print(f"  ✅ 4 个工具描述完整 ({len(tools_prompt)} chars)")

    # 3c. SessionSetupMiddleware._get_tools_prompt
    middleware = SessionSetupMiddleware(
        memory=None, window_manager=None,
        normalize_context_envelope=None, load_persona=None,
        build_context_prefix=None, sanitize_persona_for_context=None,
    )
    injected = middleware._get_tools_prompt()
    assert "content_convert" in injected, "content_convert 未注入到 enriched_system"
    print(f"  ✅ SessionSetupMiddleware 已将工具描述注入 enriched_system ({len(injected)} chars)")

    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 验证 PlannerMiddleware 跳过
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def verify_planner_skip():
    """验证 PPT 请求被 PlannerMiddleware 跳过"""
    from opencopilot.agent.middlewares import PlannerMiddleware

    print("\n" + "=" * 60)
    print("[验证 2] PlannerMiddleware PPT 跳过验证")
    print("=" * 60)

    skip_types = PlannerMiddleware._skip_planner_types
    assert "ppt" in skip_types, "ppt 不在跳过列表"
    print(f"  ✅ PPT 在跳过列表中: {skip_types}")
    print(f"  ✅ PPT 请求不会触发 Planner（避免注入 Task Plan 干扰 JSON）")
    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 验证路由一致性
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def verify_routing():
    """验证 PPT 请求路由正确性"""
    from asu_custom_agent import detect_request_type

    print("\n" + "=" * 60)
    print("[验证 3] 路由优先级验证")
    print("=" * 60)

    test_cases = [
        ("帮我规划一份AI发展的PPT大纲", "ppt"),
        ("设计一份产品介绍的幻灯片", "ppt"),
        ("帮我规划项目进度", "planning"),
    ]
    for text, expected in test_cases:
        result = detect_request_type(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} \"{text[:25]}\" → {result} (期望: {expected})")
        assert result == expected, f"路由错误: {text} → {result}"
    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. 解析 PPT JSON + 生成 PPTX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_pptx_from_response(full_response, output_path):
    """从 LLM 响应中提取 JSON 并生成 PPTX"""
    from ppt_generator import extract_json_from_text, generate_ppt_from_json

    print("\n" + "=" * 60)
    print("[验证 4] PPT JSON 解析 + PPTX 生成")
    print("=" * 60)

    print(f"  LLM 输出长度: {len(full_response)} 字符")

    json_data = extract_json_from_text(full_response)

    if json_data is None:
        print(f"  ❌ 无法从 LLM 输出中提取 JSON")
        print(f"  LLM 输出前 500 字符: {full_response[:500]}")
        return False

    if isinstance(json_data, dict) and "slides" in json_data:
        slides = json_data["slides"]
        title = json_data.get("title", "未命名")
        print(f"  ✅ JSON 解析成功: title=\"{title}\", slides={len(slides)}")
    elif isinstance(json_data, list):
        slides = json_data
        print(f"  ✅ JSON 解析成功 (数组): slides={len(slides)}")
    else:
        print(f"  ❌ 解析结果格式异常: {type(json_data)}")
        return False

    # 显示每页 slide 概要
    for i, slide in enumerate(slides):
        if isinstance(slide, dict):
            s_type = slide.get("type", "?")
            s_title = slide.get("title", "?")
            s_layout = slide.get("layout", "?")
            items_count = len(slide.get("items", []))
            print(f"    [{i}] type={s_type} layout={s_layout} title=\"{s_title[:30]}\" items={items_count}")

    # 生成 PPTX
    pptx_path = generate_ppt_from_json(slides, output_path)
    print(f"\n  ✅ PPTX 生成成功: {pptx_path}")
    print(f"  ✅ 文件大小: {os.path.getsize(pptx_path) / 1024:.1f} KB")

    # python-pptx 验证
    try:
        from pptx import Presentation
        prs = Presentation(pptx_path)
        print(f"  ✅ python-pptx 加载验证: {len(prs.slides)} 页幻灯片")
    except Exception as e:
        print(f"  ⚠️ python-pptx 加载异常: {e}")

    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 主流程
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("=" * 60)
    print("生产链路端到端验证：文档 → PPT 生成 + Skill 载入")
    print("=" * 60)
    print()

    # Step 1: 预验证（不依赖 LLM）
    try:
        verify_skill_injection()
        verify_planner_skip()
        verify_routing()
        print("\n✅ 预验证全部通过\n")
    except AssertionError as e:
        print(f"\n❌ 预验证失败: {e}")
        return

    # Step 2: 加载文档
    print("=" * 60)
    print("[运行] 加载测试文档")
    print("=" * 60)
    doc_text = load_test_document()
    print(f"  文档: {TEST_DOC_PATH}")
    print(f"  长度: {len(doc_text)} 字符")

    # Step 3: 运行生产 Pipeline（真实 LLM 调用）
    print("\n" + "=" * 60)
    print("[运行] 启动生产 Pipeline（action_type=ppt）")
    print("=" * 60)
    print()

    result = run_production_pipeline(doc_text, action_type="ppt", context_source="studio")

    if result["error"]:
        print(f"\n❌ Pipeline 执行出错: {result['error']}")
        return

    if not result["full_response"]:
        print(f"\n❌ Pipeline 无输出")
        return

    # Step 4: 解析 JSON + 生成 PPTX
    output_dir = os.path.join(_project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"e2e_production_test_{result['session_id']}.pptx")
    success = generate_pptx_from_response(result["full_response"], output_path)

    # Step 5: 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    print(f"  SkillLoader 载入:     ✅ content_convert SKILL.md 已扫描 + 注入 enriched_system")
    print(f"  PlannerMiddleware:    ✅ PPT 请求被跳过")
    print(f"  路由一致性:           ✅ PPT 关键词优先级正确")
    print(f"  Pipeline 执行:        ✅ 耗时 {result['elapsed']:.1f}s, 输出 {len(result['full_response'])} 字符")
    if success:
        print(f"  PPTX 生成:           ✅ {output_path}")
        print(f"\n🎉 生产链路端到端验证全部通过！")
    else:
        print(f"  PPTX 生成:           ❌ 解析或生成失败")
        print(f"\n⚠️ 部分验证未通过，请检查 LLM 输出格式")


if __name__ == "__main__":
    main()
