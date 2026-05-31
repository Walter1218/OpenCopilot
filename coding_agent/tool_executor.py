"""
工具执行器

执行各种工具，包括 IDE 工具和分析工具。
"""

import asyncio
import os
import subprocess
from typing import Dict, Any, Optional, List
import aiohttp


class IDEToolExecutor:
    """IDE 工具执行器"""
    
    def __init__(self, ide_port: Optional[int] = None):
        """
        初始化 IDE 工具执行器
        
        Args:
            ide_port: IDE 端口
        """
        self.ide_port = ide_port
        self._port_cache = None
    
    async def _get_ide_port(self) -> int:
        """
        获取 IDE 端口
        
        Returns:
            int: IDE 端口
        
        Raises:
            RuntimeError: IDE Extension 未启动
        """
        if self.ide_port:
            return self.ide_port
        
        if self._port_cache:
            return self._port_cache
        
        # 从临时文件读取端口
        port_file = os.path.join(os.tmpdir(), 'asu_ide_port.txt')
        if os.path.exists(port_file):
            with open(port_file, 'r') as f:
                self._port_cache = int(f.read().strip())
                return self._port_cache
        
        raise RuntimeError("IDE Extension 未启动或端口文件不存在")
    
    async def get_diagnostics(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        获取诊断信息
        
        Args:
            file_path: 文件路径
        
        Returns:
            Dict[str, Any]: 诊断信息
        """
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/diagnostics"
            
            params = {}
            if file_path:
                params["file"] = file_path
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._parse_diagnostics(data)
                    else:
                        return {"errors": [], "warnings": [], "raw": {}}
        except Exception as e:
            return {"errors": [], "warnings": [], "error": str(e)}
    
    async def get_symbol(self, file_path: Optional[str] = None, line: Optional[int] = None) -> Dict[str, Any]:
        """
        获取符号信息
        
        Args:
            file_path: 文件路径
            line: 行号
        
        Returns:
            Dict[str, Any]: 符号信息
        """
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/symbol"
            
            params = {}
            if file_path:
                params["file"] = file_path
            if line is not None:
                params["line"] = line
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_git_diff(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        获取 Git diff
        
        Args:
            file_path: 文件路径
        
        Returns:
            Dict[str, Any]: Git diff 信息
        """
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/git-diff"
            
            params = {}
            if file_path:
                params["file"] = file_path
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"diff": ""}
        except Exception as e:
            return {"diff": "", "error": str(e)}
    
    async def apply_change(
        self,
        content: Optional[str] = None,
        replace: Optional[str] = None,
        range_info: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        应用修改到 IDE
        
        Args:
            content: 新内容
            replace: 替换内容
            range_info: 范围信息
            file_path: 文件路径
            confirm: 是否确认
        
        Returns:
            Dict[str, Any]: 应用结果
        """
        if not confirm:
            return {
                "status": "pending",
                "message": "需要用户确认",
                "preview": (content or replace or "")[:500]
            }
        
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/apply"
            
            payload = {}
            if content:
                payload["content"] = content
            if replace:
                payload["replace"] = replace
            if range_info:
                payload["range"] = range_info
            if file_path:
                payload["file"] = file_path
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"status": "error", "message": f"HTTP {resp.status}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def get_context(self, file_path: Optional[str] = None, line: Optional[int] = None) -> Dict[str, Any]:
        """
        获取完整上下文
        
        Args:
            file_path: 文件路径
            line: 行号
        
        Returns:
            Dict[str, Any]: 上下文信息
        """
        # 并行获取各种信息
        diagnostics_task = self.get_diagnostics(file_path)
        symbol_task = self.get_symbol(file_path, line)
        git_diff_task = self.get_git_diff(file_path)
        
        diagnostics, symbol, git_diff = await asyncio.gather(
            diagnostics_task,
            symbol_task,
            git_diff_task,
            return_exceptions=True
        )
        
        # 处理异常
        if isinstance(diagnostics, Exception):
            diagnostics = {"errors": [], "warnings": [], "error": str(diagnostics)}
        if isinstance(symbol, Exception):
            symbol = {"error": str(symbol)}
        if isinstance(git_diff, Exception):
            git_diff = {"diff": "", "error": str(git_diff)}
        
        return {
            "diagnostics": diagnostics,
            "symbol": symbol,
            "git_diff": git_diff
        }
    
    def _parse_diagnostics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析诊断信息
        
        Args:
            data: 原始诊断数据
        
        Returns:
            Dict[str, Any]: 解析后的诊断信息
        """
        errors = []
        warnings = []
        
        # 解析不同格式的诊断信息
        if isinstance(data, list):
            for item in data:
                severity = item.get("severity", 0)
                if severity == 1:  # Error
                    errors.append({
                        "line": item.get("range", {}).get("start", {}).get("line", 0),
                        "message": item.get("message", ""),
                        "code": item.get("code", ""),
                        "source": item.get("source", "")
                    })
                elif severity == 2:  # Warning
                    warnings.append({
                        "line": item.get("range", {}).get("start", {}).get("line", 0),
                        "message": item.get("message", ""),
                        "code": item.get("code", ""),
                        "source": item.get("source", "")
                    })
        elif isinstance(data, dict):
            # 处理其他格式
            if "errors" in data:
                errors = data["errors"]
            if "warnings" in data:
                warnings = data["warnings"]
        
        return {
            "errors": errors,
            "warnings": warnings,
            "raw": data
        }


class AnalysisToolExecutor:
    """分析工具执行器"""
    
    def __init__(self, project_root: Optional[str] = None):
        """
        初始化分析工具执行器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or os.getcwd()
    
    async def run_lint(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        运行 lint 工具
        
        Args:
            file_path: 文件路径
            language: 编程语言
        
        Returns:
            Dict[str, Any]: lint 结果
        """
        try:
            # 根据语言选择 lint 工具
            if language and language.lower() == "python":
                cmd = ["python", "-m", "pylint", file_path, "--output-format=json"]
            elif language and language.lower() in ["javascript", "typescript"]:
                cmd = ["eslint", file_path, "--format=json"]
            else:
                # 默认使用 flake8
                cmd = ["python", "-m", "flake8", file_path, "--format=json"]
            
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "returncode": process.returncode
            }
        except Exception as e:
            return {
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "returncode": -1
            }
    
    async def run_type_check(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        运行类型检查
        
        Args:
            file_path: 文件路径
            language: 编程语言
        
        Returns:
            Dict[str, Any]: 类型检查结果
        """
        try:
            # 根据语言选择类型检查工具
            if language and language.lower() == "python":
                cmd = ["python", "-m", "mypy", file_path, "--ignore-missing-imports"]
            elif language and language.lower() == "typescript":
                cmd = ["tsc", "--noEmit", file_path]
            else:
                return {"error": f"不支持的语言: {language}"}
            
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "returncode": process.returncode
            }
        except Exception as e:
            return {
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "returncode": -1
            }
    
    async def run_test(self, file_path: str, test_framework: Optional[str] = None) -> Dict[str, Any]:
        """
        运行测试
        
        Args:
            file_path: 文件路径
            test_framework: 测试框架
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            # 根据测试框架选择命令
            if test_framework == "pytest":
                cmd = ["python", "-m", "pytest", file_path, "-v"]
            elif test_framework == "unittest":
                cmd = ["python", "-m", "unittest", file_path]
            else:
                # 默认使用 pytest
                cmd = ["python", "-m", "pytest", file_path, "-v"]
            
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "returncode": process.returncode
            }
        except Exception as e:
            return {
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "returncode": -1
            }
    
    async def read_file(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            start_line: 起始行号
            end_line: 结束行号
        
        Returns:
            Dict[str, Any]: 文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 处理行号范围
            if start_line is not None or end_line is not None:
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                lines = lines[start:end]
            
            content = ''.join(lines)
            
            return {
                "content": content,
                "lines": len(lines),
                "file_path": file_path
            }
        except Exception as e:
            return {
                "error": str(e),
                "content": "",
                "lines": 0,
                "file_path": file_path
            }
    
    async def write_file(self, file_path: str, content: str, confirm: bool = False) -> Dict[str, Any]:
        """
        写入文件内容
        
        Args:
            file_path: 文件路径
            content: 文件内容
            confirm: 是否确认
        
        Returns:
            Dict[str, Any]: 写入结果
        """
        if not confirm:
            return {
                "status": "pending",
                "message": "需要用户确认",
                "preview": content[:500]
            }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "status": "success",
                "message": f"文件已写入: {file_path}",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "file_path": file_path
            }


class ToolExecutor:
    """工具执行器管理器"""
    
    def __init__(self, ide_port: Optional[int] = None, project_root: Optional[str] = None):
        """
        初始化工具执行器
        
        Args:
            ide_port: IDE 端口
            project_root: 项目根目录
        """
        self.ide_executor = IDEToolExecutor(ide_port)
        self.analysis_executor = AnalysisToolExecutor(project_root)
    
    async def get_full_context(self, file_path: Optional[str] = None, line: Optional[int] = None) -> Dict[str, Any]:
        """
        获取完整上下文
        
        Args:
            file_path: 文件路径
            line: 行号
        
        Returns:
            Dict[str, Any]: 完整上下文
        """
        # 从 IDE 获取上下文
        ide_context = await self.ide_executor.get_context(file_path, line)
        
        # 读取文件内容
        file_content = {}
        if file_path:
            file_content = await self.analysis_executor.read_file(file_path)
        
        return {
            **ide_context,
            "file_content": file_content
        }
    
    async def execute_analysis(self, file_path: str, analysis_type: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        执行分析
        
        Args:
            file_path: 文件路径
            analysis_type: 分析类型
            language: 编程语言
        
        Returns:
            Dict[str, Any]: 分析结果
        """
        if analysis_type == "lint":
            return await self.analysis_executor.run_lint(file_path, language)
        elif analysis_type == "type_check":
            return await self.analysis_executor.run_type_check(file_path, language)
        elif analysis_type == "test":
            return await self.analysis_executor.run_test(file_path)
        else:
            return {"error": f"不支持的分析类型: {analysis_type}"}
    
    async def apply_fix(self, file_path: str, content: str, confirm: bool = False) -> Dict[str, Any]:
        """
        应用修复
        
        Args:
            file_path: 文件路径
            content: 修复内容
            confirm: 是否确认
        
        Returns:
            Dict[str, Any]: 应用结果
        """
        return await self.analysis_executor.write_file(file_path, content, confirm)