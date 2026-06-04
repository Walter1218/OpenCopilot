"""
内容转换引擎

功能：
- 文本智能识别：分析文本结构，推荐转换方式
- 数据提取：从文本中提取结构化数据
- 图表/表格数据结构定义
- 内容转换：将文本转换为图表/表格数据
"""

import re
import json
from typing import Optional, List, Dict, Any, Tuple


# ==========================================
# 数据结构定义
# ==========================================

def create_table_data(title: str, columns: List[str], rows: List[List[str]]) -> dict:
    """创建表格数据结构"""
    return {
        "content_type": "table",
        "table_data": {
            "title": title,
            "columns": columns,
            "rows": rows
        }
    }


def create_chart_data(title: str, chart_type: str, labels: List[str],
                      datasets: List[Dict[str, Any]]) -> dict:
    """创建图表数据结构
    
    Args:
        title: 图表标题
        chart_type: 图表类型 (bar/line/pie/doughnut)
        labels: 标签列表
        datasets: 数据集列表 [{"label": "系列名", "data": [值列表], "color": "#hex"}]
    """
    return {
        "content_type": "chart",
        "chart_type": chart_type,
        "chart_data": {
            "title": title,
            "labels": labels,
            "datasets": datasets
        }
    }


def create_flowchart_data(title: str, steps: List[str], layout: str = "horizontal") -> dict:
    """创建流程图数据结构"""
    return {
        "content_type": "flowchart",
        "flowchart_data": {
            "title": title,
            "steps": steps,
            "layout": layout
        }
    }


# ==========================================
# 文本分析器
# ==========================================

class TextAnalyzer:
    """文本结构分析器 - 智能识别文本并推荐转换方式"""
    
    # 默认颜色方案
    DEFAULT_COLORS = [
        "#007bff", "#28a745", "#ffc107", "#dc3545",
        "#6f42c1", "#17a2b8", "#fd7e14", "#20c997"
    ]
    
    @staticmethod
    def analyze(text: str) -> dict:
        """分析文本结构，返回转换建议
        
        Returns:
            {
                "recommendations": [...],
                "best_match": {...} | None,
                "extracted_data": {...} | None
            }
        """
        if not text or not text.strip():
            return {"recommendations": [], "best_match": None, "extracted_data": None}
        
        text = text.strip()
        recommendations = []
        
        # 检测各种模式
        table_result = TextAnalyzer._detect_table(text)
        if table_result:
            recommendations.append(table_result)
        
        number_result = TextAnalyzer._detect_number_comparison(text)
        if number_result:
            recommendations.append(number_result)
        
        flow_result = TextAnalyzer._detect_flow_steps(text)
        if flow_result:
            recommendations.append(flow_result)
        
        timeline_result = TextAnalyzer._detect_timeline(text)
        if timeline_result:
            recommendations.append(timeline_result)
        
        list_result = TextAnalyzer._detect_list(text)
        if list_result:
            recommendations.append(list_result)
        
        # 按置信度排序
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        
        best_match = recommendations[0] if recommendations else None
        extracted_data = None
        
        if best_match:
            extracted_data = TextAnalyzer._extract_data(text, best_match)
        
        return {
            "recommendations": recommendations,
            "best_match": best_match,
            "extracted_data": extracted_data
        }
    
    @staticmethod
    def _detect_table(text: str) -> Optional[dict]:
        """检测表格结构"""
        lines = text.strip().split('\n')
        
        # 模式1: 使用 | 分隔的表格
        if '|' in text:
            pipe_lines = [l for l in lines if '|' in l and l.strip().startswith('|')]
            if len(pipe_lines) >= 2:
                return {
                    "type": "table",
                    "subtype": "markdown",
                    "confidence": 0.95,
                    "reason": "检测到 Markdown 表格格式"
                }
        
        # 模式2: 使用制表符分隔
        if '\t' in text:
            tab_lines = [l for l in lines if '\t' in l]
            if len(tab_lines) >= 2:
                return {
                    "type": "table",
                    "subtype": "tsv",
                    "confidence": 0.9,
                    "reason": "检测到制表符分隔的数据"
                }
        
        # 模式3: 冒号分隔的键值对（多行）
        colon_pattern = re.compile(r'^[\u4e00-\u9fa5a-zA-Z]+\s*[：:]\s*.+$')
        colon_lines = [l for l in lines if colon_pattern.match(l.strip())]
        if len(colon_lines) >= 3:
            return {
                "type": "table",
                "subtype": "key_value",
                "confidence": 0.85,
                "reason": "检测到多行键值对数据，适合表格展示"
            }
        
        return None
    
    @staticmethod
    def _detect_number_comparison(text: str) -> Optional[dict]:
        """检测数字对比 → 柱状图/折线图"""
        # 提取所有数字（含百分比、小数）
        numbers = re.findall(r'\d+\.?\d*%?', text)
        
        if len(numbers) < 2:
            return None
        
        # 模式1: "标签：数字" 格式（支持字母+数字组合如 Q1, Q2）
        label_number_pattern = re.compile(
            r'([A-Za-z\u4e00-\u9fa5][A-Za-z\u4e00-\u9fa5\d]*)\s*[：:]\s*(\d+\.?\d*%?)'
        )
        matches = label_number_pattern.findall(text)
        
        # 模式2: "标签 数字万/亿" 或 "标签 数字%" 格式
        if len(matches) < 2:
            label_number_pattern2 = re.compile(
                r'([\u4e00-\u9fa5a-zA-Z]+)\s+(\d+\.?\d*)\s*[万%元人台次]'
            )
            matches = label_number_pattern2.findall(text)
        
        # 模式3: 用逗号/顿号分隔的 "标签 数字" 对
        if len(matches) < 2:
            # 提取 "Q1 100万" 这种格式
            label_number_pattern3 = re.compile(
                r'([A-Za-z\u4e00-\u9fa5]+\d*)\s+(\d+\.?\d*)\s*[万%元人台次]?(?=[，,、。\s]|$)'
            )
            matches = label_number_pattern3.findall(text)
        
        if len(matches) >= 2:
            # 有明确的标签-数字对
            # 检测是否有时间序列特征
            time_keywords = ['Q1', 'Q2', 'Q3', 'Q4', '1月', '2月', '3月', '4月',
                             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                             '第一季度', '第二季度', '第三季度', '第四季度',
                             '上半年', '下半年', '一月', '二月', '三月', '四月']
            
            has_time = any(kw in text for kw in time_keywords)
            
            if has_time:
                return {
                    "type": "chart",
                    "subtype": "line",
                    "confidence": 0.92,
                    "reason": "检测到时间序列数字数据，推荐折线图"
                }
            else:
                return {
                    "type": "chart",
                    "subtype": "bar",
                    "confidence": 0.9,
                    "reason": "检测到数字对比数据，推荐柱状图"
                }
        
        # 数字较多但无明确标签 → 可能是百分比分布
        percent_numbers = [n for n in numbers if '%' in n]
        if len(percent_numbers) >= 3:
            total = sum(float(n.replace('%', '')) for n in percent_numbers)
            if 95 <= total <= 105:  # 接近100%
                return {
                    "type": "chart",
                    "subtype": "pie",
                    "confidence": 0.88,
                    "reason": "检测到百分比分布数据，推荐饼图"
                }
        
        return None
    
    @staticmethod
    def _detect_flow_steps(text: str) -> Optional[dict]:
        """检测流程步骤"""
        flow_keywords = [
            r'步骤\s*\d', r'第[一二三四五六七八九十]步',
            r'首先', r'然后', r'接着', r'最后', r'最终',
            r'\d+[.、)\]]\s*\S',  # 编号列表
        ]
        
        # 箭头连接符（需要多个才算流程）
        arrow_patterns = [r'→', r'->', r'⇒']
        
        matches = 0
        for pattern in flow_keywords:
            if re.search(pattern, text):
                matches += 1
        
        # 检查箭头数量（需要至少 2 个箭头才算流程）
        arrow_count = 0
        for pattern in arrow_patterns:
            arrow_count += len(re.findall(pattern, text))
        
        if arrow_count >= 2:
            return {
                "type": "flowchart",
                "subtype": "horizontal",
                "confidence": 0.85,
                "reason": "检测到箭头连接的流程步骤"
            }
        
        if matches >= 2:
            return {
                "type": "flowchart",
                "subtype": "horizontal",
                "confidence": 0.85,
                "reason": "检测到流程步骤，推荐流程图"
            }
        
        return None
    
    @staticmethod
    def _detect_timeline(text: str) -> Optional[dict]:
        """检测时间线"""
        # 年份模式
        year_pattern = re.findall(r'(20\d{2}|19\d{2})\s*年?', text)
        if len(year_pattern) >= 3:
            return {
                "type": "chart",
                "subtype": "timeline",
                "confidence": 0.8,
                "reason": "检测到多年份数据，推荐时间线展示"
            }
        
        return None
    
    @staticmethod
    def _detect_list(text: str) -> Optional[dict]:
        """检测列表结构"""
        lines = text.strip().split('\n')
        
        # 检测无序列表
        bullet_patterns = [r'^[-•·*]\s+', r'^[▪▫◦]\s+']
        bullet_lines = []
        for line in lines:
            for pattern in bullet_patterns:
                if re.match(pattern, line.strip()):
                    bullet_lines.append(line)
                    break
        
        if len(bullet_lines) >= 3:
            return {
                "type": "list",
                "subtype": "bullet",
                "confidence": 0.7,
                "reason": "检测到列表结构，可保持为要点列表"
            }
        
        # 检测有序列表
        numbered_lines = [l for l in lines if re.match(r'^\d+[.、)\]]\s+', l.strip())]
        if len(numbered_lines) >= 3:
            return {
                "type": "list",
                "subtype": "numbered",
                "confidence": 0.7,
                "reason": "检测到有序列表"
            }
        
        return None
    
    @staticmethod
    def _extract_data(text: str, recommendation: dict) -> Optional[dict]:
        """根据推荐类型提取结构化数据"""
        rec_type = recommendation.get("type")
        subtype = recommendation.get("subtype")
        
        if rec_type == "table":
            return TextAnalyzer._extract_table_data(text, subtype)
        elif rec_type == "chart":
            return TextAnalyzer._extract_chart_data(text, subtype)
        elif rec_type == "flowchart":
            return TextAnalyzer._extract_flowchart_data(text)
        
        return None
    
    @staticmethod
    def _extract_table_data(text: str, subtype: str) -> dict:
        """提取表格数据"""
        lines = text.strip().split('\n')
        
        if subtype == "markdown":
            # 解析 Markdown 表格
            rows = []
            for line in lines:
                if '|' not in line:
                    continue
                if re.match(r'^[\s|:-]+$', line.strip()):
                    continue  # 跳过分隔行
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                rows.append(cells)
            
            if len(rows) >= 2:
                columns = rows[0]
                data_rows = rows[1:]
                return {
                    "columns": columns,
                    "rows": data_rows
                }
        
        elif subtype == "key_value":
            # 解析键值对
            pattern = re.compile(r'([\u4e00-\u9fa5a-zA-Z]+)\s*[：:]\s*(.+)')
            pairs = []
            for line in lines:
                match = pattern.match(line.strip())
                if match:
                    pairs.append([match.group(1).strip(), match.group(2).strip()])
            
            if pairs:
                return {
                    "columns": ["项目", "值"],
                    "rows": pairs
                }
        
        return None
    
    @staticmethod
    def _extract_chart_data(text: str, subtype: str) -> dict:
        """提取图表数据"""
        # 模式1: "标签：数字" 格式（支持字母+数字组合如 Q1, Q2）
        pattern = re.compile(
            r'([A-Za-z\u4e00-\u9fa5][A-Za-z\u4e00-\u9fa5\d]*)\s*[：:]\s*(\d+\.?\d*)%?'
        )
        matches = pattern.findall(text)
        
        # 模式2: "标签 数字万" 格式
        if len(matches) < 2:
            pattern2 = re.compile(
                r'([A-Za-z\u4e00-\u9fa5]+\d*)\s+(\d+\.?\d*)\s*[万%元人台次]?'
            )
            matches = pattern2.findall(text)
        
        if not matches:
            return None
        
        labels = [m[0] for m in matches]
        values = [float(m[1]) for m in matches]
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "数据",
                    "data": values,
                    "color": TextAnalyzer.DEFAULT_COLORS[0]
                }
            ]
        }
    
    @staticmethod
    def _extract_flowchart_data(text: str) -> dict:
        """提取流程图数据"""
        # 先按箭头拆分（处理单行箭头分隔的情况）
        arrow_pattern = r'\s*[→⇒\->]\s*'
        if re.search(arrow_pattern, text):
            # 按箭头拆分
            parts = re.split(arrow_pattern, text)
            steps = [p.strip() for p in parts if p.strip()]
        else:
            # 按行拆分
            lines = text.strip().split('\n')
            steps = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 去掉编号前缀
                cleaned = re.sub(r'^\d+[.、)\]]\s*', '', line)
                cleaned = re.sub(r'^步骤\s*\d+\s*[：:.]?\s*', '', cleaned)
                cleaned = re.sub(r'^(首先|然后|接着|最后|最终)\s*[：:,，]?\s*', '', cleaned)
                
                if cleaned and len(cleaned) > 1:
                    steps.append(cleaned)
        
        if steps:
            return {"steps": steps}
        
        return None


# ==========================================
# 内容转换器
# ==========================================

class ContentConverter:
    """内容转换器 - 将文本转换为图表/表格数据"""
    
    @staticmethod
    def convert_to_table(text: str, title: str = "") -> dict:
        """将文本转换为表格数据"""
        analysis = TextAnalyzer.analyze(text)
        
        if not title:
            title = "数据表格"
        
        extracted = analysis.get("extracted_data")
        if extracted and "columns" in extracted:
            return create_table_data(
                title=title,
                columns=extracted["columns"],
                rows=extracted.get("rows", [])
            )
        
        # 降级处理：按行拆分
        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        if lines:
            return create_table_data(
                title=title,
                columns=["内容"],
                rows=[[l] for l in lines]
            )
        
        return create_table_data(title=title, columns=["内容"], rows=[[text]])
    
    @staticmethod
    def convert_to_chart(text: str, chart_type: str = "bar", title: str = "") -> dict:
        """将文本转换为图表数据"""
        analysis = TextAnalyzer.analyze(text)
        
        if not title:
            title = "数据图表"
        
        extracted = analysis.get("extracted_data")
        if extracted and "labels" in extracted:
            return create_chart_data(
                title=title,
                chart_type=chart_type,
                labels=extracted["labels"],
                datasets=extracted.get("datasets", [])
            )
        
        # 无法提取结构化数据
        return create_chart_data(
            title=title,
            chart_type=chart_type,
            labels=["数据1", "数据2", "数据3"],
            datasets=[{"label": "示例", "data": [10, 20, 30], "color": "#007bff"}]
        )
    
    @staticmethod
    def convert_to_flowchart(text: str, title: str = "") -> dict:
        """将文本转换为流程图数据"""
        analysis = TextAnalyzer.analyze(text)
        
        if not title:
            title = "流程图"
        
        extracted = analysis.get("extracted_data")
        if extracted and "steps" in extracted:
            return create_flowchart_data(
                title=title,
                steps=extracted["steps"]
            )
        
        # 降级处理
        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        return create_flowchart_data(title=title, steps=lines[:5])


# ==========================================
# 快捷转换菜单数据
# ==========================================

CONVERSION_OPTIONS = [
    {
        "id": "table",
        "label": "表格",
        "icon": "📊",
        "description": "将数据转换为表格",
        "accept_types": ["table", "list"]
    },
    {
        "id": "bar",
        "label": "柱状图",
        "icon": "📊",
        "description": "对比不同类别的数值",
        "accept_types": ["chart"]
    },
    {
        "id": "line",
        "label": "折线图",
        "icon": "📈",
        "description": "展示数据变化趋势",
        "accept_types": ["chart"]
    },
    {
        "id": "pie",
        "label": "饼图",
        "icon": "🥧",
        "description": "展示数据占比分布",
        "accept_types": ["chart"]
    },
    {
        "id": "flowchart",
        "label": "流程图",
        "icon": "🔄",
        "description": "展示步骤流程",
        "accept_types": ["flowchart"]
    },
]


def get_conversion_suggestions(text: str) -> dict:
    """获取转换建议（供 API 和 UI 调用）"""
    analysis = TextAnalyzer.analyze(text)
    
    suggestions = []
    best_match = analysis.get("best_match")
    
    for option in CONVERSION_OPTIONS:
        opt = option.copy()
        opt["recommended"] = False
        
        if best_match:
            if best_match["type"] == "chart" and option["id"] == best_match.get("subtype"):
                opt["recommended"] = True
            elif best_match["type"] == option["id"]:
                opt["recommended"] = True
        
        suggestions.append(opt)
    
    # 把推荐的放前面
    suggestions.sort(key=lambda x: x["recommended"], reverse=True)
    
    return {
        "text": text[:200],  # 截取前200字符
        "analysis": analysis,
        "suggestions": suggestions
    }
