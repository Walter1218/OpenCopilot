# Skill 化架构设计方案

> **版本**: 1.0.0
> **日期**: 2026-05-31
> **定位**: 模块化、可组合、可扩展的能力平台
> **核心特性**: 统一接口 + 自动发现 + 意图路由

## 1. 设计目标

### 1.1 解决的核心问题

| 问题 | 当前状态 | Skill 化解决后 |
|------|----------|----------------|
| **模块耦合度高** | 功能分散在 `ppt_cocreation/`、`knowledge_graph/`、`tools/` 等目录，相互依赖 | 每个 Skill 独立封装，通过标准接口交互 |
| **扩展性差** | 新增功能需修改多个文件，牵一发而动全身 | 新功能 = 新 Skill，无需修改核心系统 |
| **缺乏统一抽象** | 各模块接口不一致，难以复用 | BaseSkill 统一接口，所有 Skill 一脉相承 |
| **功能组合困难** | 无法将多个功能组合使用 | SkillExecutor 支持多 Skill 组合执行 |
| **意图识别分散** | 各模块各自处理用户意图，缺乏全局路由 | 全局意图路由器，自动选择最佳 Skill |

### 1.2 设计原则

1. **单一职责**：每个 Skill 只做一件事，做好一件事
2. **开闭原则**：对扩展开放，对修改关闭
3. **依赖倒置**：依赖抽象接口，不依赖具体实现
4. **接口隔离**：客户端不应依赖它不需要的接口
5. **组合优于继承**：通过组合实现复杂功能

### 1.3 成功指标

- 新功能开发时间减少 50%
- 代码复用率提升 70%
- 系统可维护性提升 60%
- 测试覆盖率提升 80%

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户请求/事件                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Intent Router (意图路由)                    │
├─────────────────────────────────────────────────────────────┤
│  - 意图识别                                                  │
│  - Skill 选择                                               │
│  - 优先级排序                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Skill Executor (执行引擎)                   │
├─────────────────────────────────────────────────────────────┤
│  - 单 Skill 执行                                            │
│  - 多 Skill 组合执行                                         │
│  - 并行/串行控制                                            │
│  - 错误处理和重试                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Skill Registry (注册表)                     │
├─────────────────────────────────────────────────────────────┤
│  - Skill 注册/注销                                          │
│  - 自动发现                                                 │
│  - 依赖管理                                                 │
│  - 配置管理                                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      具体 Skill 实现                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PPT Skill    │  │ Knowledge    │  │ File Skill   │      │
│  │              │  │ Graph Skill  │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Evaluation   │  │ Coding Agent │  │ Custom Skill │      │
│  │ Skill        │  │ Skill        │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

```python
# skill_architecture/
# ├── __init__.py
# ├── base.py              # 核心基类
# ├── registry.py          # 注册表
# ├── executor.py          # 执行引擎
# ├── router.py            # 意图路由
# ├── discovery.py         # 自动发现
# ├── config.py            # 配置管理
# ├── models.py            # 数据模型
# └── skills/              # 具体 Skill 实现
#     ├── __init__.py
#     ├── ppt_skill.py
#     ├── knowledge_skill.py
#     ├── file_skill.py
#     ├── evaluation_skill.py
#     └── coding_skill.py
```

---

## 3. 核心组件设计

### 3.1 数据模型 (models.py)

```python
# skill_architecture/models.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class SkillStatus(Enum):
    """Skill 状态"""
    INITIALIZED = "initialized"      # 已初始化
    RUNNING = "running"              # 运行中
    COMPLETED = "completed"          # 已完成
    FAILED = "failed"                # 失败
    CANCELLED = "cancelled"          # 已取消


class ExecutionMode(Enum):
    """执行模式"""
    SINGLE = "single"                # 单 Skill 执行
    SEQUENTIAL = "sequential"        # 顺序执行多个 Skill
    PARALLEL = "parallel"            # 并行执行多个 Skill
    PIPELINE = "pipeline"            # 流水线执行


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str                        # Skill 名称
    version: str                     # 版本号
    description: str                 # 描述
    author: str = ""                 # 作者
    tags: List[str] = field(default_factory=list)  # 标签
    intents: List[str] = field(default_factory=list)  # 支持的意图
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他 Skill
    config_schema: Dict[str, Any] = field(default_factory=dict)  # 配置模式
    input_schema: Dict[str, Any] = field(default_factory=dict)   # 输入模式
    output_schema: Dict[str, Any] = field(default_factory=dict)  # 输出模式


@dataclass
class SkillContext:
    """Skill 执行上下文"""
    intent: str                      # 用户意图
    input_data: Dict[str, Any]       # 输入数据
    config: Dict[str, Any] = field(default_factory=dict)  # 配置
    session_id: Optional[str] = None  # 会话 ID
    user_id: Optional[str] = None     # 用户 ID
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    chain_results: List[Dict[str, Any]] = field(default_factory=list)  # 链式执行结果


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool                    # 是否成功
    data: Dict[str, Any]             # 结果数据
    error: Optional[str] = None      # 错误信息
    status: SkillStatus = SkillStatus.COMPLETED  # 状态
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    next_skills: List[str] = field(default_factory=list)  # 建议的下一步 Skill


@dataclass
class ExecutionPlan:
    """执行计划"""
    mode: ExecutionMode              # 执行模式
    skills: List[str]                # 要执行的 Skill 列表
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # 依赖关系
    parallel_groups: List[List[str]] = field(default_factory=list)  # 并行组
    timeout: int = 30                # 超时时间（秒）
    retry_count: int = 3             # 重试次数
```

### 3.2 核心基类 (base.py)

```python
# skill_architecture/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from .models import SkillMetadata, SkillContext, SkillResult, SkillStatus


class BaseSkill(ABC):
    """Skill 基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 Skill
        
        Args:
            config: 配置字典
        """
        self._config = config or {}
        self._status = SkillStatus.INITIALIZED
        self._validate_config()
    
    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """获取 Skill 元数据"""
        pass
    
    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        执行 Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        pass
    
    async def can_handle(self, context: SkillContext) -> float:
        """
        判断是否能处理该上下文
        
        Args:
            context: 执行上下文
        
        Returns:
            float: 置信度 (0-1)
        """
        # 默认实现：检查意图是否匹配
        if context.intent in self.metadata.intents:
            return 0.8
        return 0.0
    
    async def initialize(self) -> bool:
        """
        初始化 Skill（异步）
        
        Returns:
            bool: 是否成功
        """
        return True
    
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    def _validate_config(self) -> None:
        """验证配置"""
        # 子类可以覆盖此方法进行配置验证
        pass
    
    @property
    def status(self) -> SkillStatus:
        """获取状态"""
        return self._status
    
    @status.setter
    def status(self, value: SkillStatus) -> None:
        """设置状态"""
        self._status = value
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._validate_config()
```

### 3.3 注册表 (registry.py)

```python
# skill_architecture/registry.py

import os
import importlib
import inspect
from typing import Dict, List, Optional, Type
from .base import BaseSkill
from .models import SkillMetadata


class SkillRegistry:
    """Skill 注册表"""
    
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._skill_classes: Dict[str, Type[BaseSkill]] = {}
        self._metadata_cache: Dict[str, SkillMetadata] = {}
    
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
```

### 3.4 意图路由 (router.py)

```python
# skill_architecture/router.py

from typing import Dict, List, Optional, Tuple
from .base import BaseSkill
from .registry import SkillRegistry
from .models import SkillContext


class IntentRouter:
    """意图路由器"""
    
    def __init__(self, registry: SkillRegistry):
        self._registry = registry
        self._intent_cache: Dict[str, List[str]] = {}
    
    async def route(self, context: SkillContext) -> Optional[str]:
        """
        路由到最合适的 Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            str: Skill 名称，如果没有找到返回 None
        """
        # 1. 根据意图查找候选 Skill
        candidates = self._find_candidates(context)
        
        if not candidates:
            return None
        
        # 2. 计算每个候选 Skill 的置信度
        scored_candidates = await self._score_candidates(context, candidates)
        
        # 3. 选择置信度最高的 Skill
        if scored_candidates:
            best_skill, best_score = max(scored_candidates, key=lambda x: x[1])
            if best_score > 0.3:  # 最低置信度阈值
                return best_skill
        
        return None
    
    async def route_multiple(self, context: SkillContext, max_skills: int = 3) -> List[Tuple[str, float]]:
        """
        路由到多个 Skill（用于组合执行）
        
        Args:
            context: 执行上下文
            max_skills: 最大 Skill 数量
        
        Returns:
            List[Tuple[str, float]]: (Skill 名称, 置信度) 列表
        """
        # 1. 根据意图查找候选 Skill
        candidates = self._find_candidates(context)
        
        if not candidates:
            return []
        
        # 2. 计算每个候选 Skill 的置信度
        scored_candidates = await self._score_candidates(context, candidates)
        
        # 3. 按置信度排序，返回前 N 个
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:max_skills]
    
    def _find_candidates(self, context: SkillContext) -> List[str]:
        """查找候选 Skill"""
        # 1. 精确意图匹配
        candidates = self._registry.find_by_intent(context.intent)
        
        if candidates:
            return candidates
        
        # 2. 模糊匹配（基于标签）
        # 提取意图中的关键词作为标签
        keywords = context.intent.split('_')
        for keyword in keywords:
            tag_matches = self._registry.find_by_tag(keyword)
            candidates.extend(tag_matches)
        
        return list(set(candidates))
    
    async def _score_candidates(
        self, 
        context: SkillContext, 
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """计算候选 Skill 的置信度"""
        scored = []
        
        for skill_name in candidates:
            skill = self._registry.get_skill(skill_name)
            if skill:
                try:
                    score = await skill.can_handle(context)
                    scored.append((skill_name, score))
                except Exception:
                    # 如果 can_handle 抛出异常，给低分
                    scored.append((skill_name, 0.1))
        
        return scored
    
    def add_intent_mapping(self, intent: str, skills: List[str]) -> None:
        """
        添加意图映射
        
        Args:
            intent: 意图
            skills: Skill 名称列表
        """
        self._intent_cache[intent] = skills
    
    def get_intent_mapping(self, intent: str) -> List[str]:
        """获取意图映射"""
        return self._intent_cache.get(intent, [])
```

### 3.5 执行引擎 (executor.py)

```python
# skill_architecture/executor.py

import asyncio
from typing import Dict, List, Optional, Any
from .base import BaseSkill
from .registry import SkillRegistry
from .router import IntentRouter
from .models import (
    SkillContext, SkillResult, SkillStatus,
    ExecutionPlan, ExecutionMode
)


class SkillExecutor:
    """Skill 执行引擎"""
    
    def __init__(self, registry: SkillRegistry, router: IntentRouter):
        self._registry = registry
        self._router = router
        self._execution_history: List[Dict[str, Any]] = []
    
    async def execute(
        self,
        context: SkillContext,
        skill_name: Optional[str] = None
    ) -> SkillResult:
        """
        执行单个 Skill
        
        Args:
            context: 执行上下文
            skill_name: 指定的 Skill 名称（可选）
        
        Returns:
            SkillResult: 执行结果
        """
        # 1. 确定要执行的 Skill
        if skill_name:
            skill = self._registry.get_skill(skill_name)
            if not skill:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Skill not found: {skill_name}",
                    status=SkillStatus.FAILED
                )
        else:
            # 自动路由
            routed_name = await self._router.route(context)
            if not routed_name:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"No skill found for intent: {context.intent}",
                    status=SkillStatus.FAILED
                )
            skill = self._registry.get_skill(routed_name)
        
        # 2. 执行 Skill
        try:
            skill.status = SkillStatus.RUNNING
            result = await asyncio.wait_for(
                skill.execute(context),
                timeout=30  # 默认超时 30 秒
            )
            skill.status = SkillStatus.COMPLETED
            
            # 记录执行历史
            self._record_execution(skill.metadata.name, context, result)
            
            return result
        except asyncio.TimeoutError:
            skill.status = SkillStatus.FAILED
            return SkillResult(
                success=False,
                data={},
                error="Execution timeout",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            skill.status = SkillStatus.FAILED
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
            )
    
    async def execute_chain(
        self,
        context: SkillContext,
        skill_names: List[str]
    ) -> SkillResult:
        """
        链式执行多个 Skill
        
        Args:
            context: 执行上下文
            skill_names: Skill 名称列表
        
        Returns:
            SkillResult: 最后一个 Skill 的执行结果
        """
        if not skill_names:
            return SkillResult(
                success=False,
                data={},
                error="No skills specified",
                status=SkillStatus.FAILED
            )
        
        current_context = context
        last_result = None
        
        for skill_name in skill_names:
            skill = self._registry.get_skill(skill_name)
            if not skill:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Skill not found: {skill_name}",
                    status=SkillStatus.FAILED
                )
            
            # 执行当前 Skill
            result = await self.execute(current_context, skill_name)
            
            if not result.success:
                return result
            
            # 将结果添加到链式结果中
            current_context.chain_results.append({
                "skill": skill_name,
                "result": result.data
            })
            
            # 更新上下文数据，供下一个 Skill 使用
            current_context.input_data.update(result.data)
            last_result = result
        
        return last_result or SkillResult(
            success=False,
            data={},
            error="No skills executed",
            status=SkillStatus.FAILED
        )
    
    async def execute_parallel(
        self,
        context: SkillContext,
        skill_names: List[str]
    ) -> Dict[str, SkillResult]:
        """
        并行执行多个 Skill
        
        Args:
            context: 执行上下文
            skill_names: Skill 名称列表
        
        Returns:
            Dict[str, SkillResult]: 每个 Skill 的执行结果
        """
        tasks = {}
        
        for skill_name in skill_names:
            skill = self._registry.get_skill(skill_name)
            if skill:
                tasks[skill_name] = self.execute(context, skill_name)
        
        if not tasks:
            return {}
        
        # 并行执行
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )
        
        # 组织结果
        result_dict = {}
        for skill_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                result_dict[skill_name] = SkillResult(
                    success=False,
                    data={},
                    error=str(result),
                    status=SkillStatus.FAILED
                )
            else:
                result_dict[skill_name] = result
        
        return result_dict
    
    async def execute_plan(
        self,
        context: SkillContext,
        plan: ExecutionPlan
    ) -> Dict[str, SkillResult]:
        """
        根据执行计划执行
        
        Args:
            context: 执行上下文
            plan: 执行计划
        
        Returns:
            Dict[str, SkillResult]: 执行结果
        """
        if plan.mode == ExecutionMode.SINGLE:
            if plan.skills:
                result = await self.execute(context, plan.skills[0])
                return {plan.skills[0]: result}
            return {}
        
        elif plan.mode == ExecutionMode.SEQUENTIAL:
            result = await self.execute_chain(context, plan.skills)
            return {plan.skills[-1]: result}
        
        elif plan.mode == ExecutionMode.PARALLEL:
            return await self.execute_parallel(context, plan.skills)
        
        elif plan.mode == ExecutionMode.PIPELINE:
            # 流水线执行：顺序执行，但每个 Skill 的输出作为下一个的输入
            return await self._execute_pipeline(context, plan)
        
        return {}
    
    async def _execute_pipeline(
        self,
        context: SkillContext,
        plan: ExecutionPlan
    ) -> Dict[str, SkillResult]:
        """流水线执行"""
        results = {}
        current_data = context.input_data.copy()
        
        for skill_name in plan.skills:
            skill = self._registry.get_skill(skill_name)
            if not skill:
                results[skill_name] = SkillResult(
                    success=False,
                    data={},
                    error=f"Skill not found: {skill_name}",
                    status=SkillStatus.FAILED
                )
                break
            
            # 创建新的上下文，使用当前数据
            pipeline_context = SkillContext(
                intent=context.intent,
                input_data=current_data,
                config=context.config,
                session_id=context.session_id,
                user_id=context.user_id,
                metadata=context.metadata,
                chain_results=context.chain_results
            )
            
            # 执行 Skill
            result = await self.execute(pipeline_context, skill_name)
            results[skill_name] = result
            
            if not result.success:
                break
            
            # 更新数据，供下一个 Skill 使用
            current_data.update(result.data)
            context.chain_results.append({
                "skill": skill_name,
                "result": result.data
            })
        
        return results
    
    def _record_execution(
        self,
        skill_name: str,
        context: SkillContext,
        result: SkillResult
    ) -> None:
        """记录执行历史"""
        self._execution_history.append({
            "skill": skill_name,
            "intent": context.intent,
            "success": result.success,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # 只保留最近 100 条记录
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history.copy()
```

### 3.6 自动发现 (discovery.py)

```python
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
```

---

## 4. 具体 Skill 实现示例

### 4.1 文件处理 Skill

```python
# skill_architecture/skills/file_skill.py

from typing import Any, Dict, List
from ..base import BaseSkill
from ..models import SkillMetadata, SkillContext, SkillResult, SkillStatus


class FileSkill(BaseSkill):
    """文件处理 Skill"""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="file_skill",
            version="1.0.0",
            description="文件处理技能，支持读取、写入、转换文件",
            author="OpenCopilot",
            tags=["file", "read", "write", "convert"],
            intents=["file_read", "file_write", "file_convert"],
            dependencies=[],
            config_schema={
                "max_file_size": {
                    "type": "integer",
                    "description": "最大文件大小（字节）",
                    "default": 10485760  # 10MB
                }
            },
            input_schema={
                "file_path": {
                    "type": "string",
                    "description": "文件路径",
                    "required": True
                },
                "operation": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["read", "write", "convert"],
                    "required": True
                }
            },
            output_schema={
                "content": {
                    "type": "string",
                    "description": "文件内容"
                },
                "success": {
                    "type": "boolean",
                    "description": "是否成功"
                }
            }
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行文件操作"""
        try:
            operation = context.input_data.get("operation")
            file_path = context.input_data.get("file_path")
            
            if not file_path:
                return SkillResult(
                    success=False,
                    data={},
                    error="file_path is required",
                    status=SkillStatus.FAILED
                )
            
            if operation == "read":
                return await self._read_file(file_path)
            elif operation == "write":
                content = context.input_data.get("content", "")
                return await self._write_file(file_path, content)
            elif operation == "convert":
                output_format = context.input_data.get("output_format", "txt")
                return await self._convert_file(file_path, output_format)
            else:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Unknown operation: {operation}",
                    status=SkillStatus.FAILED
                )
        
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
            )
    
    async def _read_file(self, file_path: str) -> SkillResult:
        """读取文件"""
        import os
        import asyncio
        
        expanded_path = os.path.expanduser(file_path)
        
        if not os.path.exists(expanded_path):
            return SkillResult(
                success=False,
                data={},
                error=f"File not found: {file_path}",
                status=SkillStatus.FAILED
            )
        
        # 检查文件大小
        file_size = os.path.getsize(expanded_path)
        max_size = self.config.get("max_file_size", 10485760)
        
        if file_size > max_size:
            return SkillResult(
                success=False,
                data={},
                error=f"File too large: {file_size} bytes (max: {max_size})",
                status=SkillStatus.FAILED
            )
        
        # 读取文件
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, self._read_file_sync, expanded_path)
        
        return SkillResult(
            success=True,
            data={
                "content": content,
                "file_path": expanded_path,
                "file_size": file_size
            },
            status=SkillStatus.COMPLETED
        )
    
    def _read_file_sync(self, file_path: str) -> str:
        """同步读取文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def _write_file(self, file_path: str, content: str) -> SkillResult:
        """写入文件"""
        import os
        import asyncio
        
        expanded_path = os.path.expanduser(file_path)
        
        # 创建目录
        os.makedirs(os.path.dirname(expanded_path), exist_ok=True)
        
        # 写入文件
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_file_sync, expanded_path, content)
        
        return SkillResult(
            success=True,
            data={
                "file_path": expanded_path,
                "bytes_written": len(content.encode('utf-8'))
            },
            status=SkillStatus.COMPLETED
        )
    
    def _write_file_sync(self, file_path: str, content: str) -> None:
        """同步写入文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    async def _convert_file(self, file_path: str, output_format: str) -> SkillResult:
        """转换文件格式"""
        # 先读取文件
        read_result = await self._read_file(file_path)
        
        if not read_result.success:
            return read_result
        
        content = read_result.data.get("content", "")
        
        # 生成输出路径
        import os
        base_name = os.path.splitext(file_path)[0]
        output_path = f"{base_name}.{output_format}"
        
        # 写入新格式
        write_result = await self._write_file(output_path, content)
        
        if write_result.success:
            write_result.data["original_format"] = os.path.splitext(file_path)[1]
            write_result.data["output_format"] = output_format
        
        return write_result
```

### 4.2 评价 Skill

```python
# skill_architecture/skills/evaluation_skill.py

from typing import Any, Dict, List
from ..base import BaseSkill
from ..models import SkillMetadata, SkillContext, SkillResult, SkillStatus


class EvaluationSkill(BaseSkill):
    """评价 Skill"""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="evaluation_skill",
            version="1.0.0",
            description="内容质量评价技能",
            author="OpenCopilot",
            tags=["evaluation", "quality", "score"],
            intents=["evaluate", "quality_check", "score"],
            dependencies=[],
            config_schema={},
            input_schema={
                "content": {
                    "type": "string",
                    "description": "要评价的内容",
                    "required": True
                },
                "scene": {
                    "type": "string",
                    "description": "场景类型",
                    "enum": ["auto", "translate", "code", "polish", "revision", "custom"],
                    "required": True
                }
            },
            output_schema={
                "score": {
                    "type": "number",
                    "description": "评分"
                },
                "level": {
                    "type": "string",
                    "description": "等级"
                },
                "report": {
                    "type": "object",
                    "description": "详细报告"
                }
            }
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行评价"""
        try:
            # 导入评价工具
            from tools.evaluation_tools import OpenCopilotEvaluator
            
            content = context.input_data.get("content")
            scene = context.input_data.get("scene", "auto")
            
            if not content:
                return SkillResult(
                    success=False,
                    data={},
                    error="content is required",
                    status=SkillStatus.FAILED
                )
            
            # 执行评价
            evaluator = OpenCopilotEvaluator()
            report = evaluator.evaluate(
                scene=scene,
                input_text=context.input_data.get("input_text", ""),
                output_text=content,
                reference=context.input_data.get("reference"),
                instruction=context.input_data.get("instruction"),
                full_document=context.input_data.get("full_document")
            )
            
            return SkillResult(
                success=True,
                data={
                    "score": report.total_score,
                    "level": report.level,
                    "summary": report.summary,
                    "improvement_plan": report.improvement_plan,
                    "report": {
                        "scene": report.scene,
                        "scene_label": report.scene_label,
                        "results": [
                            {
                                "dimension": r.dimension,
                                "dimension_label": r.dimension_label,
                                "score": r.score,
                                "weight": r.weight,
                                "feedback": r.feedback,
                                "suggestions": r.suggestions
                            }
                            for r in report.results
                        ]
                    }
                },
                status=SkillStatus.COMPLETED
            )
        
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
            )
    
    async def can_handle(self, context: SkillContext) -> float:
        """判断是否能处理"""
        # 检查意图
        if context.intent in self.metadata.intents:
            return 0.9
        
        # 检查输入数据
        if "content" in context.input_data and "scene" in context.input_data:
            return 0.7
        
        return 0.0
```

---

## 5. 迁移路径

### 5.1 现有工具迁移

| 现有工具 | Skill 化方案 | 迁移步骤 |
|----------|-------------|----------|
| `FileReadTool` | `FileSkill` 的一部分 | 1. 创建 FileSkill<br>2. 将 FileReadTool 的逻辑移入<br>3. 更新调用方 |
| `FileWriteTool` | `FileSkill` 的一部分 | 同上 |
| `FileConvertTool` | `FileSkill` 的一部分 | 同上 |
| `MarkdownToDocxTool` | `FormatSkill` 的一部分 | 1. 创建 FormatSkill<br>2. 将转换逻辑移入 |
| `OpenCopilotEvaluator` | `EvaluationSkill` | 1. 创建 EvaluationSkill<br>2. 封装评价器 |
| `knowledge_graph/` | `KnowledgeSkill` | 1. 创建 KnowledgeSkill<br>2. 封装图查询功能 |
| `ppt_cocreation/` | `PPTSkill` | 1. 创建 PPTSkill<br>2. 封装 PPT 生成功能 |

### 5.2 迁移步骤

**阶段 1：基础设施（1-2 天）**
1. 创建 `skill_architecture/` 目录
2. 实现核心基类和接口
3. 实现注册表和执行引擎
4. 编写单元测试

**阶段 2：第一个 Skill（1-2 天）**
1. 将 `knowledge_graph/` 封装为 `KnowledgeSkill`
2. 实现自动发现机制
3. 集成到现有系统
4. 编写集成测试

**阶段 3：工具迁移（2-3 天）**
1. 将 `tools/` 中的工具逐个 Skill 化
2. 更新调用方代码
3. 确保向后兼容
4. 更新文档

**阶段 4：高级功能（2-3 天）**
1. 实现意图路由器
2. 实现组合执行
3. 实现配置管理
4. 性能优化

### 5.3 向后兼容策略

1. **适配器模式**：为现有工具创建适配器，使其符合 BaseSkill 接口
2. **渐进式迁移**：一次迁移一个模块，确保不影响现有功能
3. **双轨运行**：新旧系统并行运行，逐步切换
4. **功能开关**：使用配置开关控制新旧系统

---

## 6. 测试策略

### 6.1 单元测试

```python
# tests/test_skill_architecture.py

import pytest
from skill_architecture.base import BaseSkill
from skill_architecture.registry import SkillRegistry
from skill_architecture.router import IntentRouter
from skill_architecture.executor import SkillExecutor
from skill_architecture.models import SkillContext, SkillResult, SkillStatus


class MockSkill(BaseSkill):
    """模拟 Skill"""
    
    @property
    def metadata(self):
        from skill_architecture.models import SkillMetadata
        return SkillMetadata(
            name="mock_skill",
            version="1.0.0",
            description="Mock skill for testing",
            intents=["test", "mock"]
        )
    
    async def execute(self, context):
        return SkillResult(
            success=True,
            data={"result": "mock"},
            status=SkillStatus.COMPLETED
        )


class TestSkillRegistry:
    """注册表测试"""
    
    def test_register_skill(self):
        """测试注册 Skill"""
        registry = SkillRegistry()
        skill = MockSkill()
        registry.register(skill)
        
        assert "mock_skill" in registry.list_skills()
        assert registry.get_skill("mock_skill") == skill
    
    def test_unregister_skill(self):
        """测试注销 Skill"""
        registry = SkillRegistry()
        skill = MockSkill()
        registry.register(skill)
        registry.unregister("mock_skill")
        
        assert "mock_skill" not in registry.list_skills()
    
    def test_find_by_intent(self):
        """测试根据意图查找"""
        registry = SkillRegistry()
        skill = MockSkill()
        registry.register(skill)
        
        result = registry.find_by_intent("test")
        assert "mock_skill" in result


class TestIntentRouter:
    """意图路由测试"""
    
    @pytest.mark.asyncio
    async def test_route(self):
        """测试路由"""
        registry = SkillRegistry()
        skill = MockSkill()
        registry.register(skill)
        
        router = IntentRouter(registry)
        context = SkillContext(
            intent="test",
            input_data={}
        )
        
        result = await router.route(context)
        assert result == "mock_skill"


class TestSkillExecutor:
    """执行引擎测试"""
    
    @pytest.mark.asyncio
    async def test_execute(self):
        """测试执行"""
        registry = SkillRegistry()
        skill = MockSkill()
        registry.register(skill)
        
        router = IntentRouter(registry)
        executor = SkillExecutor(registry, router)
        
        context = SkillContext(
            intent="test",
            input_data={}
        )
        
        result = await executor.execute(context)
        assert result.success
        assert result.data["result"] == "mock"
```

### 6.2 集成测试

```python
# tests/test_skill_integration.py

import pytest
from skill_architecture.registry import SkillRegistry
from skill_architecture.router import IntentRouter
from skill_architecture.executor import SkillExecutor
from skill_architecture.discovery import SkillDiscovery
from skill_architecture.models import SkillContext


class TestSkillIntegration:
    """Skill 集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 创建注册表
        registry = SkillRegistry()
        
        # 2. 自动发现
        discovery = SkillDiscovery(registry)
        discovery.add_search_path("./skill_architecture/skills")
        discovered = discovery.discover_and_register()
        
        # 3. 创建路由器和执行器
        router = IntentRouter(registry)
        executor = SkillExecutor(registry, router)
        
        # 4. 执行测试
        context = SkillContext(
            intent="file_read",
            input_data={
                "file_path": "./test.txt",
                "operation": "read"
            }
        )
        
        result = await executor.execute(context)
        
        # 验证结果
        assert result is not None
        assert hasattr(result, 'success')
```

---

## 7. 部署与配置

### 7.1 配置文件

```yaml
# config/skill_config.yaml

skill_architecture:
  # 自动发现配置
  discovery:
    enabled: true
    paths:
      - "./skill_architecture/skills"
      - "./custom_skills"
    watch: true  # 监视目录变化
  
  # 执行引擎配置
  executor:
    default_timeout: 30
    max_parallel_skills: 5
    retry_count: 3
    retry_delay: 1
  
  # 路由配置
  router:
    min_confidence: 0.3
    max_candidates: 5
    cache_ttl: 300  # 缓存 TTL（秒）
  
  # 日志配置
  logging:
    level: "INFO"
    file: "./logs/skill_architecture.log"
    max_size: 10485760  # 10MB
    backup_count: 5
  
  # 监控配置
  monitoring:
    enabled: true
    metrics_port: 9090
    health_check_interval: 30
```

### 7.2 启动脚本

```python
# start_skill_architecture.py

import asyncio
import yaml
from skill_architecture.registry import SkillRegistry
from skill_architecture.router import IntentRouter
from skill_architecture.executor import SkillExecutor
from skill_architecture.discovery import SkillDiscovery


async def main():
    """启动 Skill 架构"""
    # 加载配置
    with open("./config/skill_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    skill_config = config.get("skill_architecture", {})
    
    # 创建注册表
    registry = SkillRegistry()
    
    # 自动发现
    discovery = SkillDiscovery(registry)
    discovery_config = skill_config.get("discovery", {})
    
    if discovery_config.get("enabled", True):
        for path in discovery_config.get("paths", []):
            discovery.add_search_path(path)
        
        discovered = discovery.discover_and_register()
        print(f"Discovered {len(discovered)} skills: {discovered}")
    
    # 创建路由器和执行器
    router = IntentRouter(registry)
    executor = SkillExecutor(registry, router)
    
    # 保存实例供外部使用
    import builtins
    builtins.skill_registry = registry
    builtins.skill_router = router
    builtins.skill_executor = executor
    
    print("Skill architecture started successfully")
    
    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 8. 总结

### 8.1 核心价值

1. **模块化**：复杂系统拆分为可管理的单元
2. **可组合**：像搭积木一样组合功能
3. **可扩展**：新功能 = 新 Skill，不改老代码
4. **标准化**：统一接口，降低认知负担
5. **可测试**：独立单元，质量有保障

### 8.2 差异化优势

- **vs 传统工具系统**：支持意图路由和组合执行
- **vs 微服务架构**：更轻量，适合本地应用
- **vs 插件系统**：更智能，支持自动发现和路由

### 8.3 预期效果

- 新功能开发时间减少 50%
- 代码复用率提升 70%
- 系统可维护性提升 60%
- 测试覆盖率提升 80%

### 8.4 后续规划

1. **Phase 1**：实现核心框架和第一个 Skill
2. **Phase 2**：迁移现有工具
3. **Phase 3**：实现高级功能（意图路由、组合执行）
4. **Phase 4**：性能优化和监控
5. **Phase 5**：文档和示例
