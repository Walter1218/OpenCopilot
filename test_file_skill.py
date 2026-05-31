#!/usr/bin/env python3
"""
FileSkill 测试

测试 FileSkill 的各项功能：
1. 初始化测试
2. can_handle 测试
3. 文件读取测试
4. 文件写入测试
5. 格式转换测试
6. 目录列表测试
7. 文件删除测试
"""

import asyncio
import sys
import os
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.file_skill import FileSkill
from skill_architecture.models import SkillContext, SkillStatus


def print_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if message:
        print(f"      {message}")


async def test_initialization():
    """测试初始化"""
    print_header("FileSkill 初始化测试")
    
    try:
        skill = FileSkill()
        
        # 验证元数据
        metadata = skill.metadata
        assert metadata.name == "file_skill"
        assert metadata.version == "1.0.0"
        assert "file" in metadata.tags
        assert "file_read" in metadata.intents
        
        print_result("初始化测试", True, "元数据验证通过")
        return True
    except Exception as e:
        print_result("初始化测试", False, str(e))
        return False


async def test_can_handle():
    """测试 can_handle 方法"""
    print_header("FileSkill can_handle 测试")
    
    try:
        skill = FileSkill()
        
        # 测试意图匹配
        context1 = SkillContext(intent="file_read", input_data={})
        confidence1 = await skill.can_handle(context1)
        assert confidence1 > 0.5
        print_result("意图匹配测试", True, f"置信度: {confidence1}")
        
        # 测试动作匹配
        context2 = SkillContext(intent="", input_data={"action": "read"})
        confidence2 = await skill.can_handle(context2)
        assert confidence2 > 0.5
        print_result("动作匹配测试", True, f"置信度: {confidence2}")
        
        # 测试内容匹配
        context3 = SkillContext(intent="", input_data={"content": "请帮我读取这个文件"})
        confidence3 = await skill.can_handle(context3)
        assert confidence3 > 0.5
        print_result("内容匹配测试", True, f"置信度: {confidence3}")
        
        # 测试不匹配
        context4 = SkillContext(intent="unknown", input_data={"action": "unknown"})
        confidence4 = await skill.can_handle(context4)
        assert confidence4 < 0.5
        print_result("不匹配测试", True, f"置信度: {confidence4}")
        
        return True
    except Exception as e:
        print_result("can_handle 测试", False, str(e))
        return False


async def test_read_file():
    """测试文件读取"""
    print_header("FileSkill 文件读取测试")
    
    try:
        skill = FileSkill()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("测试内容")
            temp_file = f.name
        
        try:
            # 测试缺少文件路径
            context1 = SkillContext(
                intent="file_read",
                input_data={"action": "read"}
            )
            result1 = await skill.execute(context1)
            assert not result1.success
            assert "file_path is required" in result1.error
            print_result("缺少文件路径测试", True, "正确返回错误")
            
            # 测试正常读取
            context2 = SkillContext(
                intent="file_read",
                input_data={
                    "action": "read",
                    "file_path": temp_file,
                    "format": "text"
                }
            )
            result2 = await skill.execute(context2)
            
            if result2.success:
                print_result("文件读取测试", True, 
                            f"读取成功，内容长度: {len(result2.data.get('content', ''))}")
            else:
                print_result("文件读取测试", False, result2.error)
            
            return result2.success
        finally:
            # 清理临时文件
            os.unlink(temp_file)
    except Exception as e:
        print_result("文件读取测试", False, str(e))
        return False


async def test_write_file():
    """测试文件写入"""
    print_header("FileSkill 文件写入测试")
    
    try:
        skill = FileSkill()
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test.txt")
            
            # 测试缺少内容
            context1 = SkillContext(
                intent="file_write",
                input_data={
                    "action": "write",
                    "file_path": temp_file
                }
            )
            result1 = await skill.execute(context1)
            assert not result1.success
            assert "content is required" in result1.error
            print_result("缺少内容测试", True, "正确返回错误")
            
            # 测试缺少文件路径
            context2 = SkillContext(
                intent="file_write",
                input_data={
                    "action": "write",
                    "content": "测试内容"
                }
            )
            result2 = await skill.execute(context2)
            assert not result2.success
            assert "file_path is required" in result2.error
            print_result("缺少文件路径测试", True, "正确返回错误")
            
            # 测试正常写入
            context3 = SkillContext(
                intent="file_write",
                input_data={
                    "action": "write",
                    "content": "测试内容",
                    "file_path": temp_file,
                    "format": "text"
                }
            )
            result3 = await skill.execute(context3)
            
            if result3.success:
                # 验证文件是否写入成功
                if os.path.exists(temp_file):
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    assert content == "测试内容"
                    print_result("文件写入测试", True, "写入成功，内容验证通过")
                else:
                    print_result("文件写入测试", False, "文件未创建")
            else:
                print_result("文件写入测试", False, result3.error)
            
            return result3.success
    except Exception as e:
        print_result("文件写入测试", False, str(e))
        return False


async def test_convert_file():
    """测试文件格式转换"""
    print_header("FileSkill 文件格式转换测试")
    
    try:
        skill = FileSkill()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("测试内容")
            temp_file = f.name
        
        try:
            # 测试缺少输入路径
            context1 = SkillContext(
                intent="file_convert",
                input_data={
                    "action": "convert",
                    "output_format": "md"
                }
            )
            result1 = await skill.execute(context1)
            assert not result1.success
            assert "input_path is required" in result1.error
            print_result("缺少输入路径测试", True, "正确返回错误")
            
            # 测试缺少输出格式
            context2 = SkillContext(
                intent="file_convert",
                input_data={
                    "action": "convert",
                    "input_path": temp_file
                }
            )
            result2 = await skill.execute(context2)
            assert not result2.success
            assert "output_format is required" in result2.error
            print_result("缺少输出格式测试", True, "正确返回错误")
            
            # 测试正常转换
            output_file = temp_file.replace('.txt', '.md')
            context3 = SkillContext(
                intent="file_convert",
                input_data={
                    "action": "convert",
                    "input_path": temp_file,
                    "output_format": "md",
                    "output_path": output_file
                }
            )
            result3 = await skill.execute(context3)
            
            if result3.success:
                print_result("文件格式转换测试", True, "转换成功")
            else:
                print_result("文件格式转换测试", False, result3.error)
            
            return result3.success
        finally:
            # 清理临时文件
            os.unlink(temp_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    except Exception as e:
        print_result("文件格式转换测试", False, str(e))
        return False


async def test_list_directory():
    """测试目录列表"""
    print_header("FileSkill 目录列表测试")
    
    try:
        skill = FileSkill()
        
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一些文件
            for i in range(3):
                with open(os.path.join(temp_dir, f"file{i}.txt"), 'w') as f:
                    f.write(f"内容{i}")
            
            # 测试目录不存在
            context1 = SkillContext(
                intent="file_list",
                input_data={
                    "action": "list",
                    "file_path": "/nonexistent/path"
                }
            )
            result1 = await skill.execute(context1)
            assert not result1.success
            assert "Directory does not exist" in result1.error
            print_result("目录不存在测试", True, "正确返回错误")
            
            # 测试正常目录列表
            context2 = SkillContext(
                intent="file_list",
                input_data={
                    "action": "list",
                    "file_path": temp_dir
                }
            )
            result2 = await skill.execute(context2)
            
            if result2.success:
                items = result2.data.get("items", [])
                print_result("目录列表测试", True, 
                            f"列出 {len(items)} 个项目")
            else:
                print_result("目录列表测试", False, result2.error)
            
            return result2.success
    except Exception as e:
        print_result("目录列表测试", False, str(e))
        return False


async def test_delete_file():
    """测试文件删除"""
    print_header("FileSkill 文件删除测试")
    
    try:
        skill = FileSkill()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("测试内容")
            temp_file = f.name
        
        try:
            # 测试文件不存在
            context1 = SkillContext(
                intent="file_delete",
                input_data={
                    "action": "delete",
                    "file_path": "/nonexistent/file.txt"
                }
            )
            result1 = await skill.execute(context1)
            assert not result1.success
            assert "File does not exist" in result1.error
            print_result("文件不存在测试", True, "正确返回错误")
            
            # 测试正常删除
            context2 = SkillContext(
                intent="file_delete",
                input_data={
                    "action": "delete",
                    "file_path": temp_file
                }
            )
            result2 = await skill.execute(context2)
            
            if result2.success:
                # 验证文件是否被删除
                if not os.path.exists(temp_file):
                    print_result("文件删除测试", True, "删除成功")
                else:
                    print_result("文件删除测试", False, "文件未删除")
            else:
                print_result("文件删除测试", False, result2.error)
            
            return result2.success
        except Exception as e:
            # 如果测试失败，确保清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            raise
    except Exception as e:
        print_result("文件删除测试", False, str(e))
        return False


async def main():
    """主测试函数"""
    print_header("FileSkill 全面测试")
    
    # 运行所有测试
    tests = [
        test_initialization,
        test_can_handle,
        test_read_file,
        test_write_file,
        test_convert_file,
        test_list_directory,
        test_delete_file
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {test.__name__} - {str(e)}")
            results.append(False)
    
    # 打印总结
    print_header("测试总结")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())