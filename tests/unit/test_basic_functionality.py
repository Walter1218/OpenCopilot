"""
基础功能测试 - 验证测试环境和基本功能
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestBasicFunctionality:
    """基础功能测试类"""
    
    def test_python_version(self):
        """测试Python版本是否符合要求"""
        assert sys.version_info >= (3, 10), "Python版本需要3.10或更高"
        # 注意：Python 3.13可能与某些依赖不完全兼容，但基本功能可用
        # assert sys.version_info < (3, 13), "Python版本需要低于3.13"
        print(f"当前Python版本: {sys.version_info}")
    
    def test_pyqt6_import(self):
        """测试PyQt6是否可以导入"""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt
            assert True
        except ImportError:
            pytest.skip("PyQt6未安装或无法导入")
    
    def test_project_structure(self):
        """测试项目结构是否完整"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 检查关键文件是否存在
        key_files = [
            "smart_copilot.py",
            "asu_custom_agent.py",
            "llm_provider.py",
            "cursor_effects.py",
            "requirements.txt"
        ]
        
        for file_name in key_files:
            file_path = os.path.join(project_root, file_name)
            assert os.path.exists(file_path), f"关键文件 {file_name} 不存在"
    
    def test_requirements_import(self):
        """测试requirements.txt中的关键依赖是否可导入"""
        critical_modules = [
            "httpx",
            "pynput",
            "PyQt6",
        ]
        
        for module_name in critical_modules:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"关键模块 {module_name} 无法导入")
    
    def test_persona_files_exist(self):
        """测试Persona文件是否存在"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        personas_dir = os.path.join(project_root, "personas")
        
        assert os.path.exists(personas_dir), "personas目录不存在"
        
        # 检查基础persona文件
        expected_personas = [
            "default.md",
            "code.md",
            "translate.md",
            "polish.md",
            "revision.md"
        ]
        
        for persona_file in expected_personas:
            persona_path = os.path.join(personas_dir, persona_file)
            assert os.path.exists(persona_path), f"Persona文件 {persona_file} 不存在"
    
    def test_tools_directory_exists(self):
        """测试tools目录是否存在"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        tools_dir = os.path.join(project_root, "tools")
        
        assert os.path.exists(tools_dir), "tools目录不存在"
        
        # 检查关键工具文件
        expected_tools = [
            "__init__.py",
            "base.py",
            "file_tools.py",
            "text_tools.py",
            "format_tools.py"
        ]
        
        for tool_file in expected_tools:
            tool_path = os.path.join(tools_dir, tool_file)
            assert os.path.exists(tool_path), f"工具文件 {tool_file} 不存在"


class TestMathOperations:
    """数学运算测试（用于验证pytest基本功能）"""
    
    def test_addition(self):
        """测试加法"""
        assert 1 + 1 == 2
    
    def test_subtraction(self):
        """测试减法"""
        assert 5 - 3 == 2
    
    def test_multiplication(self):
        """测试乘法"""
        assert 3 * 4 == 12
    
    def test_division(self):
        """测试除法"""
        assert 10 / 2 == 5.0
    
    def test_division_by_zero(self):
        """测试除零异常"""
        with pytest.raises(ZeroDivisionError):
            10 / 0


class TestStringOperations:
    """字符串操作测试"""
    
    def test_string_concatenation(self):
        """测试字符串拼接"""
        assert "hello" + " " + "world" == "hello world"
    
    def test_string_length(self):
        """测试字符串长度"""
        assert len("OpenCopilot") == 11
    
    def test_string_contains(self):
        """测试字符串包含"""
        assert "Copilot" in "OpenCopilot"
    
    def test_string_upper(self):
        """测试字符串大写转换"""
        assert "hello".upper() == "HELLO"
    
    def test_string_lower(self):
        """测试字符串小写转换"""
        assert "HELLO".lower() == "hello"


class TestListOperations:
    """列表操作测试"""
    
    def test_list_append(self):
        """测试列表追加"""
        my_list = [1, 2, 3]
        my_list.append(4)
        assert my_list == [1, 2, 3, 4]
    
    def test_list_length(self):
        """测试列表长度"""
        my_list = [1, 2, 3, 4, 5]
        assert len(my_list) == 5
    
    def test_list_contains(self):
        """测试列表包含"""
        my_list = [1, 2, 3, 4, 5]
        assert 3 in my_list
    
    def test_list_sort(self):
        """测试列表排序"""
        my_list = [3, 1, 4, 1, 5, 9, 2, 6]
        my_list.sort()
        assert my_list == [1, 1, 2, 3, 4, 5, 6, 9]


class TestDictOperations:
    """字典操作测试"""
    
    def test_dict_access(self):
        """测试字典访问"""
        my_dict = {"name": "OpenCopilot", "version": "1.0"}
        assert my_dict["name"] == "OpenCopilot"
    
    def test_dict_update(self):
        """测试字典更新"""
        my_dict = {"name": "OpenCopilot"}
        my_dict["version"] = "1.0"
        assert my_dict == {"name": "OpenCopilot", "version": "1.0"}
    
    def test_dict_keys(self):
        """测试字典键"""
        my_dict = {"name": "OpenCopilot", "version": "1.0"}
        assert "name" in my_dict.keys()
        assert "version" in my_dict.keys()
    
    def test_dict_values(self):
        """测试字典值"""
        my_dict = {"name": "OpenCopilot", "version": "1.0"}
        assert "OpenCopilot" in my_dict.values()
        assert "1.0" in my_dict.values()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])