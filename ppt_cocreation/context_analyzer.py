"""
智能上下文感知模块

分析 PPT 的整体结构、内容类型、风格一致性等，为 AI 提供全局视野。
支持两种检测模式：
1. 正则模式（快速，无依赖）
2. LLM 辅助模式（更准确，需要 API）
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """内容类型"""
    # 基础类型
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    FLOWCHART = "flowchart"
    IMAGE = "image"
    LIST = "list"
    
    # 语义类型
    DATA_COMPARISON = "data_comparison"      # 数据对比
    TIME_SERIES = "time_series"              # 时间序列
    PROCESS = "process"                      # 流程步骤
    PERSON_ATTRIBUTES = "person_attributes"  # 人物属性
    
    # 新增泛化类型
    PROBLEM_SOLUTION = "problem_solution"    # 问题-解决方案
    PROS_CONS = "pros_cons"                  # 优缺点对比
    FEATURE_LIST = "feature_list"            # 功能特点
    CASE_STUDY = "case_study"                # 案例分析
    DEFINITION = "definition"                # 定义/概念
    SUMMARY = "summary"                      # 总结/结论
    QUOTE = "quote"                          # 引用/名言
    STATISTICS = "statistics"                # 统计数据
    COMPARISON = "comparison"                # 通用对比
    ORGANIZATION = "organization"            # 组织架构
    TIMELINE = "timeline"                    # 时间线
    ARGUMENT = "argument"                    # 论点/论据


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
    支持正则模式和 LLM 辅助模式。
    """
    
    def __init__(self, llm_classify_func: Optional[Callable] = None):
        """初始化分析器
        
        Args:
            llm_classify_func: LLM 分类函数，可选。
                如果提供，签名应为 (content: str) -> Dict[str, Any]
                返回格式：{"content_type": str, "confidence": float, "reason": str}
        """
        self.llm_classify_func = llm_classify_func
        
        # 内容类型检测模式（按优先级排序）
        self.patterns = {
            # === 基础类型 ===
            ContentType.DATA_COMPARISON: [
                r'(\w+)\s*(?:销量|收入|利润|占比|份额)\s*(\d+)',
                r'(\w+)\s*(?:比|vs|对比)\s*(\w+)',
                r'(\d+%)\s*(?:增长|下降|提升|同比)',
                r'(?:最多|最少|最高|最低|领先|落后)',
                r'(?:Q[1-4]|[1-4]季度)\s*(?:增长|下降|提升)',
            ],
            ContentType.TIME_SERIES: [
                r'(?:第[一二三四]季度)',
                r'(?:\d{4}年\d{1,2}月|\d{4}年(?:营收|收入|利润|销量|产出))',
                r'(?:\d{1,2}月\s*(?:至|到)\s*\d{1,2}月)',
                r'(?:Q[1-4]|[1-4]季度)(?!.*(?:增长|下降|提升))',
            ],
            ContentType.PROCESS: [
                r'(?:第[一二三四五]步|步骤\s*\d+)',
                r'(?:首先|然后|接着|最后)',
                r'(?:第[1-5]阶段|阶段\s*\d+)',
            ],
            ContentType.PERSON_ATTRIBUTES: [
                r'(?:姓名|名字)[：:]\s*(\w+)',
                r'(\w{2,4})[，,]\s*(?:男|女)[，,]\s*(\d+)\s*岁',
                r'(\w{2,4})[，,]\s*(\d+)\s*岁[，,]\s*(\w+)',
                r'(\w{2,4})[，,]\s*(\w{2,6})[，,]\s*(\d+)(?:岁|$)',
                r'(\w{2,4})\s+(\d+)\s*岁\s+(\w+)',
                r'(\w{2,4})(?:今年|年龄)\s*(\d+)\s*岁',
                r'(?:是|叫)\s*(\w{2,4})[，,]?\s*(?:他|她)?(?:今年|年龄)\s*(\d+)\s*岁',
                r'(\w{2,4})（(\w+)[，,]\s*(\d+)岁）',
                r'(?:年龄|岁数)[：:]\s*(\d+)',
                r'(?:职位|职务|角色)[：:]\s*(\w+)',
                r'(?:客户|经理|女士|先生|老师|同学|同事|leader|负责人)\s*(\w{2,4})(?:今年|年龄)\s*(\d+)\s*岁',
                r'(?:\w{2,4})\s*(\w{2,4})(?:今年|年龄)\s*(\d+)\s*岁',
                r'(?:擅长|专长|技能)[：:]\s*(.+?)(?:[，,。]|$)',
            ],
            ContentType.LIST: [
                r'(?:^|\n)\s*[-•*]\s+',
                r'(?:^|\n)\s*\d+[.、]\s+',
                r'(?:优点|特点|优势|功能)[：:]\s*\n',
            ],
            
            # === 新增泛化类型 ===
            
            # 问题-解决方案
            ContentType.PROBLEM_SOLUTION: [
                r'(?:问题|痛点|挑战|困难)[：:]',
                r'(?:解决方案|解决办法|应对策略|方案)[：:]',
                r'(?:问题\d|[一二三四五]、.*问题)',
                r'(?:如何解决|怎么解决|怎样解决)',
                r'(?:针对.*问题.*采取)',
            ],
            
            # 优缺点对比
            ContentType.PROS_CONS: [
                r'(?:优点|优势|好处|长处)[：:]',
                r'(?:缺点|劣势|不足|短处)[：:]',
                r'(?:利弊|得失|优劣)',
                r'(?:好处是|坏处是|优势在于|劣势在于)',
                r'(?:正面|反面|积极|消极)影响',
            ],
            
            # 功能特点
            ContentType.FEATURE_LIST: [
                r'(?:核心功能|主要功能|功能特点|产品特点)[：:]',
                r'(?:特点\d|[一二三四五]、.*特点)',
                r'(?:支持|具备|拥有|提供).*(?:功能|能力|特性)',
                r'(?:亮点|卖点|特色)[：:]',
                r'(?:功能[：:].*\n.*功能)',
            ],
            
            # 案例分析
            ContentType.CASE_STUDY: [
                r'(?:案例|实例|示例)[：:]',
                r'(?:例如|比如|譬如)',
                r'(?:某公司|某企业|某客户|某用户)',
                r'(?:案例\d|案例[一二三四五])',
                r'(?:成功案例|典型案例)',
            ],
            
            # 定义/概念
            ContentType.DEFINITION: [
                r'(?:是指|指的是|定义为|定义是)',
                r'(?:概念|含义|意思)[：:]',
                r'(?:什么是|何为|何谓)',
                r'(?:\w+是\w+的一种)',
            ],
            
            # 总结/结论
            ContentType.SUMMARY: [
                r'(?:总结|综上所述|总而言之|总的来说)',
                r'(?:结论|结语|小结)[：:]',
                r'(?:最后|最终|末尾)',
                r'(?:概括|归纳|提炼)',
            ],
            
            # 引用/名言
            ContentType.QUOTE: [
                r'(?:正如.*所说|据.*所言)',
                r'(?:名言|格言|警句)',
                r'["""].*["""]',
                r'(?:引用|摘录|出自)',
                r'(?:说过|曾说|曾言|曾说过)',
                r'(?:\w+\s*(?:说过|曾说)[：:])',
            ],
            
            # 统计数据
            ContentType.STATISTICS: [
                r'(?:据统计|数据显示|调查表明)',
                r'(?:\d+\.?\d*%|百分之)',
                r'(?:平均|总计|合计|总共)',
                r'(?:样本|调查对象|受访者)',
            ],
            
            # 通用对比
            ContentType.COMPARISON: [
                r'(?:对比|比较|对照)(?!.*(?:数据|销量|收入))',
                r'(?:不同于|区别于|相比)',
                r'(?:前者|后者)',
                r'(?:方案[AB]|选项[AB])',
            ],
            
            # 组织架构
            ContentType.ORGANIZATION: [
                r'(?:组织架构|部门设置|团队结构)',
                r'(?:CEO|CTO|VP|总监|经理)',
                r'(?:向.*汇报|负责.*管理)',
                r'(?:部门|团队|小组)',
            ],
            
            # 时间线
            ContentType.TIMELINE: [
                r'(?:\d{4}年\d{1,2}月\d{1,2}日)',
                r'(?:时间线|里程碑|节点)',
                r'(?:计划.*完成|预计.*上线)',
                r'(?:阶段\d|第\d阶段)',
                r'(?:\d{4}年\d{1,2}月[：:]\s*.*)',
            ],
            
            # 论点/论据
            ContentType.ARGUMENT: [
                r'(?:论点|论据|论证)',
                r'(?:因此|所以|故|由此可见)',
                r'(?:证明|表明|说明|显示)',
                r'(?:基于.*得出)',
            ],
        }
        
        # 可视化推荐映射
        self.visual_recommendations = {
            ContentType.DATA_COMPARISON: ContentType.CHART,
            ContentType.TIME_SERIES: ContentType.CHART,
            ContentType.PERSON_ATTRIBUTES: ContentType.TABLE,
            ContentType.PROCESS: ContentType.FLOWCHART,
            ContentType.LIST: ContentType.LIST,
            ContentType.PROBLEM_SOLUTION: ContentType.FLOWCHART,
            ContentType.PROS_CONS: ContentType.TABLE,
            ContentType.FEATURE_LIST: ContentType.LIST,
            ContentType.CASE_STUDY: ContentType.TEXT,
            ContentType.DEFINITION: ContentType.TEXT,
            ContentType.SUMMARY: ContentType.TEXT,
            ContentType.QUOTE: ContentType.TEXT,
            ContentType.STATISTICS: ContentType.CHART,
            ContentType.COMPARISON: ContentType.TABLE,
            ContentType.ORGANIZATION: ContentType.FLOWCHART,
            ContentType.TIMELINE: ContentType.FLOWCHART,
            ContentType.ARGUMENT: ContentType.TEXT,
        }
        
        # 常见章节
        self.common_sections = [
            "封面", "目录", "引言", "背景", "问题", "解决方案",
            "产品介绍", "核心优势", "功能特点", "案例", "客户证言",
            "数据", "市场", "竞争", "团队", "时间线", "总结", "致谢"
        ]
    
    def analyze_content(self, content: str, use_llm: bool = False) -> ContentAnalysis:
        """分析单个内容的内容类型
        
        Args:
            content: 要分析的文本内容
            use_llm: 是否使用 LLM 辅助分类（需要在初始化时提供 llm_classify_func）
            
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
        if use_llm and self.llm_classify_func:
            content_type, confidence = self._detect_content_type_with_llm(content)
        else:
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
        """使用正则模式检测内容类型
        
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
    
    def _detect_content_type_with_llm(self, content: str) -> Tuple[ContentType, float]:
        """使用 LLM 辅助检测内容类型
        
        Args:
            content: 文本内容
            
        Returns:
            Tuple[ContentType, float]: (内容类型, 置信度)
        """
        if not self.llm_classify_func:
            return self._detect_content_type(content)
        
        try:
            # 构建提示词
            content_types_str = ", ".join([t.value for t in ContentType])
            prompt = f"""请分析以下文本的内容类型。

可选类型：{content_types_str}

文本内容：
{content[:500]}  # 限制长度避免 token 过多

请返回 JSON 格式：
{{"content_type": "类型", "confidence": 0.0-1.0, "reason": "判断理由"}}
"""
            
            # 调用 LLM
            result = self.llm_classify_func(prompt)
            
            if isinstance(result, str):
                result = json.loads(result)
            
            content_type_str = result.get("content_type", "text")
            confidence = result.get("confidence", 0.7)
            
            # 转换为枚举
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                content_type = ContentType.TEXT
                confidence = 0.5
            
            return content_type, confidence
            
        except Exception as e:
            logger.warning(f"LLM 分类失败，回退到正则模式: {e}")
            return self._detect_content_type(content)
    
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
        
        elif content_type == ContentType.STATISTICS:
            # 提取统计数据
            pattern = r'(\d+\.?\d*)%'
            matches = re.findall(pattern, content)
            for value in matches:
                entities.append({"type": "percentage", "value": value})
        
        return entities
    
    def _recommend_visual(self, content_type: ContentType, content: str) -> Optional[ContentType]:
        """推荐可视化方式
        
        Args:
            content_type: 内容类型
            content: 文本内容
            
        Returns:
            Optional[ContentType]: 推荐的可视化类型
        """
        return self.visual_recommendations.get(content_type, ContentType.TEXT)
    
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
        type_suggestions = {
            ContentType.DATA_COMPARISON: {
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "数据可视化建议",
                "description": "检测到数据对比内容，建议使用柱状图或折线图展示",
                "confidence": 0.9,
                "action": {"type": "convert_to_chart", "chart_type": "bar"}
            },
            ContentType.PERSON_ATTRIBUTES: {
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "表格展示建议",
                "description": "检测到人物属性数据，建议转换为表格展示",
                "confidence": 0.95,
                "action": {"type": "convert_to_table"}
            },
            ContentType.PROCESS: {
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "流程图建议",
                "description": "检测到流程步骤，建议使用流程图展示",
                "confidence": 0.85,
                "action": {"type": "convert_to_flowchart"}
            },
            ContentType.PROBLEM_SOLUTION: {
                "type": SuggestionType.STRUCTURE_IMPROVE,
                "title": "结构化建议",
                "description": "检测到问题-解决方案结构，建议使用左右分栏展示",
                "confidence": 0.8,
                "action": {"type": "split_columns"}
            },
            ContentType.PROS_CONS: {
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "对比表格建议",
                "description": "检测到优缺点对比，建议使用表格展示",
                "confidence": 0.85,
                "action": {"type": "convert_to_table"}
            },
            ContentType.STATISTICS: {
                "type": SuggestionType.VISUAL_ENHANCE,
                "title": "图表建议",
                "description": "检测到统计数据，建议使用饼图或柱状图展示",
                "confidence": 0.9,
                "action": {"type": "convert_to_chart", "chart_type": "pie"}
            },
        }
        
        if content_type in type_suggestions:
            suggestions.append(type_suggestions[content_type])
        
        # 基于质量分数的建议
        if quality_score < 0.6:
            suggestions.append({
                "type": SuggestionType.CONTENT_OPTIMIZE,
                "title": "内容优化建议",
                "description": "内容结构可以优化，建议添加更多关键点和数据支撑",
                "confidence": 0.7,
                "action": {"type": "optimize_content"}
            })
        
        # 基于关键点数量的建议
        if len(key_points) > 7:
            suggestions.append({
                "type": SuggestionType.STRUCTURE_IMPROVE,
                "title": "内容精简建议",
                "description": f"当前有{len(key_points)}个要点，建议精简到5个以内",
                "confidence": 0.8,
                "action": {"type": "simplify_content", "max_points": 5}
            })
        
        return suggestions
    
    def set_llm_classify_func(self, llm_classify_func: Callable):
        """设置 LLM 分类函数
        
        Args:
            llm_classify_func: LLM 分类函数
        """
        self.llm_classify_func = llm_classify_func
    
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
def analyze_content(content: str, use_llm: bool = False) -> ContentAnalysis:
    """分析内容（便捷函数）"""
    analyzer = ContextAnalyzer()
    return analyzer.analyze_content(content, use_llm)


def check_style_consistency(slides: List[Dict[str, Any]]) -> StyleCheckResult:
    """检查风格一致性（便捷函数）"""
    analyzer = ContextAnalyzer()
    return analyzer.check_style_consistency(slides)


def analyze_structure(slides: List[Dict[str, Any]]) -> PPTStructureAnalysis:
    """分析结构（便捷函数）"""
    analyzer = ContextAnalyzer()
    return analyzer.analyze_structure(slides)
