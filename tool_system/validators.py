# tool_system/validators.py

"""
参数验证器

负责验证工具调用参数是否符合工具定义。
"""

from typing import Dict, List, Optional, Any
from .models import ToolParameter


class ParameterValidator:
    """参数验证器"""
    
    def validate(
        self,
        parameters: Dict[str, Any],
        parameter_definitions: List[ToolParameter]
    ) -> Optional[str]:
        """
        验证参数
        
        Args:
            parameters: 调用参数
            parameter_definitions: 参数定义列表
            
        Returns:
            Optional[str]: 错误信息，如果验证通过则返回 None
        """
        if not parameter_definitions:
            return None
        
        # 检查必需参数
        for param_def in parameter_definitions:
            if param_def.required and param_def.name not in parameters:
                return f"Missing required parameter: {param_def.name}"
        
        # 验证每个参数
        for param_name, param_value in parameters.items():
            # 查找参数定义
            param_def = self._find_parameter_definition(param_name, parameter_definitions)
            
            if param_def:
                # 验证类型
                type_error = self._validate_type(param_name, param_value, param_def.type)
                if type_error:
                    return type_error
                
                # 验证枚举值
                if param_def.enum and param_value not in param_def.enum:
                    return f"Parameter '{param_name}' must be one of: {param_def.enum}"
        
        return None
    
    def _find_parameter_definition(
        self,
        param_name: str,
        parameter_definitions: List[ToolParameter]
    ) -> Optional[ToolParameter]:
        """查找参数定义"""
        for param_def in parameter_definitions:
            if param_def.name == param_name:
                return param_def
        return None
    
    def _validate_type(
        self,
        param_name: str,
        param_value: Any,
        expected_type: str
    ) -> Optional[str]:
        """验证参数类型"""
        if expected_type == "string":
            if not isinstance(param_value, str):
                return f"Parameter '{param_name}' must be a string"
        
        elif expected_type == "number":
            if not isinstance(param_value, (int, float)):
                return f"Parameter '{param_name}' must be a number"
        
        elif expected_type == "boolean":
            if not isinstance(param_value, bool):
                return f"Parameter '{param_name}' must be a boolean"
        
        elif expected_type == "object":
            if not isinstance(param_value, dict):
                return f"Parameter '{param_name}' must be an object"
        
        elif expected_type == "array":
            if not isinstance(param_value, list):
                return f"Parameter '{param_name}' must be an array"
        
        return None
