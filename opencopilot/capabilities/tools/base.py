"""
工具基类和注册表
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """工具参数定义"""
        return {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        # 基类提供默认实现，子类可以覆盖
        return True


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, name: str, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[name] = tool
    
    def unregister(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""
        tool = self.get_tool(name)
        if tool:
            return {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        return None
    
    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """获取所有工具信息"""
        return [self.get_tool_info(name) for name in self.list_tools()]


class ToolCallParser:
    """工具调用解析器"""
    
    @staticmethod
    def parse_tool_calls(text: str) -> List[Dict[str, Any]]:
        """
        从文本中解析工具调用
        
        支持格式：
        1. JSON格式: {"tool_calls": [...]}
        2. 标记格式: ```tool_call\n...\n```
        """
        import json
        import re
        
        tool_calls = []
        
        # 尝试解析JSON格式
        try:
            # 查找JSON块
            json_pattern = r'\{[\s\S]*"tool_calls"[\s\S]*\}'
            json_match = re.search(json_pattern, text)
            if json_match:
                data = json.loads(json_match.group())
                if "tool_calls" in data:
                    tool_calls.extend(data["tool_calls"])
        except json.JSONDecodeError:
            pass
        
        # 尝试解析标记格式
        tool_call_pattern = r'```tool_call\n([\s\S]*?)\n```'
        matches = re.findall(tool_call_pattern, text)
        for match in matches:
            try:
                tool_call = json.loads(match)
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    @staticmethod
    def format_tool_result(tool_name: str, result: Any) -> str:
        """格式化工具调用结果"""
        import json
        
        if isinstance(result, str):
            return f"[工具结果] {tool_name}:\n{result}"
        else:
            try:
                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                return f"[工具结果] {tool_name}:\n{result_str}"
            except:
                return f"[工具结果] {tool_name}:\n{str(result)}"