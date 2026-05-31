"""
FormatSkill 测试
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture import FormatSkill, SkillContext


def print_result(test_name: str, success: bool, details: str = ""):
    """打印测试结果"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} | {test_name}")
    if details:
        print(f"   详情: {details}")


async def test_format_skill():
    """测试 FormatSkill"""
    print("\n" + "=" * 60)
    print("FormatSkill 测试")
    print("=" * 60)
    
    skill = FormatSkill()
    
    # 1. 测试初始化
    print("\n--- 初始化测试 ---")
    assert skill.metadata.name == "format_skill"
    print_result("初始化测试", True, f"技能名称: {skill.metadata.name}")
    
    # 2. 测试 can_handle
    print("\n--- can_handle 测试 ---")
    
    # 测试意图匹配
    context1 = SkillContext(intent="format_convert", input_data={})
    confidence1 = await skill.can_handle(context1)
    assert confidence1 > 0.5
    print_result("意图匹配测试", True, f"置信度: {confidence1}")
    
    # 测试动作匹配
    context2 = SkillContext(intent="", input_data={"action": "md_to_docx"})
    confidence2 = await skill.can_handle(context2)
    assert confidence2 > 0.5
    print_result("动作匹配测试", True, f"置信度: {confidence2}")
    
    # 测试内容匹配
    context3 = SkillContext(intent="", input_data={"content": "请帮我转换这个Markdown文件"})
    confidence3 = await skill.can_handle(context3)
    assert confidence3 > 0.5
    print_result("内容匹配测试", True, f"置信度: {confidence3}")
    
    # 测试不匹配
    context4 = SkillContext(intent="unknown", input_data={"action": "unknown"})
    confidence4 = await skill.can_handle(context4)
    assert confidence4 < 0.5
    print_result("不匹配测试", True, f"置信度: {confidence4}")
    
    # 3. 测试 Markdown 转 Word
    print("\n--- Markdown 转 Word 测试 ---")
    md_content = """# 测试文档

## 第一章

这是一个测试段落。

- 列表项1
- 列表项2

## 第二章

1. 有序列表1
2. 有序列表2
"""
    
    context_md_docx = SkillContext(
        intent="md_to_docx",
        input_data={
            "action": "md_to_docx",
            "content": md_content
        }
    )
    result_md_docx = await skill.execute(context_md_docx)
    assert result_md_docx.success
    assert result_md_docx.data["format"] == "docx"
    print_result("Markdown 转 Word 测试", True, 
                 f"段落数: {result_md_docx.data.get('paragraphs', 'N/A')}")
    
    # 4. 测试 Markdown 转 PPT
    print("\n--- Markdown 转 PPT 测试 ---")
    context_md_pptx = SkillContext(
        intent="md_to_pptx",
        input_data={
            "action": "md_to_pptx",
            "content": md_content
        }
    )
    result_md_pptx = await skill.execute(context_md_pptx)
    assert result_md_pptx.success
    assert result_md_pptx.data["format"] == "pptx"
    print_result("Markdown 转 PPT 测试", True, 
                 f"幻灯片数: {result_md_pptx.data.get('slides', 'N/A')}")
    
    # 5. 测试文本转表格
    print("\n--- 文本转表格测试 ---")
    text_content = """姓名,年龄,城市
张三,25,北京
李四,30,上海
王五,28,广州
"""
    
    context_text_table = SkillContext(
        intent="text_to_table",
        input_data={
            "action": "text_to_table",
            "content": text_content,
            "format": "markdown"
        }
    )
    result_text_table = await skill.execute(context_text_table)
    assert result_text_table.success
    assert result_text_table.data["format"] == "markdown"
    print_result("文本转表格测试", True, 
                 f"行数: {result_text_table.data.get('rows', 'N/A')}, "
                 f"列数: {result_text_table.data.get('columns', 'N/A')}")
    
    # 6. 测试表格转 HTML
    print("\n--- 表格转 HTML 测试 ---")
    context_text_html = SkillContext(
        intent="text_to_table",
        input_data={
            "action": "text_to_table",
            "content": text_content,
            "format": "html"
        }
    )
    result_text_html = await skill.execute(context_text_html)
    assert result_text_html.success
    assert result_text_html.data["format"] == "html"
    print_result("表格转 HTML 测试", True, 
                 f"行数: {result_text_html.data.get('rows', 'N/A')}")
    
    # 7. 测试表格转 CSV
    print("\n--- 表格转 CSV 测试 ---")
    context_text_csv = SkillContext(
        intent="text_to_table",
        input_data={
            "action": "text_to_table",
            "content": text_content,
            "format": "csv"
        }
    )
    result_text_csv = await skill.execute(context_text_csv)
    assert result_text_csv.success
    assert result_text_csv.data["format"] == "csv"
    print_result("表格转 CSV 测试", True, 
                 f"行数: {result_text_csv.data.get('rows', 'N/A')}")
    
    # 8. 测试文件写入
    print("\n--- 文件写入测试 ---")
    temp_docx = "/tmp/test_format_output.docx"
    context_file = SkillContext(
        intent="md_to_docx",
        input_data={
            "action": "md_to_docx",
            "content": md_content,
            "output_path": temp_docx
        }
    )
    result_file = await skill.execute(context_file)
    assert result_file.success
    assert os.path.exists(temp_docx)
    print_result("文件写入测试", True, f"输出路径: {temp_docx}")
    
    # 清理临时文件
    if os.path.exists(temp_docx):
        os.remove(temp_docx)
    
    # 9. 测试错误处理
    print("\n--- 错误处理测试 ---")
    context_empty = SkillContext(
        intent="md_to_docx",
        input_data={
            "action": "md_to_docx",
            "content": ""
        }
    )
    result_empty = await skill.execute(context_empty)
    assert not result_empty.success
    assert "缺少 Markdown 内容" in result_empty.error
    print_result("错误处理测试", True, "空内容正确返回错误")
    
    # 测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("\n支持的功能:")
    print("  1. Markdown 转 Word (.docx)")
    print("  2. Markdown 转 PPT (.pptx)")
    print("  3. 文本转表格 (Markdown/HTML/CSV)")
    print("  4. 文件写入功能")
    print("  5. 错误处理机制")


if __name__ == "__main__":
    asyncio.run(test_format_skill())
