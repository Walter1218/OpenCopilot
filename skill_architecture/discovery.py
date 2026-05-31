# skill_architecture/discovery.py

import os
import importlib
import inspect
from typing import List, Type
from .base import BaseSkill
from .registry import SkillRegistry


class SkillDiscovery:
    """Skill 自动发现"""
    
    def __init__(self, registry: SkillRegistry):
        self._registry = registry
        self._search_paths: List[str] = []
    
    def add_search_path(self, path: str) -> None:
        """
        添加搜索路径
        
        Args:
            path: 搜索路径
        """
        if path not in self._search_paths:
            self._search_paths.append(path)
    
    def discover(self) -> List[str]:
        """
        执行自动发现
        
        Returns:
            List[str]: 发现的 Skill 名称列表
        """
        discovered = []
        
        for search_path in self._search_paths:
            if not os.path.exists(search_path):
                continue
            
            # 扫描目录
            for item in os.listdir(search_path):
                item_path = os.path.join(search_path, item)
                
                # 如果是目录，递归扫描
                if os.path.isdir(item_path):
                    discovered.extend(self._scan_directory(item_path))
                
                # 如果是 Python 文件，直接扫描
                elif item.endswith('.py'):
                    skills = self._scan_file(item_path)
                    discovered.extend(skills)
        
        return list(set(discovered))
    
    def _scan_directory(self, directory: str) -> List[str]:
        """扫描目录"""
        discovered = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    skills = self._scan_file(file_path)
                    discovered.extend(skills)
        
        return discovered
    
    def _scan_file(self, file_path: str) -> List[str]:
        """扫描文件"""
        discovered = []
        
        try:
            # 动态导入模块
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找 Skill 类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseSkill) and 
                    obj != BaseSkill):
                    
                    # 注册 Skill 类
                    self._registry.register_class(obj)
                    discovered.append(name)
        
        except Exception as e:
            print(f"Failed to scan {file_path}: {e}")
        
        return discovered
    
    def discover_and_register(self) -> List[str]:
        """发现并注册所有 Skill"""
        discovered = self.discover()
        
        # 为每个发现的 Skill 类创建实例并注册
        for skill_name in discovered:
            skill_class = self._registry.get_skill_class(skill_name)
            if skill_class:
                try:
                    skill = skill_class()
                    self._registry.register(skill)
                except Exception as e:
                    print(f"Failed to create instance of {skill_name}: {e}")
        
        return discovered