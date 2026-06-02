"""
符号分析器测试

测试符号分析器的各项功能：
1. AST 符号分析
2. 项目符号索引
3. 跨文件符号查找
4. 符号引用查找
"""

import pytest
import os
import tempfile
import shutil

# 导入被测试模块
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.symbol_analyzer import (
    SymbolAnalyzer,
    ProjectSymbolIndex,
    ASTSymbolAnalyzer,
    Position,
    SymbolKind
)


class TestASTSymbolAnalyzer:
    """AST 符号分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建 AST 符号分析器实例"""
        return ASTSymbolAnalyzer()
    
    @pytest.fixture
    def test_file(self):
        """创建测试文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''"""测试文件"""

def hello():
    """Say hello"""
    print("Hello, World!")

def greet(name):
    """Greet someone"""
    hello()
    print(f"Hello, {name}!")

class MyClass:
    """Test class"""
    
    def method(self):
        """Test method"""
        hello()

# 使用
hello()
greet("World")
obj = MyClass()
obj.method()
''')
            return f.name
    
    def test_get_document_symbols(self, analyzer, test_file):
        """测试获取文档符号"""
        symbols = analyzer.get_document_symbols(test_file)
        
        assert len(symbols) > 0
        
        # 检查是否包含预期的符号
        symbol_names = [s.name for s in symbols]
        assert "hello" in symbol_names
        assert "greet" in symbol_names
        assert "MyClass" in symbol_names
        assert "method" in symbol_names
    
    def test_find_definition(self, analyzer, test_file):
        """测试查找定义"""
        # 查找 hello 函数的定义
        # hello() 调用在第 9 行（0-based 索引为 8）
        position = Position(line=8, character=4)  # hello() 调用
        location = analyzer.find_definition(test_file, position)
        
        assert location is not None
        assert location.file_path == test_file
        assert location.range.start.line == 2  # hello 函数定义在第 3 行（0-based 索引为 2）
    
    def test_find_references(self, analyzer, test_file):
        """测试查找引用"""
        # 查找 hello 函数的引用
        # hello 函数定义在第 3 行（0-based 索引为 2）
        position = Position(line=2, character=4)  # hello 函数定义
        references = analyzer.find_references(test_file, position, include_declaration=True)
        
        assert len(references) > 0
        
        # 应该包含定义和调用
        definition_refs = [r for r in references if r.is_definition]
        usage_refs = [r for r in references if not r.is_definition]
        
        assert len(definition_refs) >= 1
        assert len(usage_refs) >= 1
    
    def test_get_symbol_at_position(self, analyzer, test_file):
        """测试获取光标下的符号"""
        tree = analyzer._parse_file(test_file)
        
        # 测试 hello 函数定义（第 3 行，0-based 索引为 2）
        position = Position(line=2, character=4)
        symbol_name = analyzer._get_symbol_at_position(tree, position)
        assert symbol_name == "hello"
        
        # 测试 greet 函数定义（第 7 行，0-based 索引为 6）
        position = Position(line=6, character=4)
        symbol_name = analyzer._get_symbol_at_position(tree, position)
        assert symbol_name == "greet"
    
    def test_nonexistent_file(self, analyzer):
        """测试不存在的文件"""
        symbols = analyzer.get_document_symbols("/nonexistent/file.py")
        assert symbols == []
    
    def test_invalid_python_file(self, analyzer):
        """测试无效的 Python 文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def invalid_syntax(:\n")
            f.name
        
        try:
            symbols = analyzer.get_document_symbols(f.name)
            assert symbols == []
        finally:
            os.unlink(f.name)


class TestProjectSymbolIndex:
    """项目符号索引测试类"""
    
    @pytest.fixture
    def project_dir(self):
        """创建测试项目目录"""
        temp_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        files = {
            "main.py": '''"""Main module"""

def main():
    """Main function"""
    print("Hello from main")

if __name__ == "__main__":
    main()
''',
            "utils.py": '''"""Utils module"""

def helper():
    """Helper function"""
    return "helper"

class Utils:
    """Utils class"""
    
    def method(self):
        """Utils method"""
        return helper()
''',
            "submodule/__init__.py": '''"""Submodule"""
''',
            "submodule/core.py": '''"""Core module"""

from ..utils import Utils

def core_function():
    """Core function"""
    utils = Utils()
    return utils.method()
'''
        }
        
        for filename, content in files.items():
            filepath = os.path.join(temp_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
        
        yield temp_dir
        
        # 清理
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def index(self):
        """创建项目符号索引实例"""
        return ProjectSymbolIndex()
    
    def test_index_file(self, index, project_dir):
        """测试索引单个文件"""
        file_path = os.path.join(project_dir, "main.py")
        
        result = index.index_file(file_path)
        
        assert result is True
        assert file_path in index._symbol_index
        assert len(index._symbol_index[file_path]) > 0
    
    def test_index_directory(self, index, project_dir):
        """测试索引目录"""
        indexed_count = index.index_directory(project_dir)
        
        assert indexed_count > 0
        assert len(index._symbol_index) > 0
    
    def test_find_symbol(self, index, project_dir):
        """测试查找符号"""
        index.index_directory(project_dir)
        
        # 查找 main 函数
        symbols = index.find_symbol("main")
        assert len(symbols) > 0
        assert any(s.name == "main" for s in symbols)
        
        # 查找 Utils 类
        symbols = index.find_symbol("Utils")
        assert len(symbols) > 0
        assert any(s.name == "Utils" for s in symbols)
    
    def test_find_references(self, index, project_dir):
        """测试查找引用"""
        index.index_directory(project_dir)
        
        # 查找 helper 函数的引用
        references = index.find_references("helper")
        assert len(references) > 0
    
    def test_get_file_symbols(self, index, project_dir):
        """测试获取文件符号"""
        index.index_directory(project_dir)
        
        file_path = os.path.join(project_dir, "utils.py")
        symbols = index.get_file_symbols(file_path)
        
        assert len(symbols) > 0
        symbol_names = [s.name for s in symbols]
        assert "helper" in symbol_names
        assert "Utils" in symbol_names
    
    def test_get_statistics(self, index, project_dir):
        """测试获取统计信息"""
        index.index_directory(project_dir)
        
        stats = index.get_statistics()
        
        assert "total_files" in stats
        assert "total_symbols" in stats
        assert "unique_symbol_names" in stats
        assert stats["total_files"] > 0
        assert stats["total_symbols"] > 0
    
    def test_clear(self, index, project_dir):
        """测试清除索引"""
        index.index_directory(project_dir)
        assert len(index._symbol_index) > 0
        
        index.clear()
        assert len(index._symbol_index) == 0
        assert len(index._name_index) == 0
        assert len(index._file_hashes) == 0
    
    def test_nonexistent_directory(self, index):
        """测试不存在的目录"""
        indexed_count = index.index_directory("/nonexistent/dir")
        assert indexed_count == 0


class TestSymbolAnalyzer:
    """符号分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建符号分析器实例"""
        return SymbolAnalyzer()
    
    @pytest.fixture
    def project_dir(self):
        """创建测试项目目录"""
        temp_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        files = {
            "main.py": '''"""Main module"""

def main():
    """Main function"""
    print("Hello from main")

if __name__ == "__main__":
    main()
''',
            "utils.py": '''"""Utils module"""

def helper():
    """Helper function"""
    return "helper"

class Utils:
    """Utils class"""
    
    def method(self):
        """Utils method"""
        return helper()
'''
        }
        
        for filename, content in files.items():
            filepath = os.path.join(temp_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
        
        yield temp_dir
        
        # 清理
        shutil.rmtree(temp_dir)
    
    def test_get_document_symbols(self, analyzer, project_dir):
        """测试获取文档符号"""
        file_path = os.path.join(project_dir, "main.py")
        
        symbols = analyzer.get_document_symbols(file_path)
        
        assert len(symbols) > 0
        assert any(s["name"] == "main" for s in symbols)
    
    def test_find_definition(self, analyzer, project_dir):
        """测试查找定义"""
        file_path = os.path.join(project_dir, "main.py")
        
        # 查找 main 函数定义
        # main 函数定义在第 3 行（0-based 索引为 2）
        definition = analyzer.find_definition(file_path, 2, 4)
        
        assert definition is not None
        assert definition["file"] == file_path
    
    def test_find_references(self, analyzer, project_dir):
        """测试查找引用"""
        file_path = os.path.join(project_dir, "main.py")
        
        # 查找 main 函数引用
        references = analyzer.find_references(file_path, 4, 4)
        
        assert len(references) > 0
    
    def test_index_project(self, analyzer, project_dir):
        """测试索引项目"""
        indexed_count = analyzer.index_project(project_dir)
        
        assert indexed_count > 0
    
    def test_find_symbol_in_project(self, analyzer, project_dir):
        """测试在项目中查找符号"""
        analyzer.index_project(project_dir)
        
        # 查找 main 函数
        symbols = analyzer.find_symbol_in_project("main")
        
        assert len(symbols) > 0
        assert any(s["name"] == "main" for s in symbols)
    
    def test_find_references_in_project(self, analyzer, project_dir):
        """测试在项目中查找引用"""
        analyzer.index_project(project_dir)
        
        # 查找 helper 函数的引用
        references = analyzer.find_references_in_project("helper")
        
        assert len(references) > 0
    
    def test_get_project_symbols(self, analyzer, project_dir):
        """测试获取项目符号"""
        analyzer.index_project(project_dir)
        
        symbols = analyzer.get_project_symbols()
        
        assert len(symbols) > 0
        assert any("main.py" in f for f in symbols.keys())
    
    def test_get_project_statistics(self, analyzer, project_dir):
        """测试获取项目统计信息"""
        analyzer.index_project(project_dir)
        
        stats = analyzer.get_project_statistics()
        
        assert "total_files" in stats
        assert "total_symbols" in stats
        assert stats["total_files"] > 0
    
    def test_clear_cache(self, analyzer, project_dir):
        """测试清除缓存"""
        analyzer.index_project(project_dir)
        
        # 确保索引存在
        stats = analyzer.get_project_statistics()
        assert stats["total_files"] > 0
        
        # 清除缓存
        analyzer.clear_cache()
        
        # 索引应该被清除
        stats = analyzer.get_project_statistics()
        assert stats["total_files"] == 0
    
    def test_nonexistent_file(self, analyzer):
        """测试不存在的文件"""
        symbols = analyzer.get_document_symbols("/nonexistent/file.py")
        assert symbols == []
        
        definition = analyzer.find_definition("/nonexistent/file.py", 0, 0)
        assert definition is None
        
        references = analyzer.find_references("/nonexistent/file.py", 0, 0)
        assert references == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])