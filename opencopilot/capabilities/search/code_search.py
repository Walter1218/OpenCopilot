"""
代码搜索提供者

使用 ripgrep 或 grep 进行本地代码搜索。
"""

import os
import subprocess
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
from .core import SearchProvider, SearchResult, SearchType


class CodeSearchProvider(SearchProvider):
    """
    代码搜索提供者
    
    支持：
    - 正则表达式搜索
    - 文件类型过滤
    - 目录范围限制
    
    使用示例：
        provider = CodeSearchProvider("/path/to/workspace")
        results = provider.search("def process_data", scope="./src")
    """
    
    # 默认忽略的目录
    DEFAULT_IGNORE_DIRS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".idea", ".vscode", "dist", "build", "*.egg-info"
    }
    
    # 默认支持的代码文件扩展面
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
        ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
        ".scala", ".r", ".m", ".mm", ".sh", ".bash", ".zsh", ".fish",
        ".sql", ".html", ".css", ".scss", ".less", ".json", ".yaml",
        ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".md", ".txt"
    }
    
    def __init__(self, workspace: str = None):
        """
        初始化代码搜索提供者
        
        Args:
            workspace: 工作目录
        """
        self.workspace = workspace or os.getcwd()
        self.ignore_dirs = self.DEFAULT_IGNORE_DIRS.copy()
    
    def search(self, query: str, count: int = 10, **kwargs) -> List[SearchResult]:
        """
        执行代码搜索
        
        Args:
            query: 搜索查询（支持正则表达式）
            count: 返回结果数量
            **kwargs: 额外参数
                - scope: 搜索范围（目录）
                - file_types: 文件类型列表
                - ignore_dirs: 忽略的目录
                - case_sensitive: 是否区分大小写
                
        Returns:
            搜索结果列表
        """
        scope = kwargs.get("scope", self.workspace)
        file_types = kwargs.get("file_types")
        ignore_dirs = kwargs.get("ignore_dirs", self.ignore_dirs)
        case_sensitive = kwargs.get("case_sensitive", False)
        
        try:
            # 使用 ripgrep 或 grep 搜索
            results = self._search_with_grep(
                query, scope, file_types, ignore_dirs, case_sensitive
            )
            return results[:count]
        except Exception as e:
            print(f"Code search error: {e}")
            return []
    
    def _search_with_grep(self, query: str, scope: str, 
                          file_types: Optional[List[str]],
                          ignore_dirs: set, case_sensitive: bool) -> List[SearchResult]:
        """
        使用 grep/ripgrep 搜索
        
        Args:
            query: 搜索查询
            scope: 搜索范围
            file_types: 文件类型
            ignore_dirs: 忽略的目录
            case_sensitive: 是否区分大小写
            
        Returns:
            搜索结果列表
        """
        results = []
        
        # 构建 grep 命令
        cmd = ["grep", "-r", "-n"]
        
        if not case_sensitive:
            cmd.append("-i")
        
        # 添加忽略目录
        for dir_name in ignore_dirs:
            cmd.extend(["--exclude-dir", dir_name])
        
        # 添加文件类型过滤
        if file_types:
            for ext in file_types:
                cmd.extend(["--include", f"*{ext}"])
        else:
            # 默认搜索代码文件
            for ext in self.CODE_EXTENSIONS:
                cmd.extend(["--include", f"*{ext}"])
        
        # 添加搜索模式和范围
        cmd.extend([query, scope])
        
        try:
            # 执行搜索
            output = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # 解析结果
            if output.returncode == 0:
                results = self._parse_grep_output(output.stdout, query)
        except subprocess.TimeoutExpired:
            print("Search timeout")
        except FileNotFoundError:
            # grep 不可用，使用 Python 搜索
            results = self._search_with_python(query, scope, file_types, ignore_dirs)
        
        return results
    
    def _parse_grep_output(self, output: str, query: str) -> List[SearchResult]:
        """
        解析 grep 输出
        
        Args:
            output: grep 输出
            query: 搜索查询
            
        Returns:
            搜索结果列表
        """
        results = []
        
        for line in output.strip().split('\n'):
            if not line:
                continue
            
            # 解析格式：file:line:content
            parts = line.split(':', 2)
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = parts[1]
                content = parts[2]
                
                # 计算相对路径
                try:
                    rel_path = os.path.relpath(file_path, self.workspace)
                except:
                    rel_path = file_path
                
                result = SearchResult(
                    title=f"{rel_path}:{line_num}",
                    content=content.strip(),
                    url=f"file://{file_path}",
                    source=SearchType.CODE,
                    score=self._calculate_score(query, content),
                    metadata={
                        "file": rel_path,
                        "line": int(line_num),
                        "workspace": self.workspace
                    }
                )
                results.append(result)
        
        return results
    
    def _search_with_python(self, query: str, scope: str,
                           file_types: Optional[List[str]],
                           ignore_dirs: set) -> List[SearchResult]:
        """
        使用 Python 进行搜索（grep 不可用时的后备方案）
        
        Args:
            query: 搜索查询
            scope: 搜索范围
            file_types: 文件类型
            ignore_dirs: 忽略的目录
            
        Returns:
            搜索结果列表
        """
        results = []
        pattern = re.compile(query, re.IGNORECASE)
        
        for root, dirs, files in os.walk(scope):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                # 检查文件类型
                ext = os.path.splitext(file)[1]
                if file_types and ext not in file_types:
                    continue
                if not file_types and ext not in self.CODE_EXTENSIONS:
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                # 计算相对路径
                                rel_path = os.path.relpath(file_path, self.workspace)
                                
                                result = SearchResult(
                                    title=f"{rel_path}:{line_num}",
                                    content=line.strip(),
                                    url=f"file://{file_path}",
                                    source=SearchType.CODE,
                                    score=self._calculate_score(query, line),
                                    metadata={
                                        "file": rel_path,
                                        "line": line_num,
                                        "workspace": self.workspace
                                    }
                                )
                                results.append(result)
                except:
                    continue
        
        return results
    
    def _calculate_score(self, query: str, content: str) -> float:
        """
        计算匹配分数
        
        Args:
            query: 搜索查询
            content: 匹配内容
            
        Returns:
            分数 (0-1)
        """
        # 简单的分数计算：匹配度
        query_lower = query.lower()
        content_lower = content.lower()
        
        if query_lower in content_lower:
            # 完整匹配
            return 0.9
        elif any(word in content_lower for word in query_lower.split()):
            # 部分匹配
            return 0.6
        else:
            # 正则匹配
            return 0.5
    
    def add_ignore_dir(self, dir_name: str):
        """添加忽略目录"""
        self.ignore_dirs.add(dir_name)
    
    def remove_ignore_dir(self, dir_name: str):
        """移除忽略目录"""
        self.ignore_dirs.discard(dir_name)
