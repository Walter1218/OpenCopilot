"""
Prompt模板管理工具

提供prompt模板的版本管理、优化迭代和效果评估功能
"""

import json
import os
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PromptVersion:
    """Prompt版本数据类"""
    version: str  # 版本号
    content: str  # prompt内容
    created_at: str  # 创建时间
    created_by: str  # 创建者
    description: str  # 版本描述
    evaluation_score: Optional[float] = None  # 评估分数
    metrics: Optional[Dict[str, Any]] = None  # 评估指标


@dataclass
class PromptTemplate:
    """Prompt模板数据类"""
    name: str  # 模板名称
    scene: str  # 场景类型
    current_version: str  # 当前版本
    versions: List[PromptVersion]  # 版本列表
    description: str  # 模板描述
    tags: List[str]  # 标签


class PromptManager:
    """Prompt模板管理器"""
    
    def __init__(self, storage_dir: str = "prompts"):
        """
        初始化管理器
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板"""
        for template_file in self.storage_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template = self._deserialize_template(data)
                    self.templates[template.name] = template
            except Exception as e:
                print(f"加载模板 {template_file} 失败: {e}")
    
    def _serialize_template(self, template: PromptTemplate) -> Dict[str, Any]:
        """
        序列化模板
        
        Args:
            template: PromptTemplate对象
            
        Returns:
            Dict: 序列化后的数据
        """
        return {
            "name": template.name,
            "scene": template.scene,
            "current_version": template.current_version,
            "versions": [
                {
                    "version": v.version,
                    "content": v.content,
                    "created_at": v.created_at,
                    "created_by": v.created_by,
                    "description": v.description,
                    "evaluation_score": v.evaluation_score,
                    "metrics": v.metrics
                }
                for v in template.versions
            ],
            "description": template.description,
            "tags": template.tags
        }
    
    def _deserialize_template(self, data: Dict[str, Any]) -> PromptTemplate:
        """
        反序列化模板
        
        Args:
            data: 模板数据
            
        Returns:
            PromptTemplate: 模板对象
        """
        versions = [
            PromptVersion(
                version=v["version"],
                content=v["content"],
                created_at=v["created_at"],
                created_by=v["created_by"],
                description=v["description"],
                evaluation_score=v.get("evaluation_score"),
                metrics=v.get("metrics")
            )
            for v in data.get("versions", [])
        ]
        
        return PromptTemplate(
            name=data["name"],
            scene=data["scene"],
            current_version=data["current_version"],
            versions=versions,
            description=data["description"],
            tags=data.get("tags", [])
        )
    
    def create_template(self, name: str, scene: str, content: str, 
                       description: str = "", tags: List[str] = None) -> PromptTemplate:
        """
        创建新模板
        
        Args:
            name: 模板名称
            scene: 场景类型
            content: prompt内容
            description: 模板描述
            tags: 标签列表
            
        Returns:
            PromptTemplate: 创建的模板
        """
        if name in self.templates:
            raise ValueError(f"模板 {name} 已存在")
        
        version = PromptVersion(
            version="1.0.0",
            content=content,
            created_at=datetime.now().isoformat(),
            created_by="system",
            description="初始版本"
        )
        
        template = PromptTemplate(
            name=name,
            scene=scene,
            current_version="1.0.0",
            versions=[version],
            description=description,
            tags=tags or []
        )
        
        self.templates[name] = template
        self._save_template(template)
        
        return template
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        获取模板
        
        Args:
            name: 模板名称
            
        Returns:
            Optional[PromptTemplate]: 模板对象
        """
        return self.templates.get(name)
    
    def get_current_prompt(self, name: str) -> Optional[str]:
        """
        获取当前版本的prompt
        
        Args:
            name: 模板名称
            
        Returns:
            Optional[str]: prompt内容
        """
        template = self.get_template(name)
        if not template:
            return None
        
        for version in template.versions:
            if version.version == template.current_version:
                return version.content
        
        return None
    
    def update_template(self, name: str, content: str, 
                       description: str = "", 
                       evaluation_score: float = None,
                       metrics: Dict[str, Any] = None) -> PromptVersion:
        """
        更新模板（创建新版本）
        
        Args:
            name: 模板名称
            content: 新的prompt内容
            description: 版本描述
            evaluation_score: 评估分数
            metrics: 评估指标
            
        Returns:
            PromptVersion: 新版本
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"模板 {name} 不存在")
        
        # 生成新版本号
        current_version = template.current_version
        version_parts = current_version.split('.')
        new_minor = int(version_parts[1]) + 1
        new_version = f"{version_parts[0]}.{new_minor}.0"
        
        # 创建新版本
        new_version_obj = PromptVersion(
            version=new_version,
            content=content,
            created_at=datetime.now().isoformat(),
            created_by="system",
            description=description,
            evaluation_score=evaluation_score,
            metrics=metrics
        )
        
        # 更新模板
        template.versions.append(new_version_obj)
        template.current_version = new_version
        
        # 保存模板
        self._save_template(template)
        
        return new_version_obj
    
    def get_version(self, name: str, version: str) -> Optional[PromptVersion]:
        """
        获取指定版本
        
        Args:
            name: 模板名称
            version: 版本号
            
        Returns:
            Optional[PromptVersion]: 版本对象
        """
        template = self.get_template(name)
        if not template:
            return None
        
        for v in template.versions:
            if v.version == version:
                return v
        
        return None
    
    def rollback_version(self, name: str, target_version: str) -> bool:
        """
        回滚到指定版本
        
        Args:
            name: 模板名称
            target_version: 目标版本号
            
        Returns:
            bool: 是否成功
        """
        template = self.get_template(name)
        if not template:
            return False
        
        # 检查目标版本是否存在
        target_exists = any(v.version == target_version for v in template.versions)
        if not target_exists:
            return False
        
        # 更新当前版本
        template.current_version = target_version
        
        # 保存模板
        self._save_template(template)
        
        return True
    
    def list_templates(self, scene: str = None, tags: List[str] = None) -> List[PromptTemplate]:
        """
        列出模板
        
        Args:
            scene: 场景类型（可选）
            tags: 标签列表（可选）
            
        Returns:
            List[PromptTemplate]: 模板列表
        """
        templates = list(self.templates.values())
        
        if scene:
            templates = [t for t in templates if t.scene == scene]
        
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        return templates
    
    def search_templates(self, keyword: str) -> List[PromptTemplate]:
        """
        搜索模板
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[PromptTemplate]: 匹配的模板列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        for template in self.templates.values():
            # 搜索名称、描述、标签
            if (keyword_lower in template.name.lower() or
                keyword_lower in template.description.lower() or
                any(keyword_lower in tag.lower() for tag in template.tags)):
                results.append(template)
                continue
            
            # 搜索prompt内容
            current_prompt = self.get_current_prompt(template.name)
            if current_prompt and keyword_lower in current_prompt.lower():
                results.append(template)
        
        return results
    
    def _save_template(self, template: PromptTemplate):
        """
        保存模板到文件
        
        Args:
            template: 模板对象
        """
        file_path = self.storage_dir / f"{template.name}.json"
        data = self._serialize_template(template)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def delete_template(self, name: str) -> bool:
        """
        删除模板
        
        Args:
            name: 模板名称
            
        Returns:
            bool: 是否成功
        """
        if name not in self.templates:
            return False
        
        # 删除文件
        file_path = self.storage_dir / f"{name}.json"
        if file_path.exists():
            file_path.unlink()
        
        # 从内存中删除
        del self.templates[name]
        
        return True
    
    def export_template(self, name: str, format: str = "json") -> Optional[str]:
        """
        导出模板
        
        Args:
            name: 模板名称
            format: 导出格式（json, md）
            
        Returns:
            Optional[str]: 导出内容
        """
        template = self.get_template(name)
        if not template:
            return None
        
        if format == "json":
            return json.dumps(self._serialize_template(template), 
                            ensure_ascii=False, indent=2)
        elif format == "md":
            return self._template_to_markdown(template)
        
        return None
    
    def _template_to_markdown(self, template: PromptTemplate) -> str:
        """
        将模板转换为Markdown格式
        
        Args:
            template: 模板对象
            
        Returns:
            str: Markdown内容
        """
        current_prompt = self.get_current_prompt(template.name)
        
        md = f"# {template.name}\n\n"
        md += f"**场景**: {template.scene}\n"
        md += f"**当前版本**: {template.current_version}\n"
        md += f"**描述**: {template.description}\n"
        md += f"**标签**: {', '.join(template.tags)}\n\n"
        
        md += "## 当前Prompt\n\n"
        md += f"```\n{current_prompt}\n```\n\n"
        
        md += "## 版本历史\n\n"
        md += "| 版本 | 创建时间 | 描述 | 评估分数 |\n"
        md += "|------|----------|------|----------|\n"
        
        for version in template.versions:
            score = f"{version.evaluation_score:.1f}" if version.evaluation_score else "N/A"
            md += f"| {version.version} | {version.created_at} | {version.description} | {score} |\n"
        
        return md
    
    def import_template(self, content: str, format: str = "json") -> Optional[PromptTemplate]:
        """
        导入模板
        
        Args:
            content: 模板内容
            format: 导入格式（json）
            
        Returns:
            Optional[PromptTemplate]: 导入的模板
        """
        if format == "json":
            try:
                data = json.loads(content)
                template = self._deserialize_template(data)
                
                # 检查是否已存在
                if template.name in self.templates:
                    raise ValueError(f"模板 {template.name} 已存在")
                
                self.templates[template.name] = template
                self._save_template(template)
                
                return template
            except json.JSONDecodeError:
                return None
        
        return None


class PromptOptimizer:
    """Prompt优化器"""
    
    def __init__(self, prompt_manager: PromptManager):
        """
        初始化优化器
        
        Args:
            prompt_manager: Prompt管理器
        """
        self.prompt_manager = prompt_manager
        self.optimization_rules = self._load_optimization_rules()
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """
        加载优化规则
        
        Returns:
            Dict: 优化规则
        """
        return {
            "fluency": {
                "patterns": [
                    (r'(?i)very|extremely|非常', "过度修饰"),
                    (r'(?i)basically|基本上', "模糊表达"),
                ],
                "suggestions": [
                    "使用更精确的形容词",
                    "避免过度修饰",
                    "使用具体数据替代模糊描述"
                ]
            },
            "tone": {
                "patterns": [
                    (r'(?i)hi|hello|hey', "非正式称呼"),
                    (r'(?i)ok|okay', "非正式确认"),
                ],
                "suggestions": [
                    "使用正式称呼",
                    "使用专业术语",
                    "保持语气一致"
                ]
            },
            "accuracy": {
                "patterns": [
                    (r'(?i)maybe|perhaps|可能', "不确定表达"),
                    (r'(?i)approximately|大约', "模糊数据"),
                ],
                "suggestions": [
                    "使用确定性表达",
                    "提供准确数据",
                    "添加数据来源"
                ]
            }
        }
    
    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        分析prompt
        
        Args:
            prompt: prompt内容
            
        Returns:
            Dict: 分析结果
        """
        analysis = {
            "length": len(prompt),
            "structure": self._analyze_structure(prompt),
            "language": self._analyze_language(prompt),
            "issues": self._find_issues(prompt)
        }
        
        return analysis
    
    def _analyze_structure(self, prompt: str) -> Dict[str, Any]:
        """
        分析prompt结构
        
        Args:
            prompt: prompt内容
            
        Returns:
            Dict: 结构分析
        """
        lines = prompt.split('\n')
        
        return {
            "total_lines": len(lines),
            "non_empty_lines": len([l for l in lines if l.strip()]),
            "sections": len(re.findall(r'^#+\s', prompt, re.MULTILINE)),
            "bullet_points": len(re.findall(r'^[-*]\s', prompt, re.MULTILINE)),
            "code_blocks": len(re.findall(r'```', prompt))
        }
    
    def _analyze_language(self, prompt: str) -> Dict[str, Any]:
        """
        分析语言特征
        
        Args:
            prompt: prompt内容
            
        Returns:
            Dict: 语言分析
        """
        # 中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', prompt))
        
        # 英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', prompt))
        
        # 平均句子长度
        sentences = re.split(r'[。！？.!?]', prompt)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        
        return {
            "chinese_chars": chinese_chars,
            "english_words": english_words,
            "total_chars": len(prompt),
            "avg_sentence_length": avg_sentence_length,
            "sentence_count": len(sentences)
        }
    
    def _find_issues(self, prompt: str) -> List[Dict[str, str]]:
        """
        查找prompt问题
        
        Args:
            prompt: prompt内容
            
        Returns:
            List: 问题列表
        """
        issues = []
        
        # 检查常见问题
        issue_patterns = [
            (r'(?i)please note that', "冗余表达", "建议直接说明要求"),
            (r'(?i)it is important to', "冗余表达", "建议直接强调重要性"),
            (r'(?i)make sure to', "冗余表达", "建议直接说明要求"),
            (r'(?i)you should', "命令式表达", "建议使用更礼貌的表达"),
            (r'(?i)you must', "强制性表达", "建议使用更委婉的表达"),
        ]
        
        for pattern, issue_type, suggestion in issue_patterns:
            if re.search(pattern, prompt):
                issues.append({
                    "type": issue_type,
                    "suggestion": suggestion,
                    "location": "全文"
                })
        
        return issues
    
    def optimize_prompt(self, prompt: str, evaluation_score: float = None) -> str:
        """
        优化prompt
        
        Args:
            prompt: 原始prompt
            evaluation_score: 评估分数（可选）
            
        Returns:
            str: 优化后的prompt
        """
        optimized = prompt
        
        # 应用优化规则
        for dimension, rules in self.optimization_rules.items():
            for pattern, description in rules["patterns"]:
                if re.search(pattern, optimized):
                    # 根据问题类型进行优化
                    if dimension == "fluency":
                        optimized = self._optimize_fluency(optimized)
                    elif dimension == "tone":
                        optimized = self._optimize_tone(optimized)
                    elif dimension == "accuracy":
                        optimized = self._optimize_accuracy(optimized)
        
        # 添加结构优化
        optimized = self._optimize_structure(optimized)
        
        return optimized
    
    def _optimize_fluency(self, prompt: str) -> str:
        """
        优化流畅性
        
        Args:
            prompt: 原始prompt
            
        Returns:
            str: 优化后的prompt
        """
        # 移除英文冗余修饰词
        redundant_words = ['very', 'extremely', 'really', 'quite', 'rather']
        for word in redundant_words:
            prompt = re.sub(rf'\b{word}\b', '', prompt, flags=re.IGNORECASE)
        
        # 移除中文冗余修饰词
        chinese_redundant = ['非常', '十分', '特别', '极其', '相当', '很']
        for word in chinese_redundant:
            # 处理重复修饰词，如"非常非常"
            prompt = re.sub(rf'{word}{word}', word, prompt)
            # 处理单个修饰词
            prompt = re.sub(rf'{word}', '', prompt)
        
        # 简化复杂句子
        prompt = re.sub(r'It is important to note that', '', prompt, flags=re.IGNORECASE)
        prompt = re.sub(r'Please note that', '', prompt, flags=re.IGNORECASE)
        
        return prompt
    
    def _optimize_tone(self, prompt: str) -> str:
        """
        优化语气
        
        Args:
            prompt: 原始prompt
            
        Returns:
            str: 优化后的prompt
        """
        # 替换非正式表达
        replacements = [
            (r'\bhi\b', '您好', re.IGNORECASE),
            (r'\bhello\b', '您好', re.IGNORECASE),
            (r'\bok\b', '好的', re.IGNORECASE),
            (r'\bokay\b', '好的', re.IGNORECASE),
        ]
        
        for pattern, replacement, flags in replacements:
            prompt = re.sub(pattern, replacement, prompt, flags=flags)
        
        return prompt
    
    def _optimize_accuracy(self, prompt: str) -> str:
        """
        优化准确性
        
        Args:
            prompt: 原始prompt
            
        Returns:
            str: 优化后的prompt
        """
        # 移除英文不确定表达
        english_uncertain = ['maybe', 'perhaps', 'approximately', 'about', 'around']
        for word in english_uncertain:
            prompt = re.sub(rf'\b{word}\b', '', prompt, flags=re.IGNORECASE)
        
        # 移除中文不确定表达
        chinese_uncertain = ['可能', '也许', '或许', '大概', '大约', '左右', '约']
        for word in chinese_uncertain:
            prompt = re.sub(rf'{word}', '', prompt)
        
        # 清理多余空格
        prompt = re.sub(r'\s+', ' ', prompt)
        prompt = prompt.strip()
        
        return prompt
    
    def _optimize_structure(self, prompt: str) -> str:
        """
        优化结构
        
        Args:
            prompt: 原始prompt
            
        Returns:
            str: 优化后的prompt
        """
        # 确保有清晰的段落分隔
        prompt = re.sub(r'\n{3,}', '\n\n', prompt)
        
        # 确保列表格式一致
        prompt = re.sub(r'^[-*]\s', '- ', prompt, flags=re.MULTILINE)
        
        return prompt
    
    def generate_optimization_report(self, original_prompt: str, 
                                   optimized_prompt: str) -> Dict[str, Any]:
        """
        生成优化报告
        
        Args:
            original_prompt: 原始prompt
            optimized_prompt: 优化后的prompt
            
        Returns:
            Dict: 优化报告
        """
        original_analysis = self.analyze_prompt(original_prompt)
        optimized_analysis = self.analyze_prompt(optimized_prompt)
        
        report = {
            "original": {
                "length": original_analysis["length"],
                "issues": len(original_analysis["issues"])
            },
            "optimized": {
                "length": optimized_analysis["length"],
                "issues": len(optimized_analysis["issues"])
            },
            "improvements": {
                "length_change": optimized_analysis["length"] - original_analysis["length"],
                "issues_fixed": len(original_analysis["issues"]) - len(optimized_analysis["issues"])
            }
        }
        
        return report


# 创建全局实例
prompt_manager = PromptManager()
prompt_optimizer = PromptOptimizer(prompt_manager)


def create_prompt_template(name: str, scene: str, content: str, 
                          description: str = "", tags: List[str] = None) -> PromptTemplate:
    """
    创建prompt模板
    
    Args:
        name: 模板名称
        scene: 场景类型
        content: prompt内容
        description: 模板描述
        tags: 标签列表
        
    Returns:
        PromptTemplate: 创建的模板
    """
    return prompt_manager.create_template(name, scene, content, description, tags)


def get_prompt_template(name: str) -> Optional[PromptTemplate]:
    """
    获取prompt模板
    
    Args:
        name: 模板名称
        
    Returns:
        Optional[PromptTemplate]: 模板对象
    """
    return prompt_manager.get_template(name)


def update_prompt_template(name: str, content: str, 
                          description: str = "",
                          evaluation_score: float = None) -> PromptVersion:
    """
    更新prompt模板
    
    Args:
        name: 模板名称
        content: 新的prompt内容
        description: 版本描述
        evaluation_score: 评估分数
        
    Returns:
        PromptVersion: 新版本
    """
    return prompt_manager.update_template(name, content, description, evaluation_score)


def optimize_prompt(prompt: str) -> str:
    """
    优化prompt
    
    Args:
        prompt: 原始prompt
        
    Returns:
        str: 优化后的prompt
    """
    return prompt_optimizer.optimize_prompt(prompt)


def analyze_prompt(prompt: str) -> Dict[str, Any]:
    """
    分析prompt
    
    Args:
        prompt: prompt内容
        
    Returns:
        Dict: 分析结果
    """
    return prompt_optimizer.analyze_prompt(prompt)


# 工具注册信息
TOOL_INFO = {
    "name": "prompt_management",
    "description": "Prompt模板管理工具",
    "parameters": {
        "action": {
            "type": "string",
            "description": "操作类型（create, get, update, optimize, analyze）",
            "required": True
        },
        "name": {
            "type": "string",
            "description": "模板名称",
            "required": False
        },
        "scene": {
            "type": "string",
            "description": "场景类型",
            "required": False
        },
        "content": {
            "type": "string",
            "description": "prompt内容",
            "required": False
        },
        "description": {
            "type": "string",
            "description": "模板描述",
            "required": False
        },
        "tags": {
            "type": "array",
            "description": "标签列表",
            "required": False
        }
    }
}