"""
PPT 编辑指令意图路由器

根据用户自然语言指令，将不同意图路由到不同处理管线：
- 简单操作（改标题/副标题/版式）→ 直接执行，不调用 LLM
- 图表/表格转换 → ChartConversionPipeline
- 添加/删除幻灯片 → 结构操作
- 复杂文案改写 → LLM
"""

import re
from typing import Optional, Tuple, Dict, Any


class IntentRouter:
    """指令意图路由器"""

    # 简单操作：正则匹配 → 直接执行
    SIMPLE_PATTERNS = {
        "update_title": [
            r'第?\s*(\d+)\s*页?\s*(?:的|标题)\s*[改修更换]\s*[为成至]?\s*(?:标题\s*[:：]?\s*)?(.+)',
            r'(?:把|将)\s*第?\s*(\d+)\s*页?\s*(?:标题|题目)\s*(?:改|修|设)\s*为\s*(.+)',
            r'(?:标题|题目)\s*(?:改|修)\s*为\s*(.+)',  # 当前页
        ],
        "update_subtitle": [
            r'第?\s*(\d+)\s*页?\s*(?:的|副标题)\s*[改修更换]\s*[为成至]?\s*(?:副标题\s*[:：]?\s*)?(.+)',
            r'(?:副标题|小标题)\s*(?:改|修)\s*为\s*(.+)',
        ],
        "update_layout": [
            r'第?\s*(\d+)\s*页?\s*(?:版式|布局)\s*(?:改为|设为|切换为)\s*(.+)',
            r'(?:版式|布局)\s*(?:改为|设为)\s*(.+)',
        ],
        "add_slide": [
            r'(?:添加|新增|加上|插入)\s*(?:一?[个张页]\s*)?(?:新?\s*)?(?:幻灯片|页面)',
            r'在\s*第\s*(\d+)\s*页\s*(?:后|后面|之后)\s*(?:添加|插入|加上)',
        ],
        "remove_slide": [
            r'(?:删除|移除|去掉)\s*第?\s*(\d+)\s*[页张个]?\s*(?:幻灯片|页面)?',
            r'第?\s*(\d+)\s*[页张]\s*(?:不要了|删除|删掉|去掉)',
        ],
        "convert_chart": [
            r'(?:转[为成]|改成|变成|做成)\s*(?:图表|柱状图|折线图|饼图|环形图|图)',
            r'(?:图表化|可视化)\s*(?:展示|显示)?',
        ],
        "convert_table": [
            r'(?:转为|改成|变成|做成)\s*表格',
            r'用\s*表格\s*(?:展示|显示|呈现)',
        ],
        "convert_flowchart": [
            r'(?:转为|改成|变成|做成)\s*流程图',
            r'用\s*流程图\s*(?:展示|显示|呈现)',
        ],
        "polish_text": [
            r'(?:润色|润饰|改写|重写|优化)\s*(?:文字|文案|内容)?',
            r'(?:把|将)\s*(?:文字|内容)\s*(?:润色|优化|改写)',
        ],
        "regenerate": [
            r'(?:重新|再次)\s*生成',
            r'(?:全部|整个|完整)\s*(?:重做|重来|刷新)',
        ],
    }

    @classmethod
    def classify(cls, instruction: str, current_slide_index: int = -1) -> Dict[str, Any]:
        """分类用户指令并返回处理方案

        Returns:
            {
                "intent": str,          # 意图类型
                "method": "direct" | "llm",  # 处理方式
                "params": dict,          # 传递给处理函数的参数
                "confidence": float,     # 置信度 0-1
            }
        """
        instruction = instruction.strip()

        for intent, patterns in cls.SIMPLE_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, instruction, re.IGNORECASE)
                if match:
                    params = cls._extract_params(intent, match, instruction, current_slide_index)
                    method = "direct" if intent in (
                        "update_title", "update_subtitle", "update_layout",
                        "add_slide", "remove_slide"
                    ) else "llm"
                    return {
                        "intent": intent,
                        "method": method,
                        "params": params,
                        "confidence": 0.85,
                    }

        # 默认 LLM 处理
        return {
            "intent": "complex",
            "method": "llm",
            "params": {"instruction": instruction, "slide_index": current_slide_index},
            "confidence": 0.3,
        }

    @classmethod
    def _extract_params(cls, intent: str, match: re.Match, instruction: str,
                        current_index: int) -> Dict[str, Any]:
        """从正则匹配中提取参数"""
        groups = match.groups()

        if intent == "update_title":
            if len(groups) >= 2:
                slide_idx = int(groups[0]) - 1 if groups[0].isdigit() else current_index
                return {"slide_index": slide_idx, "new_title": groups[-1].strip()}
            elif len(groups) == 1:
                return {"slide_index": current_index, "new_title": groups[0].strip()}

        elif intent == "update_subtitle":
            if len(groups) >= 2:
                slide_idx = int(groups[0]) - 1 if groups[0].isdigit() else current_index
                return {"slide_index": slide_idx, "new_subtitle": groups[-1].strip()}
            elif len(groups) == 1:
                return {"slide_index": current_index, "new_subtitle": groups[0].strip()}

        elif intent == "update_layout":
            layout_map = {
                "纯文本": "text_only", "图文混排": "image_right", "图左文右": "image_left",
                "三栏": "three_columns", "两栏": "two_columns", "全图": "full_image",
            }
            layout_val = groups[-1].strip() if groups else "text_only"
            layout_val = layout_map.get(layout_val, layout_val)
            slide_idx = int(groups[0]) - 1 if len(groups) >= 2 and groups[0].isdigit() else current_index
            return {"slide_index": slide_idx, "layout": layout_val}

        elif intent == "add_slide":
            insert_after = int(groups[0]) - 1 if groups and groups[0].isdigit() else current_index
            return {"insert_after": insert_after}

        elif intent == "remove_slide":
            slide_idx = int(groups[0]) - 1 if groups and groups[0].isdigit() else current_index
            return {"slide_index": slide_idx}

        elif intent in ("convert_chart", "convert_table", "convert_flowchart"):
            chart_type_map = {"柱状图": "bar", "折线图": "line", "饼图": "pie", "环形图": "doughnut"}
            chart_type = "bar"
            for cn, en in chart_type_map.items():
                if cn in instruction:
                    chart_type = en
                    break
            return {"target": "current_slide", "chart_type": chart_type}

        elif intent == "polish_text":
            return {"slide_index": current_index, "instruction": instruction}

        elif intent == "regenerate":
            return {"action": "regenerate_all"}

        return {"slide_index": current_index, "instruction": instruction}
