"""
文档搜索提供者

搜索 Markdown、文本等文档文件。
"""

import os
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
from .core import SearchProvider, SearchResult, SearchType


class DocSearchProvider(SearchProvider):
    """
    文档搜索提供者
    
    支持：
    - Markdown 文件搜索
    - 文本文件搜索
    - 内容和标题匹配
    
    使用示例：
        provider = DocSearchProvider("/path/to/workspace")
        results = provider.search("架构设计", scope="./docs")
    """
    
    # 文档文件扩展名
    DOC_EXTENSIONS = {
        ".md", ".markdown", ".txt", ".rst", ".adoc", ".asciidoc",
        ".org", ".wiki", ".textile", ".rdoc", ".pod", ".tex"
    }
    
    # 默认忽略的目录
    DEFAULT_IGNORE_DIRS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".idea", ".vscode"
    }
    
    def __init__(self, workspace: str = None):
        """
        初始化文档搜索提供者
        
        Args:
            workspace: 工作目录
        """
        self.workspace = workspace or os.getcwd()
        self.ignore_dirs = self.DEFAULT_IGNORE_DIRS.copy()
    
    def search(self, query: str, count: int = 10, **kwargs) -> List[SearchResult]:
        """
        执行文档搜索
        
        Args:
            query: 搜索查询
            count: 返回结果数量
            **kwargs: 额外参数
                - scope: 搜索范围（目录）
                - search_title: 是否搜索标题
                - search_content: 是否搜索内容
                - file_types: 文件类型列表
                
        Returns:
            搜索结果列表
        """
        scope = kwargs.get("scope", self.workspace)
        search_title = kwargs.get("search_title", True)
        search_content = kwargs.get("search_content", True)
        file_types = kwargs.get("file_types", self.DOC_EXTENSIONS)
        
        try:
            results = self._search_docs(
                query, scope, search_title, search_content, file_types
            )
            return results[:count]
        except Exception as e:
            print(f"Doc search error: {e}")
            return []
    
    def _search_docs(self, query: str, scope: str,
                    search_title: bool, search_content: bool,
                    file_types: set) -> List[SearchResult]:
        """
        搜索文档
        
        Args:
            query: 搜索查询
            scope: 搜索范围
            search_title: 是否搜索标题
            search_content: 是否搜索内容
            file_types: 文件类型
            
        Returns:
            搜索结果列表
        """
        results = []
        pattern = re.compile(query, re.IGNORECASE)
        
        for root, dirs, files in os.walk(scope):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                # 检查文件类型
                ext = os.path.splitext(file)[1].lower()
                if ext not in file_types:
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    file_results = self._search_file(
                        file_path, query, pattern, search_title, search_content
                    )
                    results.extend(file_results)
                except:
                    continue
        
        return results
    
    def _search_file(self, file_path: str, query: str, pattern: re.Pattern,
                    search_title: bool, search_content: bool) -> List[SearchResult]:
        """
        搜索单个文件
        
        Args:
            file_path: 文件路径
            query: 搜索查询
            pattern: 编译后的正则表达式
            search_title: 是否搜索标题
            search_content: 是否搜索内容
            
        Returns:
            搜索结果列表
        """
        results = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # 计算相对路径
        rel_path = os.path.relpath(file_path, self.workspace)
        
        # 提取标题（Markdown 标题）
        titles = []
        for line in lines:
            if line.strip().startswith('#'):
                titles.append(line.strip())
        
        # 搜索标题
        if search_title:
            for title in titles:
                if pattern.search(title):
                    result = SearchResult(
                        title=rel_path,
                        content=title,
                        url=f"file://{file_path}",
                        source=SearchType.DOC,
                        score=self._calculate_score(query, title, is_title=True),
                        metadata={
                            "file": rel_path,
                            "type": "title",
                            "workspace": self.workspace
                        }
                    )
                    results.append(result)
        
        # 搜索内容
        if search_content:
            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    # 获取上下文（前后各 2 行）
                    start = max(0, line_num - 3)
                    end = min(len(lines), line_num + 2)
                    context = ''.join(lines[start:end]).strip()
                    
                    result = SearchResult(
                        title=f"{rel_path}:{line_num}",
                        content=context,
                        url=f"file://{file_path}",
                        source=SearchType.DOC,
                        score=self._calculate_score(query, line),
                        metadata={
                            "file": rel_path,
                            "line": line_num,
                            "type": "content",
                            "workspace": self.workspace
                        }
                    )
                    results.append(result)
        
        return results
    
    def _calculate_score(self, query: str, content: str, is_title: bool = False) -> float:
        """
        计算匹配分数
        
        Args:
            query: 搜索查询
            content: 匹配内容
            is_title: 是否是标题匹配
            
        Returns:
            分数 (0-1)
        """
        query_lower = query.lower()
        content_lower = content.lower()
        
        # 基础分数
        base_score = 0.5
        
        # 完整匹配
        if query_lower in content_lower:
            base_score = 0.8
        # 部分匹配
        elif any(word in content_lower for word in query_lower.split()):
            base_score = 0.6
        
        # 标题匹配加分
        if is_title:
            base_score += 0.1
        
        return min(1.0, base_score)
    
    def search_by_tag(self, tag: str, scope: str = None) -> List[SearchResult]:
        """
        按标签搜索（Markdown 标签）
        
        Args:
            tag: 标签（不含 #）
            scope: 搜索范围
            
        Returns:
            搜索结果列表
        """
        query = f"#{tag}"
        return self.search(query, scope=scope or self.workspace)
    
    def search_headings(self, query: str, scope: str = None) -> List[SearchResult]:
        """
        搜索标题
        
        Args:
            query: 搜索查询
            scope: 搜索范围
            
        Returns:
            搜索结果列表
        """
        return self.search(
            query, 
            scope=scope or self.workspace,
            search_title=True,
            search_content=False
        )
    
    def add_ignore_dir(self, dir_name: str):
        """添加忽略目录"""
        self.ignore_dirs.add(dir_name)
    
    def remove_ignore_dir(self, dir_name: str):
        """移除忽略目录"""
        self.ignore_dirs.discard(dir_name)
