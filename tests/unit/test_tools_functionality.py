"""
工具模块功能测试 - 测试工具的实际功能
"""

import pytest
import sys
import os
import asyncio
import tempfile

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestFileReadToolFunctionality:
    """FileReadTool功能测试"""
    
    @pytest.fixture
    def sample_text_file(self):
        """创建测试用的文本文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("这是一个测试文本文件。\n")
            f.write("包含多行内容。\n")
            f.write("包含中文和English混合。\n")
            f.write("包含特殊字符：!@#$%^&*()\n")
            f.write("包含数字：1234567890\n")
            f.write("\n")
            f.write("段落分隔。\n")
            f.write("\n")
            f.write("第二段内容。\n")
            temp_path = f.name
        
        yield temp_path
        
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_read_text_file(self, sample_text_file):
        """测试读取文本文件"""
        from tools.file_tools import FileReadTool
        
        tool = FileReadTool()
        result = await tool.execute(file_path=sample_text_file, format="text")
        
        # 验证返回结果
        assert "error" not in result
        assert result["type"] == "text"
        assert "content" in result
        assert result["file_path"] == sample_text_file
        
        # 验证内容
        content = result["content"]
        assert "这是一个测试文本文件" in content
        assert "包含多行内容" in content
        assert "包含中文和English混合" in content
        assert "包含特殊字符：!@#$%^&*()" in content
        assert "包含数字：1234567890" in content
        assert "段落分隔" in content
        assert "第二段内容" in content
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """测试读取不存在的文件"""
        from tools.file_tools import FileReadTool
        
        tool = FileReadTool()
        result = await tool.execute(file_path="/path/to/nonexistent/file.txt", format="text")
        
        # 验证返回错误
        assert "error" in result
        assert "文件不存在" in result["error"]
    
    @pytest.mark.asyncio
    async def test_read_file_missing_path(self):
        """测试缺少文件路径参数"""
        from tools.file_tools import FileReadTool
        
        tool = FileReadTool()
        result = await tool.execute(format="text")
        
        # 验证返回错误
        assert "error" in result
        assert "file_path is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_read_file_with_user_path(self):
        """测试读取用户目录下的文件"""
        from tools.file_tools import FileReadTool
        
        # 创建临时文件在用户目录
        home_dir = os.path.expanduser("~")
        temp_file = os.path.join(home_dir, "test_file_for_tools.txt")
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write("测试用户目录文件读取")
            
            tool = FileReadTool()
            result = await tool.execute(file_path="~/test_file_for_tools.txt", format="text")
            
            # 验证返回结果
            assert "error" not in result
            assert result["type"] == "text"
            assert "测试用户目录文件读取" in result["content"]
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_read_file_parameters(self):
        """测试FileReadTool参数定义"""
        from tools.file_tools import FileReadTool
        
        tool = FileReadTool()
        
        # 验证工具属性
        assert tool.name == "file_read"
        assert "文件" in tool.description or "读取" in tool.description
        
        # 验证参数定义
        parameters = tool.parameters
        assert "file_path" in parameters
        assert "format" in parameters
        
        # 验证file_path参数
        file_path_param = parameters["file_path"]
        assert file_path_param["type"] == "string"
        assert file_path_param["required"] is True
        
        # 验证format参数
        format_param = parameters["format"]
        assert format_param["type"] == "string"
        assert "enum" in format_param
        assert "text" in format_param["enum"]
        assert "docx" in format_param["enum"]
        assert "pptx" in format_param["enum"]
        assert "pdf" in format_param["enum"]


class TestTextExtractToolFunctionality:
    """TextExtractTool功能测试"""
    
    @pytest.fixture
    def sample_markdown_content(self):
        """示例Markdown内容"""
        return """# 测试文档

## 第一章

这是一个测试文档。

### 1.1 节

- 列表项1
- 列表项2
- 列表项3

### 1.2 节

1. 有序列表1
2. 有序列表2
3. 有序列表3

## 第二章

这是一个表格：

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |
| 数据4 | 数据5 | 数据6 |

这是一个代码块：

```python
def hello():
    print("Hello, World!")
```
"""
    
    @pytest.mark.asyncio
    async def test_extract_all_text(self, sample_markdown_content):
        """测试提取全部文本"""
        from tools.text_tools import TextExtractTool
        
        tool = TextExtractTool()
        result = await tool.execute(content=sample_markdown_content, extract_type="all")
        
        # 验证返回结果
        assert "error" not in result
        assert result["type"] == "all"
        assert result["content"] == sample_markdown_content
    
    @pytest.mark.asyncio
    async def test_extract_headings(self, sample_markdown_content):
        """测试提取标题"""
        from tools.text_tools import TextExtractTool
        
        tool = TextExtractTool()
        result = await tool.execute(content=sample_markdown_content, extract_type="headings")
        
        # 验证返回结果
        assert "error" not in result
        assert result["type"] == "headings"
        assert "headings" in result
        assert "count" in result
        
        # 验证标题提取
        headings = result["headings"]
        assert len(headings) == 5  # # 测试文档, ## 第一章, ### 1.1 节, ### 1.2 节, ## 第二章
        
        # 验证标题级别
        heading_texts = [h["text"] for h in headings]
        assert "测试文档" in heading_texts
        assert "第一章" in heading_texts
        assert "1.1 节" in heading_texts
        assert "1.2 节" in heading_texts
        assert "第二章" in heading_texts
    
    @pytest.mark.asyncio
    async def test_extract_key_points(self, sample_markdown_content):
        """测试提取关键点"""
        from tools.text_tools import TextExtractTool
        
        tool = TextExtractTool()
        result = await tool.execute(content=sample_markdown_content, extract_type="key_points")
        
        # 验证返回结果
        assert "error" not in result
        assert result["type"] == "key_points"
        assert "key_points" in result
        assert "count" in result
        
        # 验证关键点提取
        key_points = result["key_points"]
        assert len(key_points) > 0
        assert len(key_points) <= 10  # 限制最多10个关键点
    
    @pytest.mark.asyncio
    async def test_extract_tables(self, sample_markdown_content):
        """测试提取表格"""
        from tools.text_tools import TextExtractTool
        
        tool = TextExtractTool()
        result = await tool.execute(content=sample_markdown_content, extract_type="tables")
        
        # 验证返回结果
        assert "error" not in result
        assert result["type"] == "tables"
        assert "tables" in result
        
        # 验证表格提取
        tables = result["tables"]
        assert len(tables) > 0
    
    @pytest.mark.asyncio
    async def test_extract_lists(self, sample_markdown_content):
        """测试提取列表"""
        from tools.text_tools import TextExtractTool
        
        tool = TextExtractTool()
        result = await tool.execute(content=sample_markdown_content, extract_type="lists")
        
        # 验证返回结果
        assert "error" not in result
        assert result["type"] == "lists"
        
        # 验证列表提取 - 返回包含有序和无序列表
        assert "ordered_items" in result or "unordered_items" in result
        total_items = result.get("ordered_count", 0) + result.get("unordered_count", 0)
        assert total_items > 0
    
    @pytest.mark.asyncio
    async def test_extract_missing_content(self):
        """测试缺少内容参数"""
        from tools.text_tools import TextExtractTool
        
        tool = TextExtractTool()
        result = await tool.execute(extract_type="all")
        
        # 验证返回错误
        assert "error" in result
        assert "content is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_extract_parameters(self):
        """测试TextExtractTool参数定义"""
        from tools.text_tools import TextExtractTool
        
        tool = TextExtractTool()
        
        # 验证工具属性
        assert tool.name == "text_extract"
        assert "文本" in tool.description or "提取" in tool.description
        
        # 验证参数定义
        parameters = tool.parameters
        assert "content" in parameters
        assert "extract_type" in parameters
        
        # 验证content参数
        content_param = parameters["content"]
        assert content_param["type"] == "string"
        assert content_param["required"] is True
        
        # 验证extract_type参数
        extract_type_param = parameters["extract_type"]
        assert extract_type_param["type"] == "string"
        assert "enum" in extract_type_param
        assert "all" in extract_type_param["enum"]
        assert "headings" in extract_type_param["enum"]
        assert "key_points" in extract_type_param["enum"]
        assert "summary" in extract_type_param["enum"]
        assert "tables" in extract_type_param["enum"]
        assert "lists" in extract_type_param["enum"]


class TestToolRegistryFunctionality:
    """ToolRegistry功能测试"""
    
    def test_register_and_get_tool(self):
        """测试注册和获取工具"""
        from tools.base import ToolRegistry, BaseTool
        
        # 创建一个简单的工具类
        class TestTool(BaseTool):
            @property
            def name(self):
                return "test_tool"
            
            @property
            def description(self):
                return "测试工具"
            
            async def execute(self, **kwargs):
                return {"result": "success"}
        
        registry = ToolRegistry()
        tool = TestTool()
        
        # 注册工具
        registry.register("test_tool", tool)
        
        # 获取工具
        retrieved_tool = registry.get_tool("test_tool")
        assert retrieved_tool is tool
        
        # 列出工具
        tools_list = registry.list_tools()
        assert "test_tool" in tools_list
    
    def test_unregister_tool(self):
        """测试注销工具"""
        from tools.base import ToolRegistry, BaseTool
        
        class TestTool(BaseTool):
            @property
            def name(self):
                return "test_tool"
            
            @property
            def description(self):
                return "测试工具"
            
            async def execute(self, **kwargs):
                return {"result": "success"}
        
        registry = ToolRegistry()
        tool = TestTool()
        
        # 注册工具
        registry.register("test_tool", tool)
        
        # 注销工具
        registry.unregister("test_tool")
        
        # 验证工具已注销
        retrieved_tool = registry.get_tool("test_tool")
        assert retrieved_tool is None
        
        tools_list = registry.list_tools()
        assert "test_tool" not in tools_list
    
    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具"""
        from tools.base import ToolRegistry
        
        registry = ToolRegistry()
        retrieved_tool = registry.get_tool("nonexistent_tool")
        assert retrieved_tool is None


class TestBaseToolFunctionality:
    """BaseTool功能测试"""
    
    def test_validate_parameters(self):
        """测试参数验证"""
        from tools.base import BaseTool
        
        class TestTool(BaseTool):
            @property
            def name(self):
                return "test_tool"
            
            @property
            def description(self):
                return "测试工具"
            
            async def execute(self, **kwargs):
                return {"result": "success"}
        
        tool = TestTool()
        
        # 测试默认参数验证
        assert tool.validate_parameters({}) is True
        assert tool.validate_parameters({"param1": "value1"}) is True


class TestToolsIntegration:
    """工具模块集成测试"""
    
    @pytest.mark.asyncio
    async def test_file_read_and_text_extract_integration(self):
        """测试文件读取和文本提取集成"""
        from tools.file_tools import FileReadTool
        from tools.text_tools import TextExtractTool
        
        # 创建测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# 测试标题\n\n这是测试内容。\n\n## 第二节\n\n更多内容。\n")
            temp_path = f.name
        
        try:
            # 读取文件
            file_tool = FileReadTool()
            file_result = await file_tool.execute(file_path=temp_path, format="text")
            
            assert "error" not in file_result
            content = file_result["content"]
            
            # 提取标题
            text_tool = TextExtractTool()
            headings_result = await text_tool.execute(content=content, extract_type="headings")
            
            assert "error" not in headings_result
            headings = headings_result["headings"]
            
            # 验证标题提取
            heading_texts = [h["text"] for h in headings]
            assert "测试标题" in heading_texts
            assert "第二节" in heading_texts
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)