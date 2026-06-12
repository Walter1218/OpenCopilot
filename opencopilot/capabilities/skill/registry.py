# skill_architecture/registry.py

import os
import importlib
import inspect
from typing import Dict, List, Optional, Type, Any
from .base import BaseSkill
from .models import SkillMetadata


class SkillRegistry:
    """Skill 注册表"""
    
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._skill_classes: Dict[str, Type[BaseSkill]] = {}
        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._register_builtins()
    
    def _register_builtins(self):
        """注册内置 Skills（从 skills/ 目录 + 代码内置类）"""
        builtin_skills = []
        try:
            from .knowledge_skill import KnowledgeSkill
            builtin_skills.append(KnowledgeSkill())
        except Exception: pass
        try:
            from .coding_skill import CodingSkill
            builtin_skills.append(CodingSkill())
        except Exception: pass
        try:
            from .ppt_skill import PPTSkill
            builtin_skills.append(PPTSkill())
        except Exception: pass
        try:
            from .evaluation_skill import EvaluationSkill
            builtin_skills.append(EvaluationSkill())
        except Exception: pass
        try:
            from .file_skill import FileSkill
            builtin_skills.append(FileSkill())
        except Exception: pass
        try:
            from .format_skill import FormatSkill
            builtin_skills.append(FormatSkill())
        except Exception: pass
        try:
            from .persona_skill import PersonaSkill
            builtin_skills.append(PersonaSkill())
        except Exception: pass
        try:
            from .content_convert_skill import ContentConvertSkill
            builtin_skills.append(ContentConvertSkill())
        except Exception: pass
        
        for skill in builtin_skills:
            self.register(skill)
    
    def register(self, skill: BaseSkill) -> None:
        """
        注册 Skill 实例
        
        Args:
            skill: Skill 实例
        """
        metadata = skill.metadata
        self._skills[metadata.name] = skill
        self._metadata_cache[metadata.name] = metadata
    
    def register_class(self, skill_class: Type[BaseSkill]) -> None:
        """
        注册 Skill 类
        
        Args:
            skill_class: Skill 类
        """
        # 创建临时实例获取元数据
        temp_instance = skill_class()
        metadata = temp_instance.metadata
        self._skill_classes[metadata.name] = skill_class
    
    def unregister(self, name: str) -> None:
        """
        注销 Skill
        
        Args:
            name: Skill 名称
        """
        if name in self._skills:
            del self._skills[name]
        if name in self._skill_classes:
            del self._skill_classes[name]
        if name in self._metadata_cache:
            del self._metadata_cache[name]
    
    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """
        获取 Skill 实例
        
        Args:
            name: Skill 名称
        
        Returns:
            BaseSkill: Skill 实例
        """
        return self._skills.get(name)
    
    def get_skill_class(self, name: str) -> Optional[Type[BaseSkill]]:
        """
        获取 Skill 类
        
        Args:
            name: Skill 名称
        
        Returns:
            Type[BaseSkill]: Skill 类
        """
        return self._skill_classes.get(name)
    
    def create_skill(self, name: str, config: Dict[str, Any] = None) -> Optional[BaseSkill]:
        """
        创建 Skill 实例
        
        Args:
            name: Skill 名称
            config: 配置
        
        Returns:
            BaseSkill: Skill 实例
        """
        skill_class = self.get_skill_class(name)
        if skill_class:
            skill = skill_class(config)
            self.register(skill)
            return skill
        return None
    
    def list_skills(self) -> List[str]:
        """列出所有 Skill 名称"""
        return list(set(list(self._skills.keys()) + list(self._skill_classes.keys())))
    
    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        """获取 Skill 元数据"""
        return self._metadata_cache.get(name)
    
    def get_all_metadata(self) -> Dict[str, SkillMetadata]:
        """获取所有 Skill 元数据"""
        return self._metadata_cache.copy()
    
    def find_by_intent(self, intent: str) -> List[str]:
        """
        根据意图查找 Skill
        
        Args:
            intent: 意图
        
        Returns:
            List[str]: Skill 名称列表
        """
        result = []
        for name, metadata in self._metadata_cache.items():
            if intent in metadata.intents:
                result.append(name)
        return result
    
    def find_by_tag(self, tag: str) -> List[str]:
        """
        根据标签查找 Skill
        
        Args:
            tag: 标签
        
        Returns:
            List[str]: Skill 名称列表
        """
        result = []
        for name, metadata in self._metadata_cache.items():
            if tag in metadata.tags:
                result.append(name)
        return result
    
    def auto_discover(self, directory: str) -> None:
        """
        自动发现并注册 Skill
        
        Args:
            directory: Skill 目录
        """
        if not os.path.exists(directory):
            return
        
        for filename in os.listdir(directory):
            if filename.endswith('_skill.py'):
                module_name = filename[:-3]
                try:
                    # 动态导入模块
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        os.path.join(directory, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 查找 Skill 类
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseSkill) and 
                            obj != BaseSkill):
                            self.register_class(obj)
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")