"""
符号分析器

提供代码符号分析功能，包括：
- 符号引用查找 (Find References)
- 定义跳转 (Go to Definition)
- 文档符号列表 (Document Symbols)

支持两种模式：
1. AST 模式：使用 Python ast 模块，无需外部依赖
2. LSP 模式：集成 Language Server Protocol，提供更准确的分析
"""

import os
import ast
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class SymbolKind(int, Enum):
    """符号类型（VS Code 标准）"""
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
    OBJECT = 19
    KEY = 20
    NULL = 21
    ENUM_MEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPE_PARAMETER = 26


@dataclass
class Position:
    """位置"""
    line: int  # 0-based
    character: int  # 0-based


@dataclass
class Range:
    """范围"""
    start: Position
    end: Position


@dataclass
class Location:
    """位置信息"""
    file_path: str
    range: Range


@dataclass
class SymbolInfo:
    """符号信息"""
    name: str
    kind: SymbolKind
    location: Location
    container_name: Optional[str] = None
    detail: Optional[str] = None


@dataclass
class ReferenceInfo:
    """引用信息"""
    location: Location
    is_definition: bool = False


class ASTSymbolAnalyzer:
    """AST 符号分析器
    
    使用 Python ast 模块进行符号分析。
    无需外部依赖，但功能有限。
    """
    
    def __init__(self):
        self._file_cache: Dict[str, ast.Module] = {}
    
    def _parse_file(self, file_path: str) -> Optional[ast.Module]:
        """解析文件"""
        if file_path in self._file_cache:
            return self._file_cache[file_path]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=file_path)
            self._file_cache[file_path] = tree
            return tree
            
        except Exception as e:
            logger.error(f"解析文件失败 {file_path}: {e}")
            return None
    
    def _get_node_name(self, node: ast.AST) -> Optional[str]:
        """获取节点名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            return node.name
        elif isinstance(node, ast.ClassDef):
            return node.name
        elif isinstance(node, ast.Import):
            return node.names[0].name if node.names else None
        elif isinstance(node, ast.ImportFrom):
            return node.module
        return None
    
    def _get_symbol_kind(self, node: ast.AST) -> SymbolKind:
        """获取符号类型"""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return SymbolKind.FUNCTION
        elif isinstance(node, ast.ClassDef):
            return SymbolKind.CLASS
        elif isinstance(node, ast.Name):
            # 变量或函数调用
            return SymbolKind.VARIABLE
        elif isinstance(node, ast.Attribute):
            return SymbolKind.PROPERTY
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            return SymbolKind.MODULE
        return SymbolKind.VARIABLE
    
    def _node_to_location(self, node: ast.AST, file_path: str) -> Location:
        """将 AST 节点转换为位置信息"""
        return Location(
            file_path=file_path,
            range=Range(
                start=Position(
                    line=node.lineno - 1,  # AST 使用 1-based，转换为 0-based
                    character=node.col_offset
                ),
                end=Position(
                    line=getattr(node, 'end_lineno', node.lineno) - 1,
                    character=getattr(node, 'end_col_offset', node.col_offset)
                )
            )
        )
    
    def get_document_symbols(self, file_path: str) -> List[SymbolInfo]:
        """获取文档符号列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[SymbolInfo]: 符号列表
        """
        tree = self._parse_file(file_path)
        if not tree:
            return []
        
        symbols = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = self._get_node_name(node)
                if name:
                    symbol = SymbolInfo(
                        name=name,
                        kind=self._get_symbol_kind(node),
                        location=self._node_to_location(node, file_path),
                        detail=ast.get_docstring(node)
                    )
                    symbols.append(symbol)
        
        return symbols
    
    def find_definition(self, file_path: str, position: Position) -> Optional[Location]:
        """查找符号定义
        
        Args:
            file_path: 文件路径
            position: 位置
            
        Returns:
            Optional[Location]: 定义位置
        """
        tree = self._parse_file(file_path)
        if not tree:
            return None
        
        # 查找光标下的符号
        symbol_name = self._get_symbol_at_position(tree, position)
        if not symbol_name:
            return None
        
        # 查找定义
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == symbol_name:
                    return self._node_to_location(node, file_path)
            elif isinstance(node, ast.ClassDef):
                if node.name == symbol_name:
                    return self._node_to_location(node, file_path)
        
        return None
    
    def find_references(self, file_path: str, position: Position, 
                       include_declaration: bool = True) -> List[ReferenceInfo]:
        """查找符号引用
        
        Args:
            file_path: 文件路径
            position: 位置
            include_declaration: 是否包含声明
            
        Returns:
            List[ReferenceInfo]: 引用列表
        """
        tree = self._parse_file(file_path)
        if not tree:
            return []
        
        # 查找光标下的符号
        symbol_name = self._get_symbol_at_position(tree, position)
        if not symbol_name:
            return []
        
        references = []
        
        # 查找所有引用
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == symbol_name:
                location = self._node_to_location(node, file_path)
                references.append(ReferenceInfo(
                    location=location,
                    is_definition=False
                ))
            elif isinstance(node, ast.Attribute) and node.attr == symbol_name:
                location = self._node_to_location(node, file_path)
                references.append(ReferenceInfo(
                    location=location,
                    is_definition=False
                ))
        
        # 如果需要包含声明
        if include_declaration:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == symbol_name:
                        location = self._node_to_location(node, file_path)
                        references.append(ReferenceInfo(
                            location=location,
                            is_definition=True
                        ))
                elif isinstance(node, ast.ClassDef):
                    if node.name == symbol_name:
                        location = self._node_to_location(node, file_path)
                        references.append(ReferenceInfo(
                            location=location,
                            is_definition=True
                        ))
        
        return references
    
    def _get_symbol_at_position(self, tree: ast.AST, position: Position) -> Optional[str]:
        """获取光标下的符号名称
        
        Args:
            tree: AST 树
            position: 光标位置
            
        Returns:
            Optional[str]: 符号名称，如果未找到则返回 None
        """
        # 收集所有可能的符号节点
        candidates = []
        
        for node in ast.walk(tree):
            if not hasattr(node, 'lineno') or not hasattr(node, 'col_offset'):
                continue
            
            node_line = node.lineno - 1  # 转换为 0-based
            node_col = node.col_offset
            
            # 检查行号是否匹配
            if node_line != position.line:
                continue
            
            # 获取节点名称
            name = self._get_node_name(node)
            if not name:
                continue
            
            # 计算名称的结束位置
            name_end_col = node_col + len(name)
            
            # 检查光标是否在名称范围内
            if node_col <= position.character <= name_end_col:
                candidates.append((node, name, node_col))
        
        # 如果有多个候选，选择最具体的（列号最大的）
        if candidates:
            candidates.sort(key=lambda x: x[2], reverse=True)
            return candidates[0][1]
        
        return None


class ProjectSymbolIndex:
    """项目符号索引
    
    构建项目级别的符号索引，支持跨文件符号分析。
    """
    
    def __init__(self):
        """初始化项目符号索引"""
        self._symbol_index: Dict[str, List[SymbolInfo]] = {}  # 文件路径 -> 符号列表
        self._name_index: Dict[str, List[SymbolInfo]] = {}  # 符号名称 -> 符号列表
        self._file_hashes: Dict[str, str] = {}  # 文件路径 -> 文件哈希
        self._ast_analyzer = ASTSymbolAnalyzer()
    
    def _get_file_hash(self, file_path: str) -> str:
        """获取文件哈希"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""
    
    def index_file(self, file_path: str) -> bool:
        """索引单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否成功
        """
        if not os.path.exists(file_path):
            return False
        
        # 检查文件是否已索引且未变化
        current_hash = self._get_file_hash(file_path)
        if file_path in self._file_hashes and self._file_hashes[file_path] == current_hash:
            return True
        
        try:
            # 解析文件
            tree = self._ast_analyzer._parse_file(file_path)
            if not tree:
                return False
            
            # 提取符号
            symbols = self._ast_analyzer.get_document_symbols(file_path)
            
            # 更新索引
            self._symbol_index[file_path] = symbols
            self._file_hashes[file_path] = current_hash
            
            # 更新名称索引
            for symbol in symbols:
                if symbol.name not in self._name_index:
                    self._name_index[symbol.name] = []
                self._name_index[symbol.name].append(symbol)
            
            return True
            
        except Exception as e:
            logger.error(f"索引文件失败 {file_path}: {e}")
            return False
    
    def index_directory(self, directory: str, extensions: List[str] = None) -> int:
        """索引目录
        
        Args:
            directory: 目录路径
            extensions: 文件扩展名过滤（默认: [".py"]）
            
        Returns:
            int: 索引的文件数量
        """
        if extensions is None:
            extensions = [".py"]
        
        indexed_count = 0
        
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
                'node_modules', '__pycache__', 'venv', '.git', 'dist', 'build'
            ]]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    if self.index_file(file_path):
                        indexed_count += 1
        
        logger.info(f"索引完成: {indexed_count} 个文件")
        return indexed_count
    
    def find_symbol(self, name: str, symbol_type: Optional[SymbolKind] = None) -> List[SymbolInfo]:
        """查找符号
        
        Args:
            name: 符号名称
            symbol_type: 符号类型过滤
            
        Returns:
            List[SymbolInfo]: 符号列表
        """
        symbols = self._name_index.get(name, [])
        
        if symbol_type:
            symbols = [s for s in symbols if s.kind == symbol_type]
        
        return symbols
    
    def find_references(self, name: str, exclude_file: Optional[str] = None) -> List[SymbolInfo]:
        """查找符号的所有引用
        
        Args:
            name: 符号名称
            exclude_file: 排除的文件路径
            
        Returns:
            List[SymbolInfo]: 引用列表
        """
        references = []
        
        for file_path, symbols in self._symbol_index.items():
            if exclude_file and file_path == exclude_file:
                continue
            
            for symbol in symbols:
                if symbol.name == name:
                    references.append(symbol)
        
        return references
    
    def get_file_symbols(self, file_path: str) -> List[SymbolInfo]:
        """获取文件的所有符号
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[SymbolInfo]: 符号列表
        """
        return self._symbol_index.get(file_path, [])
    
    def get_all_symbols(self) -> Dict[str, List[SymbolInfo]]:
        """获取所有符号
        
        Returns:
            Dict[str, List[SymbolInfo]]: 文件路径 -> 符号列表
        """
        return self._symbol_index.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取索引统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_symbols = sum(len(symbols) for symbols in self._symbol_index.values())
        unique_names = len(self._name_index)
        
        return {
            "total_files": len(self._symbol_index),
            "total_symbols": total_symbols,
            "unique_symbol_names": unique_names,
            "files": list(self._symbol_index.keys())
        }
    
    def clear(self):
        """清除索引"""
        self._symbol_index.clear()
        self._name_index.clear()
        self._file_hashes.clear()


class SymbolAnalyzer:
    """符号分析器
    
    提供统一的符号分析接口。
    支持 AST 模式和 LSP 模式。
    """
    
    def __init__(self, use_lsp: bool = False):
        """初始化符号分析器
        
        Args:
            use_lsp: 是否使用 LSP 模式
        """
        self.use_lsp = use_lsp
        self.ast_analyzer = ASTSymbolAnalyzer()
        self._lsp_clients = {}
        self._project_index = ProjectSymbolIndex()
    
    def get_document_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        """获取文档符号列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Dict[str, Any]]: 符号列表
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return []
        
        symbols = self.ast_analyzer.get_document_symbols(file_path)
        
        return [
            {
                "name": s.name,
                "kind": s.kind.value,
                "location": {
                    "file": s.location.file_path,
                    "range": {
                        "start": {
                            "line": s.location.range.start.line,
                            "character": s.location.range.start.character
                        },
                        "end": {
                            "line": s.location.range.end.line,
                            "character": s.location.range.end.character
                        }
                    }
                },
                "containerName": s.container_name,
                "detail": s.detail
            }
            for s in symbols
        ]
    
    def find_definition(self, file_path: str, line: int, character: int) -> Optional[Dict[str, Any]]:
        """查找符号定义
        
        Args:
            file_path: 文件路径
            line: 行号 (0-based)
            character: 列号 (0-based)
            
        Returns:
            Optional[Dict[str, Any]]: 定义位置
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
        
        position = Position(line=line, character=character)
        location = self.ast_analyzer.find_definition(file_path, position)
        
        if location:
            return {
                "file": location.file_path,
                "range": {
                    "start": {
                        "line": location.range.start.line,
                        "character": location.range.start.character
                    },
                    "end": {
                        "line": location.range.end.line,
                        "character": location.range.end.character
                    }
                }
            }
        
        return None
    
    def find_references(self, file_path: str, line: int, character: int,
                       include_declaration: bool = True) -> List[Dict[str, Any]]:
        """查找符号引用
        
        Args:
            file_path: 文件路径
            line: 行号 (0-based)
            character: 列号 (0-based)
            include_declaration: 是否包含声明
            
        Returns:
            List[Dict[str, Any]]: 引用列表
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return []
        
        position = Position(line=line, character=character)
        references = self.ast_analyzer.find_references(file_path, position, include_declaration)
        
        return [
            {
                "file": ref.location.file_path,
                "range": {
                    "start": {
                        "line": ref.location.range.start.line,
                        "character": ref.location.range.start.character
                    },
                    "end": {
                        "line": ref.location.range.end.line,
                        "character": ref.location.range.end.character
                    }
                },
                "isDefinition": ref.is_definition
            }
            for ref in references
        ]
    
    def clear_cache(self):
        """清除缓存"""
        self.ast_analyzer._file_cache.clear()
        self._project_index.clear()
    
    def index_project(self, project_path: str, extensions: List[str] = None) -> int:
        """索引项目
        
        Args:
            project_path: 项目路径
            extensions: 文件扩展名过滤
            
        Returns:
            int: 索引的文件数量
        """
        if not os.path.exists(project_path):
            logger.error(f"项目路径不存在: {project_path}")
            return 0
        
        return self._project_index.index_directory(project_path, extensions)
    
    def find_symbol_in_project(self, name: str, symbol_type: Optional[int] = None) -> List[Dict[str, Any]]:
        """在项目中查找符号
        
        Args:
            name: 符号名称
            symbol_type: 符号类型（SymbolKind 的值）
            
        Returns:
            List[Dict[str, Any]]: 符号列表
        """
        kind = SymbolKind(symbol_type) if symbol_type else None
        symbols = self._project_index.find_symbol(name, kind)
        
        return [
            {
                "name": s.name,
                "kind": s.kind.value,
                "location": {
                    "file": s.location.file_path,
                    "range": {
                        "start": {
                            "line": s.location.range.start.line,
                            "character": s.location.range.start.character
                        },
                        "end": {
                            "line": s.location.range.end.line,
                            "character": s.location.range.end.character
                        }
                    }
                },
                "containerName": s.container_name,
                "detail": s.detail
            }
            for s in symbols
        ]
    
    def find_references_in_project(self, name: str, exclude_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """在项目中查找符号引用
        
        Args:
            name: 符号名称
            exclude_file: 排除的文件路径
            
        Returns:
            List[Dict[str, Any]]: 引用列表
        """
        references = self._project_index.find_references(name, exclude_file)
        
        return [
            {
                "name": s.name,
                "kind": s.kind.value,
                "location": {
                    "file": s.location.file_path,
                    "range": {
                        "start": {
                            "line": s.location.range.start.line,
                            "character": s.location.range.start.character
                        },
                        "end": {
                            "line": s.location.range.end.line,
                            "character": s.location.range.end.character
                        }
                    }
                },
                "containerName": s.container_name
            }
            for s in references
        ]
    
    def get_project_symbols(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取项目所有符号
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: 文件路径 -> 符号列表
        """
        all_symbols = self._project_index.get_all_symbols()
        
        result = {}
        for file_path, symbols in all_symbols.items():
            result[file_path] = [
                {
                    "name": s.name,
                    "kind": s.kind.value,
                    "location": {
                        "file": s.location.file_path,
                        "range": {
                            "start": {
                                "line": s.location.range.start.line,
                                "character": s.location.range.start.character
                            },
                            "end": {
                                "line": s.location.range.end.line,
                                "character": s.location.range.end.character
                            }
                        }
                    },
                    "containerName": s.container_name,
                    "detail": s.detail
                }
                for s in symbols
            ]
        
        return result
    
    def get_project_statistics(self) -> Dict[str, Any]:
        """获取项目符号统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return self._project_index.get_statistics()


# 全局符号分析器实例
_symbol_analyzer: Optional[SymbolAnalyzer] = None


def get_symbol_analyzer() -> SymbolAnalyzer:
    """获取全局符号分析器实例
    
    Returns:
        SymbolAnalyzer: 符号分析器实例
    """
    global _symbol_analyzer
    if _symbol_analyzer is None:
        _symbol_analyzer = SymbolAnalyzer()
    return _symbol_analyzer


# 测试代码
if __name__ == "__main__":
    def test_symbol_analyzer():
        """测试符号分析器"""
        analyzer = SymbolAnalyzer()
        
        # 测试文件
        test_file = __file__
        
        print(f"分析文件: {test_file}")
        
        # 获取文档符号
        symbols = analyzer.get_document_symbols(test_file)
        print(f"\n找到 {len(symbols)} 个符号:")
        for symbol in symbols[:10]:  # 只显示前 10 个
            print(f"  - {symbol['name']} (kind: {symbol['kind']})")
        
        # 查找定义
        if symbols:
            first_symbol = symbols[0]
            line = first_symbol['location']['range']['start']['line']
            char = first_symbol['location']['range']['start']['character']
            
            definition = analyzer.find_definition(test_file, line, char)
            print(f"\n查找定义 ({line}:{char}):")
            if definition:
                print(f"  找到: {definition['file']}:{definition['range']['start']['line']}")
            else:
                print("  未找到")
    
    test_symbol_analyzer()
