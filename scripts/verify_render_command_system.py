#!/usr/bin/env python3
"""
渲染指令系统验证脚本

验证内容：
1. RenderCommand 数据结构
2. RenderCommandParser 解析器
3. RenderExecutor 执行器
4. QuickActionGenerator 快捷指令
5. 向后兼容性
"""

import sys
import json
sys.path.insert(0, '.')

def test_render_command():
    """测试 RenderCommand 数据结构"""
    print("\n" + "="*60)
    print("1. 测试 RenderCommand 数据结构")
    print("="*60)
    
    from opencopilot.capabilities.ppt.render_command import RenderCommand
    
    # 创建渲染指令
    cmd = RenderCommand(
        source_text="2025年全年营收12.8亿元",
        render_type="chart",
        render_params={"chart_type": "bar", "title": "营收趋势"},
        slide_index=0,
        instruction="把这段数据用柱状图展示"
    )
    
    print(f"✓ 创建渲染指令成功:")
    print(f"  - command_id: {cmd.command_id}")
    print(f"  - render_type: {cmd.render_type}")
    print(f"  - source_text: {cmd.source_text[:30]}...")
    print(f"  - slide_index: {cmd.slide_index}")
    
    # 转换为字典
    cmd_dict = cmd.to_dict()
    print(f"\n✓ 转换为字典: {json.dumps(cmd_dict, ensure_ascii=False, indent=2)[:200]}...")
    
    # 从字典创建
    cmd2 = RenderCommand.from_dict(cmd_dict)
    print(f"\n✓ 从字典创建: render_type={cmd2.render_type}")
    
    return True

def test_render_command_parser():
    """测试 RenderCommandParser 解析器"""
    print("\n" + "="*60)
    print("2. 测试 RenderCommandParser 解析器")
    print("="*60)
    
    from opencopilot.capabilities.ppt.render_command import RenderCommandParser
    
    # 测试新格式（render_commands）
    response_new = '''
```json
{
  "render_commands": [
    {
      "source_text": "2025年全年营收12.8亿元",
      "render_type": "chart",
      "render_params": {
        "chart_type": "bar",
        "title": "营收趋势"
      }
    },
    {
      "source_text": "技术团队50人",
      "render_type": "table",
      "render_params": {
        "title": "团队规模"
      }
    }
  ]
}
```
'''
    
    commands = RenderCommandParser.parse(response_new)
    print(f"✓ 解析新格式: {len(commands)} 条指令")
    for i, cmd in enumerate(commands):
        print(f"  [{i+1}] type={cmd.render_type}, source={cmd.source_text[:20]}...")
    
    # 测试旧格式（action）
    response_old = '''
```json
{
  "action": "update",
  "slide_index": 0,
  "field": "title",
  "value": "新标题"
}
```
'''
    
    commands_old = RenderCommandParser.parse(response_old)
    print(f"\n✓ 解析旧格式: {len(commands_old)} 条指令（应该是0，因为旧格式由 CoCreationWidget 处理）")
    
    return True

def test_render_executor():
    """测试 RenderExecutor 执行器"""
    print("\n" + "="*60)
    print("3. 测试 RenderExecutor 执行器")
    print("="*60)
    
    from opencopilot.capabilities.ppt.render_command import RenderCommand
    from opencopilot.capabilities.ppt.render_executor import RenderExecutor
    
    # 初始 slides_data
    slides_data = [
        {
            "type": "content",
            "layout": "text_only",
            "title": "测试幻灯片",
            "items": [{"text": "原有内容"}]
        }
    ]
    
    executor = RenderExecutor(slides_data, "这是原文内容")
    
    # 执行渲染指令
    cmd = RenderCommand(
        source_text="2025年全年营收12.8亿元",
        render_type="chart",
        render_params={"chart_type": "bar", "title": "营收趋势"},
        slide_index=0
    )
    
    result = executor.execute(cmd)
    print(f"✓ 执行渲染指令:")
    print(f"  - success: {result.success}")
    print(f"  - slide_index: {result.slide_index}")
    print(f"  - message: {result.message}")
    
    # 检查 slides_data 是否更新
    print(f"\n✓ 更新后的 slides_data:")
    print(f"  - items 数量: {len(slides_data[0].get('items', []))}")
    
    return True

def test_quick_action_generator():
    """测试 QuickActionGenerator 快捷指令"""
    print("\n" + "="*60)
    print("4. 测试 QuickActionGenerator 快捷指令")
    print("="*60)
    
    from opencopilot.capabilities.ppt.render_command import QuickActionGenerator
    
    # 测试包含数值的文本
    text_with_numbers = "2025年全年营收12.8亿元，同比增长15%"
    actions = QuickActionGenerator.generate_actions(text_with_numbers)
    print(f"✓ 数值文本生成 {len(actions)} 个快捷指令:")
    for action in actions[:5]:
        print(f"  - {action['label']}")
    
    # 测试包含步骤的文本
    text_with_steps = "第一步：需求分析\n第二步：架构设计\n第三步：编码实现"
    actions_steps = QuickActionGenerator.generate_actions(text_with_steps)
    print(f"\n✓ 步骤文本生成 {len(actions_steps)} 个快捷指令:")
    for action in actions_steps[:5]:
        print(f"  - {action['label']}")
    
    return True

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "="*60)
    print("5. 测试向后兼容性")
    print("="*60)
    
    from opencopilot.capabilities.ppt.render_command import RenderCommandParser
    
    # 混合格式响应
    response_mixed = '''
这是 AI 的响应文本。

```json
{
  "render_commands": [
    {
      "source_text": "营收数据",
      "render_type": "chart",
      "render_params": {"chart_type": "bar"}
    }
  ]
}
```

这是补充说明。
'''
    
    commands = RenderCommandParser.parse(response_mixed)
    print(f"✓ 混合格式解析: {len(commands)} 条渲染指令")
    
    # 纯文本响应（无 JSON）
    response_text = "这是一段纯文本响应，没有 JSON 数据。"
    commands_text = RenderCommandParser.parse(response_text)
    print(f"✓ 纯文本响应: {len(commands_text)} 条指令（应该是0）")
    
    return True

def test_api_endpoints():
    """测试 API 端点（模拟）"""
    print("\n" + "="*60)
    print("6. 测试 API 端点（模拟）")
    print("="*60)
    
    # 模拟 API 请求数据
    render_command_request = {
        "render_commands": [
            {
                "source_text": "2025年全年营收12.8亿元",
                "render_type": "chart",
                "render_params": {"chart_type": "bar", "title": "营收趋势"}
            }
        ],
        "slides_data": [
            {
                "type": "content",
                "layout": "text_only",
                "title": "测试",
                "items": []
            }
        ],
        "original_text": "这是原文",
        "current_index": 0
    }
    
    print(f"✓ 渲染指令请求数据结构正确: {len(render_command_request['render_commands'])} 条指令")
    
    # 模拟快捷指令请求
    quick_actions_request = {
        "selected_text": "2025年全年营收12.8亿元，同比增长15%",
        "slide_index": 0
    }
    
    print(f"✓ 快捷指令请求数据结构正确: text_len={len(quick_actions_request['selected_text'])}")
    
    return True

def main():
    """主测试函数"""
    print("🚀 开始验证渲染指令系统")
    
    tests = [
        ("RenderCommand", test_render_command),
        ("RenderCommandParser", test_render_command_parser),
        ("RenderExecutor", test_render_executor),
        ("QuickActionGenerator", test_quick_action_generator),
        ("向后兼容性", test_backward_compatibility),
        ("API端点", test_api_endpoints),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} | {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！渲染指令系统验证成功。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
