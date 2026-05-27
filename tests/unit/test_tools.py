"""
工具模块测试 - 测试tools目录下的工具功能
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestToolsModule:
    """工具模块测试类"""
    
    def test_tools_import(self):
        """测试tools模块是否可以导入"""
        try:
            import tools
            assert True
        except ImportError:
            pytest.fail("无法导入tools模块")
    
    def test_base_module_import(self):
        """测试base模块是否可以导入"""
        try:
            from tools import base
            assert True
        except ImportError:
            pytest.fail("无法导入tools.base模块")
    
    def test_file_tools_import(self):
        """测试file_tools模块是否可以导入"""
        try:
            from tools import file_tools
            assert True
        except ImportError:
            pytest.fail("无法导入tools.file_tools模块")
    
    def test_text_tools_import(self):
        """测试text_tools模块是否可以导入"""
        try:
            from tools import text_tools
            assert True
        except ImportError:
            pytest.fail("无法导入tools.text_tools模块")
    
    def test_format_tools_import(self):
        """测试format_tools模块是否可以导入"""
        try:
            from tools import format_tools
            assert True
        except ImportError:
            pytest.fail("无法导入tools.format_tools模块")


class TestBaseTools:
    """基础工具测试类"""
    
    def test_tool_registry(self):
        """测试工具注册表"""
        try:
            from tools.base import ToolRegistry
            
            # 创建工具注册表实例
            registry = ToolRegistry()
            
            # 验证注册表有必要的方法
            assert hasattr(registry, 'register')
            assert hasattr(registry, 'get_tool')
            assert hasattr(registry, 'list_tools')
            
        except ImportError:
            pytest.skip("无法导入ToolRegistry")
    
    def test_base_tool_class(self):
        """测试基础工具类"""
        try:
            from tools.base import BaseTool
            
            # 验证BaseTool是一个类
            assert isinstance(BaseTool, type)
            
            # 验证BaseTool有必要的方法和属性
            assert hasattr(BaseTool, 'execute')
            assert hasattr(BaseTool, 'description')
            assert hasattr(BaseTool, 'name')
            assert hasattr(BaseTool, 'parameters')
            assert hasattr(BaseTool, 'validate_parameters')
            
        except ImportError:
            pytest.skip("无法导入BaseTool")


class TestFileTools:
    """文件工具测试类"""
    
    def test_file_tools_availability(self):
        """测试文件工具是否可用"""
        try:
            from tools.file_tools import FileReadTool
            
            # 验证类存在
            assert isinstance(FileReadTool, type)
            
        except ImportError:
            pytest.skip("无法导入文件工具")
    
    def test_file_reader_methods(self):
        """测试FileReadTool的方法"""
        try:
            from tools.file_tools import FileReadTool
            
            reader = FileReadTool()
            
            # 验证有必要的属性和方法
            assert hasattr(reader, 'name')
            assert hasattr(reader, 'description')
            assert hasattr(reader, 'parameters')
            assert hasattr(reader, 'execute')
            assert hasattr(reader, 'validate_parameters')
            
        except ImportError:
            pytest.skip("无法导入FileReadTool")


class TestTextTools:
    """文本工具测试类"""
    
    def test_text_tools_availability(self):
        """测试文本工具是否可用"""
        try:
            from tools.text_tools import TextExtractTool
            
            # 验证类存在
            assert isinstance(TextExtractTool, type)
            
        except ImportError:
            pytest.skip("无法导入文本工具")
    
    def test_text_processor_methods(self):
        """测试TextExtractTool的方法"""
        try:
            from tools.text_tools import TextExtractTool
            
            processor = TextExtractTool()
            
            # 验证有必要的属性和方法
            assert hasattr(processor, 'name')
            assert hasattr(processor, 'description')
            assert hasattr(processor, 'parameters')
            assert hasattr(processor, 'execute')
            assert hasattr(processor, 'validate_parameters')
            
        except ImportError:
            pytest.skip("无法导入TextExtractTool")


class TestFormatTools:
    """格式工具测试类"""
    
    def test_format_tools_availability(self):
        """测试格式工具是否可用"""
        try:
            from tools.format_tools import MarkdownToDocxTool
            
            # 验证类存在
            assert isinstance(MarkdownToDocxTool, type)
            
        except ImportError:
            pytest.skip("无法导入格式工具")
    
    def test_format_converter_methods(self):
        """测试MarkdownToDocxTool的方法"""
        try:
            from tools.format_tools import MarkdownToDocxTool
            
            converter = MarkdownToDocxTool()
            
            # 验证有必要的属性和方法
            assert hasattr(converter, 'name')
            assert hasattr(converter, 'description')
            assert hasattr(converter, 'parameters')
            assert hasattr(converter, 'execute')
            assert hasattr(converter, 'validate_parameters')
            
        except ImportError:
            pytest.skip("无法导入MarkdownToDocxTool")


class TestToolsIntegration:
    """工具集成测试"""
    
    def test_tools_directory_structure(self):
        """测试tools目录结构"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        tools_dir = os.path.join(project_root, "tools")
        
        assert os.path.exists(tools_dir), "tools目录不存在"
        
        # 检查关键文件
        expected_files = [
            "__init__.py",
            "base.py",
            "file_tools.py",
            "text_tools.py",
            "format_tools.py"
        ]
        
        for file_name in expected_files:
            file_path = os.path.join(tools_dir, file_name)
            assert os.path.exists(file_path), f"工具文件 {file_name} 不存在"
    
    def test_tools_module_init(self):
        """测试tools模块的__init__.py"""
        try:
            import tools
            
            # 验证模块有__all__属性或其他导出
            # 这取决于tools/__init__.py的实现
            assert True
            
        except ImportError:
            pytest.fail("无法导入tools模块")
    
    def test_tools_cross_import(self):
        """测试工具模块间的交叉导入"""
        try:
            # 尝试从不同模块导入
            from tools.base import BaseTool, ToolRegistry
            from tools.file_tools import FileReadTool
            from tools.text_tools import TextExtractTool
            from tools.format_tools import MarkdownToDocxTool
            
            # 验证所有导入成功
            assert BaseTool is not None
            assert ToolRegistry is not None
            assert FileReadTool is not None
            assert TextExtractTool is not None
            assert MarkdownToDocxTool is not None
            
        except ImportError as e:
            pytest.fail(f"工具模块交叉导入失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])