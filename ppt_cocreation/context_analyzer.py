"""
智能上下文感知模块

分析 PPT 的整体结构、内容类型、风格一致性等，为 AI 提供全局视野。
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    FLOWCHART = "flowchart"
    IMAGE = "image"
    LIST = "list"
    DATA_COMPARISON = "data_comparison"
    TIME_SERIES = "time_series"
    PROCESS = "process"
    PERSON_ATTRIBUTES = "person_attributes"


class SuggestionType(str, Enum):
    """建议类型"""
    CONTENT_OPTIMIZE = "content_optimize"  # 内容优化
    VISUAL_ENHANCE = "visual_enhance"      # 视觉增强
    STRUCTURE_IMPROVE = "structure_improve" # 结构改进
    STYLE_CONSISTENT = "style_consistent"  # 风格一致


@dataclass
class ContentAnalysis:
    """内容分析结果"""
    content_type: ContentType
    confidence: float
    key_points: List[str]
    entities: List[Dict[str, Any]]
    recommended_visual: Optional[ContentType] = None
    quality_score: float = 0.0
    suggestions: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class StyleCheckResult:
    """风格检查结果"""
    consistent: bool
    issues: List[Dict[str, Any]]
    recommended_style: Dict[str, Any]
    consistency_score: float


@dataclass
class PPTStructureAnalysis:
    """PPT 结构分析结果"""
    total_slides: int
    slide_types: List[str]
    logical_flow: List[str]
    repeated_content: List[Dict[str, Any]]
    missing_sections: List[str]
    structure_score: float


class ContextAnalyzer:
    """上下文分析器
    
    分析 PPT 的整体结构、内容类型、风格一致性等。
    """
    
    def __init__(self):
        """初始化分析器"""
        # 内容类型检测模式（按优先级排序）
        self.patterns = {
            ContentType.TIME_SERIES: [
                r'(?:Q[1-4]|[1-4]季度)',
                r'(?:第[一二三四]季度)',
                r'(?:\d{4}年\d{1,2}月|\d{4}年(?:营收|收入|利润|增长|销量|产出))',
                r'(?:\d{1,2}月\s*(?:至|到)\s*\d{1,2}月)',
            ],
            ContentType.DATA_COMPARISON: [
                r'(\w+)\s*(?:销量|收入|利润|占比|份额)\s*(\d+)',
                r'(\w+)\s*(?:比|vs|对比)\s*(\w+)',
                r'(\d+%)\s*(?:增长|下降|提升|同比)',
                r'(?:最多|最少|最高|最低|领先|落后)',
            ],
            ContentType.PROCESS: [
                r'(?:第[一二三四五]步|步骤\s*\d+)',
                r'(?:首先|然后|接着|最后)',
                r'(?:第[1-5]阶段|阶段\s*\d+)',
            ],
            ContentType.PERSON_ATTRIBUTES: [
                # 标准格式：姓名：张三
                r'(?:姓名|名字)[：:]\s*(\w+)',
                # 姓名，男/女，年龄岁
                r'(\w{2,4})[，,]\s*(?:男|女)[，,]\s*(\d+)\s*岁',
                # 姓名，年龄岁，职位（无性别）
                r'(\w{2,4})[，,]\s*(\d+)\s*岁[，,]\s*(\w+)',
                # 姓名，职位，年龄（无岁字）
                r'(\w{2,4})[，,]\s*(\w{2,6})[，,]\s*(\d+)(?:岁|$)',
                # 姓名  年龄岁  职位（空格分隔）
                r'(\w{2,4})\s+(\d+)\s*岁\s+(\w+)',
                # 自然语言：姓名今年/年龄岁
                r'(\w{2,4})(?:今年|年龄)\s*(\d+)\s*岁',
                # 自然语言描述：是张三，他今年30岁
                r'(?:是|叫)\s*(\w{2,4})[，,]?\s*(?:他|她)?(?:今年|年龄)\s*(\d+)\s*岁',
                # 括号格式：姓名（职位，年龄岁）
                r'(\w{2,4})（(\w+)[，,]\s*(\d+)岁）',
                # 年龄：30
                r'(?:年龄|岁数)[：:]\s*(\d+)',
                # 职位：工程师
                r'(?:职位|职务|角色)[：:]\s*(\w+)',
                # 称谓+姓名+年龄：王女士今年45岁
                r'(?:客户|经理|女士|先生|老师|同学|同事|leader|负责人)\s*(\w{2,4})(?:今年|年龄)\s*(\d+)\s*岁',
                # 描述性：项目经理李四今年35岁
                r'(?:\w{2,4})\s*(\w{2,4})(?:今年|年龄)\s*(\d+)\s*岁',
                # 擅长技能
                r'(?:擅长|专长|技能)[：:]\s*(.+?)(?:[，,。]|$)',
            ],
            ContentType.LIST: [
                r'(?:^|\n)\s*[-•*]\s+',
                r'(?:^|\n)\s*\d+[.、]\s+',
                r'(?:优点|特点|优势|功能)[：:]\s*\n',
            ],
        }
        
        # 常见章节
        self.common_sections = [
            "封面", "目录", "引言", "背景", "问题", "解决方案",
            "产品介绍", "核心优势", "功能特点", "案例", "客户证言",
            "数据", "市场", "竞争", "团队", "时间线", "总结", "致谢"
        ]
    
    def analyze_content(self, content: str) -> ContentAnalysis:
        """分析单个内容的内容类型
        
        Args:
            content: 要分析的文本内容
            
        Returns:
            ContentAnalysis: 内容分析结果
        """
        if not content or not content.strip():
            return ContentAnalysis(
                content_type=ContentType.TEXT,
                confidence=0.0,
                key_points=[],
                entities=[],
                quality_score=0.0
            )
        
        # 检测内容类型
        content_type, confidence = self._detect_content_type(content)
        
        # 提取关键点
        key_points = self._extract_key_points(content)
        
        # 提取实体
        entities = self._extract_entities(content, content_type)
        
        # 推荐可视化方式
        recommended_visual = self._recommend_visual(content_type, content)
        
        # 计算质量分数
        quality_score = self._calculate_quality_score(content, key_points)
        
        # 生成建议
        suggestions = self._generate_suggestions(
            content_type, content, key_points, quality_score
        )
        
        return ContentAnalysis(
            content_type=content_type,
            confidence=confidence,
            key_points=key_points,
            entities=entities,
            recommended_visual=recommended_visual,
            quality_score=quality_score,
            suggestions=suggestions
        )
    
    def _detect_content_type(self, content: str) -> Tuple[ContentType, float]:
        """检测内容类型
        
        Args:
            content: 文本内容
            
        Returns:
            Tuple[ContentType, float]: (内容类型, 置信度)
        """
        scores = {}
        
        for content_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                score += len(matches)
            
            if score > 0:
                scores[content_type] = score
        
        if not scores:
            return ContentType.TEXT, 0.5
        
        # 找到得分最高的类型
        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]
        
        # 计算置信度（基于匹配数量）
        confidence = min(0.5 + max_score * 0.1, 0.95)
        
        return best_type, confidence
    
    def _extract_key_points(self, content: str) -> List[str]:
        """提取关键点
        
        Args:
            content: 文本内容
            
        Returns:
            List[str]: 关键点列表
        """
        key_points = []
        
        # 按行分割
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测列表项
            if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+[.、]\s+', line):
                # 提取列表项内容
                point = re.sub(r'^[-•*]\s+', '', line)
                point = re.sub(r'^\d+[.、]\s+', '', point)
                key_points.append(point.strip())
            # 检测包含关键信息的行
            elif any(keyword in line for keyword in ['优势', '特点', '功能', '提升', '降低', '增长']):
                key_points.append(line)
        
        # 如果没有找到明确的关键点，取前5行作为关键点
        if not key_points:
            key_points = [line.strip() for line in lines[:5] if line.strip()]
        
        return key_points[:10]  # 最多返回10个关键点
    
    def _extract_entities(self, content: str, content_type: ContentType) -> List[Dict[str, Any]]:
        """提取实体
        
        Args:
            content: 文本内容
            content_type: 内容类型
            
        Returns:
            List[Dict[str, Any]]: 实体列表
        """
        entities = []
        
        if content_type == ContentType.PERSON_ATTRIBUTES:
            # 提取人物属性
            pattern = r'(\w+)\s*(?:今年|年龄)\s*(\d+)\s*岁'
            matches = re.findall(pattern, content)
            for name, age in matches:
                entities.append({"name": name, "age": age})
        
        elif content_type == ContentType.DATA_COMPARISON:
            # 提取数据对比
            pattern = r'(\w+)\s*(?:销量|收入|利润)\s*(\d+)'
            matches = re.findall(pattern, content)
            for name, value in matches:
                entities.append({"name": name, "value": value})
        
        return entities
    
    def _recommend_visual(self, content_type: ContentType, content: str) -> Optional[ContentType]:
        """推荐可视化方式
        
        Args:
            content_type: 内容类型
            content: 文本内容
            
        Returns:
            Optional[ContentType]: 推荐的可视化类型
        """
        recommendations = {
            ContentType.DATA_COMPARISON: ContentType.CHART,
            ContentType.TIME_SERIES: ContentType.CHART,
            ContentType.PERSON_ATTRIBUTES: ContentType.TABLE,
            ContentType.PROCESS: ContentType.FLOWCHART,
            ContentType.LIST: ContentType.LIST,
        }
        
        return recommendations.get(content_type, ContentType.TEXT)
    
    def _calculate_quality_score(self, content: str, key_points: List[str]) -> float:
        """计算质量分数
        
        Args:
            content: 文本内容
            key_points: 关键点列表
            
        Returns:
            float: 质量分数 (0-1)
        """
        score = 0.5  # 基础分
        
        # 内容长度
        if len(content) > 100:
            score += 0.1
        if len(content) > 300:
            score += 0.1
        
        # 关键点数量
        if len(key_points) >= 3:
            score += 0.1
        if len(key_points) >= 5:
            score += 0.1
        
        # 结构化程度
        if re.search(r'^[-•*]\s+', content, re.MULTILINE):
            score += 0.1
        if re.search(r'^\d+[.、]\s+', content, re.MULTILINE):
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_suggestions(
        self,
        content_type: ContentType,
        content: str,
        key_points: List[str],
        quality_score: float
    ) -> List[Dict[str, Any]]:
        """生成建议
        
        Args:
            content_type: 内容类型
            content: 文本内容
            key_points: 关键点列表
            quality_score: 质量分数
            
        Returns:
            List[Dict[str, Any]]: 建议列表
        """
        suggestions = []
        
        # 基于内容类型的建议
        if content_type == ContentType.DATA_COMPARISON:
            suggestions.append({
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "数据可视化建议",
                "description": "检测到数据对比内容，建议使用柱状图或折线图展示",
                "confidence": 0.9,
                "action": {
                    "type": "convert_to_chart",
                    "chart_type": "bar"
                }
            })
        
        elif content_type == ContentType.PERSON_ATTRIBUTES:
            suggestions.append({
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "表格展示建议",
                "description": "检测到人物属性数据，建议转换为表格展示",
                "confidence": 0.95,
                "action": {
                    "type": "convert_to_table"
                }
            })
        
        elif content_type == ContentType.PROCESS:
            suggestions.append({
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "流程图建议",
                "description": "检测到流程步骤，建议使用流程图展示",
                "confidence": 0.85,
                "action": {
                    "type": "convert_to_flowchart"
                }
            })
        
        # 基于质量分数的建议
        if quality_score < 0.6:
            suggestions.append({
                "type": SuggestionType.CONTENT_OPTIMIZE,
                "title": "内容优化建议",
                "description": "内容结构可以优化，建议添加更多关键点和数据支撑",
                "confidence": 0.7,
                "action": {
                    "type": "optimize_content"
                }
            })
        
        # 基于关键点数量的建议
        if len(key_points) > 7:
            suggestions.append({
                "type": SuggestionType.STRUCTURE_IMPROVE,
                "title": "内容精简建议",
                "description": f"当前有{len(key_points)}个要点，建议精简到5个以内",
                "confidence": 0.8,
                "action": {
                    "type": "simplify_content",
                    "max_points": 5
                }
            })
        
        return suggestions
    
    def check_style_consistency(self, slides: List[Dict[str, Any]]) -> StyleCheckResult:
        """检查风格一致性
        
        Args:
            slides: 幻灯片列表
            
        Returns:
            StyleCheckResult: 风格检查结果
        """
        if not slides:
            return StyleCheckResult(
                consistent=True,
                issues=[],
                recommended_style={},
                consistency_score=1.0
            )
        
        # 收集所有样式
        styles = []
        for slide in slides:
            style = slide.get("style", {})
            if style:
                styles.append(style)
        
        if not styles:
            return StyleCheckResult(
                consistent=True,
                issues=[],
                recommended_style={},
                consistency_score=1.0
            )
        
        # 检查一致性
        issues = []
        recommended_style = {}
        
        # 检查主色调
        colors = [s.get("primary_color") for s in styles if s.get("primary_color")]
        if colors:
            most_common_color = max(set(colors), key=colors.count)
            recommended_style["primary_color"] = most_common_color
            
            for i, color in enumerate(colors):
                if color != most_common_color:
                    issues.append({
                        "slide_index": i,
                        "issue": "配色不一致",
                        "expected": most_common_color,
                        "actual": color,
                        "suggestion": {
                            "action": "fix_style",
                            "params": {"primary_color": most_common_color}
                        }
                    })
        
        # 检查字体
        fonts = [s.get("font") for s in styles if s.get("font")]
        if fonts:
            most_common_font = max(set(fonts), key=fonts.count)
            recommended_style["font"] = most_common_font
            
            for i, font in enumerate(fonts):
                if font != most_common_font:
                    issues.append({
                        "slide_index": i,
                        "issue": "字体不一致",
                        "expected": most_common_font,
                        "actual": font,
                        "suggestion": {
                            "action": "fix_style",
                            "params": {"font": most_common_font}
                        }
                    })
        
        # 计算一致性分数
        total_checks = len(colors) + len(fonts)
        issues_count = len(issues)
        consistency_score = 1.0 - (issues_count / total_checks) if total_checks > 0 else 1.0
        
        return StyleCheckResult(
            consistent=len(issues) == 0,
            issues=issues,
            recommended_style=recommended_style,
            consistency_score=consistency_score
        )
    
    def analyze_structure(self, slides: List[Dict[str, Any]]) -> PPTStructureAnalysis:
        """分析 PPT 结构
        
        Args:
            slides: 幻灯片列表
            
        Returns:
            PPTStructureAnalysis: 结构分析结果
        """
        if not slides:
            return PPTStructureAnalysis(
                total_slides=0,
                slide_types=[],
                logical_flow=[],
                repeated_content=[],
                missing_sections=[],
                structure_score=0.0
            )
        
        # 分析每页幻灯片
        slide_types = []
        all_content = []
        
        for slide in slides:
            title = slide.get("title", "")
            content = slide.get("content", "")
            
            # 检测幻灯片类型
            slide_type = self._detect_slide_type(title, content)
            slide_types.append(slide_type)
            
            # 收集内容用于重复检测
            all_content.append({
                "index": slide.get("index", 0),
                "title": title,
                "content": content
            })
        
        # 检测重复内容
        repeated_content = self._detect_repeated_content(all_content)
        
        # 检测缺失章节
        missing_sections = self._detect_missing_sections(slide_types)
        
        # 分析逻辑流程
        logical_flow = self._analyze_logical_flow(slide_types)
        
        # 计算结构分数
        structure_score = self._calculate_structure_score(
            slide_types, repeated_content, missing_sections
        )
        
        return PPTStructureAnalysis(
            total_slides=len(slides),
            slide_types=slide_types,
            logical_flow=logical_flow,
            repeated_content=repeated_content,
            missing_sections=missing_sections,
            structure_score=structure_score
        )
    
    def _detect_slide_type(self, title: str, content: str) -> str:
        """检测幻灯片类型
        
        Args:
            title: 标题
            content: 内容
            
        Returns:
            str: 幻灯片类型
        """
        title_lower = title.lower()
        
        # 基于标题检测类型
        type_keywords = {
            "cover": ["封面", "cover", "标题", "title"],
            "toc": ["目录", "toc", "table of contents", "agenda"],
            "problem": ["问题", "pain points", "challenges", "挑战"],
            "solution": ["解决方案", "solution", "answer", "方案"],
            "product": ["产品", "product", "feature", "功能"],
            "advantage": ["优势", "advantage", "benefit", "价值"],
            "case": ["案例", "case", "example", "客户"],
            "data": ["数据", "data", "statistics", "统计"],
            "team": ["团队", "team", "成员"],
            "timeline": ["时间线", "timeline", "roadmap", "计划"],
            "summary": ["总结", "summary", "conclusion", "结论"],
            "thankyou": ["致谢", "thank you", "谢谢", "联系"],
        }
        
        for slide_type, keywords in type_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return slide_type
        
        # 基于内容检测类型
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in ["%", "万", "亿", "增长"]):
            return "data"
        
        return "content"
    
    def _detect_repeated_content(self, all_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测重复内容
        
        Args:
            all_content: 所有幻灯片内容
            
        Returns:
            List[Dict[str, Any]]: 重复内容列表
        """
        repeated = []
        
        # 简单的重复检测：比较标题
        titles = [c["title"] for c in all_content if c["title"]]
        seen_titles = set()
        
        for i, title in enumerate(titles):
            if title in seen_titles:
                repeated.append({
                    "type": "duplicate_title",
                    "title": title,
                    "indices": [j for j, t in enumerate(titles) if t == title]
                })
            else:
                seen_titles.add(title)
        
        return repeated
    
    def _detect_missing_sections(self, slide_types: List[str]) -> List[str]:
        """检测缺失章节
        
        Args:
            slide_types: 幻灯片类型列表
            
        Returns:
            List[str]: 缺失的章节列表
        """
        missing = []
        
        # 检查常见章节是否存在
        essential_sections = ["cover", "problem", "solution", "summary"]
        
        for section in essential_sections:
            if section not in slide_types:
                missing.append(section)
        
        return missing
    
    def _analyze_logical_flow(self, slide_types: List[str]) -> List[str]:
        """分析逻辑流程
        
        Args:
            slide_types: 幻灯片类型列表
            
        Returns:
            List[str]: 逻辑流程建议
        """
        suggestions = []
        
        # 检查常见问题
        if "cover" not in slide_types[:1]:
            suggestions.append("建议在第一页添加封面")
        
        if "summary" not in slide_types[-1:]:
            suggestions.append("建议在最后添加总结页")
        
        # 检查问题-解决方案顺序
        if "problem" in slide_types and "solution" in slide_types:
            problem_idx = slide_types.index("problem")
            solution_idx = slide_types.index("solution")
            if problem_idx > solution_idx:
                suggestions.append("建议将问题放在解决方案之前")
        
        return suggestions
    
    def _calculate_structure_score(
        self,
        slide_types: List[str],
        repeated_content: List[Dict[str, Any]],
        missing_sections: List[str]
    ) -> float:
        """计算结构分数
        
        Args:
            slide_types: 幻灯片类型列表
            repeated_content: 重复内容列表
            missing_sections: 缺失章节列表
            
        Returns:
            float: 结构分数 (0-1)
        """
        score = 0.7  # 基础分
        
        # 扣分项
        if repeated_content:
            score -= 0.1 * len(repeated_content)
        
        if missing_sections:
            score -= 0.05 * len(missing_sections)
        
        # 加分项
        if "cover" in slide_types:
            score += 0.05
        if "summary" in slide_types:
            score += 0.05
        if len(slide_types) >= 5:
            score += 0.05
        
        return max(0.0, min(1.0, score))


# 便捷函数
def analyze_content(content: str) -> ContentAnalysis:
    """分析内容（便捷函数）"""
    analyzer = ContextAnalyzer()
    return analyzer.analyze_content(content)


def check_style_consistency(slides: List[Dict[str, Any]]) -> StyleCheckResult:
    """检查风格一致性（便捷函数）"""
    analyzer = ContextAnalyzer()
    return analyzer.check_style_consistency(slides)


def analyze_structure(slides: List[Dict[str, Any]]) -> PPTStructureAnalysis:
    """分析结构（便捷函数）"""
    analyzer = ContextAnalyzer()
    return analyzer.analyze_structure(slides)