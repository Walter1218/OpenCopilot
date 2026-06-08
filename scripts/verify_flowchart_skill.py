#!/usr/bin/env python3
"""
content_convert Skill 流程图转换验证脚本

验证内容：
1. Skill 载入状态
2. convert_to_flowchart 功能
3. 共创模式 API 接口调用
"""

import sys
import os
import json
import asyncio

# 确保项目根目录在 sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def banner(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def verify_skill_loading():
    """验证 1: Skill 载入状态"""
    banner("验证 1: Skill 载入状态")
    
    from opencopilot.agent.skill_loader import SkillLoader
    
    loader = SkillLoader(skills_dir="skills/")
    eligible = loader.load_eligible()
    
    results = {
        "loaded_skills": [s.name for s in eligible],
        "content_convert_found": "content_convert" in [s.name for s in eligible],
        "tools_count": 0,
        "has_flowchart_tool": False,
        "prompt_length": 0,
    }
    
    spec = loader.skills.get("content_convert")
    if spec:
        tool_names = [t.name for t in spec.tools]
        results["tools_count"] = len(tool_names)
        results["has_flowchart_tool"] = "convert_to_flowchart" in tool_names
        print(f"✓ content_convert 工具: {tool_names}")
    
    tools_prompt = loader.build_tools_prompt(eligible)
    results["prompt_length"] = len(tools_prompt)
    results["prompt_has_flowchart"] = "convert_to_flowchart" in tools_prompt
    
    print(f"✓ 已载入 Skills: {results['loaded_skills']}")
    print(f"✓ System Prompt 长度: {results['prompt_length']} chars")
    print(f"✓ 包含 convert_to_flowchart: {results['prompt_has_flowchart']}")
    
    return results


def verify_flowchart_conversion():
    """验证 2: convert_to_flowchart 功能"""
    banner("验证 2: ContentConvertSkill.convert_to_flowchart")
    
    from opencopilot.capabilities.skill import ContentConvertSkill
    from opencopilot.capabilities.skill.models import SkillContext
    
    skill = ContentConvertSkill()
    
    test_cases = [
        {
            "name": "签名算法步骤",
            "text": """签名步骤：
1. 将请求参数按 key 字典序排序
2. 拼接为 key1=value1&key2=value2 格式
3. 末尾追加 &key=MERCHANT_SECRET（商户密钥）
4. 计算 MD5 哈希值，转大写""",
            "title": "签名算法流程"
        },
        {
            "name": "开发流程",
            "text": "需求分析\n方案设计\n编码实现\n测试验证\n上线部署",
            "title": "软件开发流程"
        },
        {
            "name": "箭头分隔",
            "text": "用户下单 → 支付确认 → 仓库发货 → 物流配送 → 签收完成",
            "title": "订单流程"
        }
    ]
    
    results = []
    for tc in test_cases:
        ctx = SkillContext(
            intent="convert_to_flowchart",
            input_data={"text": tc["text"], "title": tc["title"]}
        )
        
        result = asyncio.run(skill.execute(ctx))
        
        success = result.success and result.data.get("action") == "convert_flowchart"
        flowchart_data = result.data.get("flowchart_data", {})
        steps_count = len(flowchart_data.get("flowchart_data", {}).get("steps", []))
        
        print(f"{'✓' if success else '✗'} {tc['name']}: steps={steps_count}")
        results.append({"name": tc["name"], "success": success, "steps_count": steps_count})
    
    return results


def verify_cocreation_api():
    """验证 3: 共创模式 API 接口"""
    banner("验证 3: 共创模式 API 接口调用")
    
    from opencopilot.agent.caller import call_agent_pipeline_sync
    
    # 模拟 PPT 页面数据
    current_slides = [
        {
            "type": "title",
            "layout": "center",
            "title": "支付网关 API v2.3",
            "subtitle": "接口文档"
        },
        {
            "type": "content",
            "layout": "text_only",
            "title": "签名算法",
            "items": [
                {"level": 0, "text": "1. 将请求参数按 key 字典序排序"},
                {"level": 0, "text": "2. 拼接为 key1=value1&key2=value2 格式"},
                {"level": 0, "text": "3. 末尾追加 &key=MERCHANT_SECRET（商户密钥）"},
                {"level": 0, "text": "4. 计算 MD5 哈希值，转大写"}
            ]
        }
    ]
    
    instruction = "把签名算法页面转换为流程图展示"
    
    context = json.dumps({
        "current_slides": current_slides,
        "instruction": instruction,
    }, ensure_ascii=False)
    
    print(f"指令: {instruction}")
    print("正在调用 Agent Pipeline...")
    
    full_response = ""
    chunk_count = 0
    for chunk in call_agent_pipeline_sync(
        text=context,
        action_type="ppt",
        context_source="ppt_editor",
        is_new_task=True,
        session_id="flowchart_verify"
    ):
        full_response += chunk
        chunk_count += 1
    
    # 解析响应
    import re
    actions = []
    for line in full_response.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
                if "action" in obj:
                    actions.append(obj)
            except json.JSONDecodeError:
                pass
    
    # 检查是否包含流程图数据
    has_flowchart = any(
        "flowchart" in json.dumps(a, ensure_ascii=False).lower()
        for a in actions
    )
    
    print(f"✓ 收到 {chunk_count} chunks，{len(full_response)} chars")
    print(f"✓ 解析出 {len(actions)} 个操作")
    print(f"✓ 包含流程图操作: {has_flowchart}")
    
    if has_flowchart:
        for a in actions:
            if "item" in a and "content_type" in a.get("item", {}):
                if a["item"]["content_type"] == "flowchart":
                    print("\n生成的流程图数据:")
                    print(json.dumps(a["item"]["flowchart_data"], ensure_ascii=False, indent=2))
    
    return {
        "chunks": chunk_count,
        "response_length": len(full_response),
        "actions_count": len(actions),
        "has_flowchart": has_flowchart
    }


def main():
    banner("content_convert Skill 流程图转换验证")
    
    # 验证 1: Skill 载入
    skill_results = verify_skill_loading()
    
    # 验证 2: 流程图转换功能
    conversion_results = verify_flowchart_conversion()
    
    # 验证 3: 共创模式 API
    api_results = verify_cocreation_api()
    
    # 汇总
    banner("验证汇总")
    
    all_passed = True
    
    # Skill 载入
    if skill_results["content_convert_found"] and skill_results["has_flowchart_tool"]:
        print("✓ Skill 载入: 通过")
    else:
        print("✗ Skill 载入: 失败")
        all_passed = False
    
    # 流程图转换
    conversion_passed = all(r["success"] for r in conversion_results)
    if conversion_passed:
        print("✓ 流程图转换: 通过")
    else:
        print("✗ 流程图转换: 失败")
        all_passed = False
    
    # API 调用
    if api_results["has_flowchart"]:
        print("✓ 共创模式 API: 通过")
    else:
        print("✗ 共创模式 API: 失败")
        all_passed = False
    
    print(f"\n{'='*70}")
    if all_passed:
        print("  ✅ 所有验证通过！content_convert Skill 流程图功能正常工作")
    else:
        print("  ❌ 部分验证失败，请检查日志")
    print(f"{'='*70}\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
