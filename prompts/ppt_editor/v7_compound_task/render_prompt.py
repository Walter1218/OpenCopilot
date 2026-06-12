"""
render_prompt_generator 快照 — V7 复合任务 few-shot 增强

V7 不改 system prompt 规则，只增强 few-shot 示例：
1. 新增复合任务示例（标题改写 + 图表转换 + 文案润色）
2. 新增忠实改写正反例
3. 新增 headline_rewrite 专项示例
"""

import json

RENDER_PROMPT_VERSION = "v7_compound_task"

INSTRUCTION_TYPE_MAP = {
    "柱状图": "chart", "折线图": "chart", "饼图": "chart",
    "图表": "chart", "数据可视化": "chart", "趋势": "chart", "占比": "chart",
    "表格": "table", "对比": "table", "列表": "table", "整理": "table",
    "流程图": "flowchart", "步骤": "flowchart", "流程": "flowchart", "过程": "flowchart",
    "精简": "text", "提炼": "text", "改写": "text", "扩写": "text", "总结": "text",
    # V6 新增
    "润色": "text", "专业化": "text", "正式": "text", "汇报": "text",
    # V7 新增：复合任务关键词
    "标题": "compound", "换标题": "compound",
}

# ===== V7 新增：复合任务示例 =====
COMPOUND_TASK_EXAMPLES = {
    "headline_chart_rewrite": {
        "_description": "复合任务：同时改标题 + 转图表 + 润色文案",
        "render_commands": [
            {
                "source_text": "Business Overview",
                "render_type": "text",
                "render_params": {
                    "title": "2026 H1 营收增长 32%，突破 850M",
                    "style": "conclusion_headline"
                },
                "slide_index": -1,
                "slot": "title"
            },
            {
                "source_text": "Q1 revenue was 380M RMB and Q2 revenue was 470M RMB",
                "render_type": "chart",
                "render_params": {
                    "chart_type": "bar",
                    "title": "季度营收对比",
                    "chart_data": {
                        "labels": ["Q1", "Q2"],
                        "values": [380, 470]
                    }
                },
                "slide_index": -1,
                "slot": "body"
            },
            {
                "source_text": "Revenue grew 32 percent year over year and enterprise plans led growth",
                "render_type": "text",
                "render_params": {
                    "text": "2026 H1 营收同比增长 32%，企业级订阅计划驱动主要增长",
                    "style": "professional_faithful"
                },
                "slide_index": -1,
                "slot": "body"
            }
        ]
    }
}

# ===== V7 新增：headline_rewrite 专项示例 =====
HEADLINE_REWRITE_EXAMPLES = {
    "conclusion_headline_good": {
        "_description": "正例：结论型标题改写，保留事实锚点",
        "source_text": "Business Overview",
        "render_type": "text",
        "render_params": {
            "title": "2026 H1 营收达 850M，同比增长 32%",
            "style": "conclusion_headline"
        },
        "slot": "title",
        "_note": "保留了 850M 和 32% 两个事实锚点"
    },
    "conclusion_headline_bad": {
        "_description": "反例：标题改写丢失事实锚点",
        "source_text": "Business Overview",
        "render_type": "text",
        "render_params": {
            "title": "业绩表现亮眼，增长势头强劲",
            "style": "WRONG_no_fact_anchor"
        },
        "slot": "title",
        "_note": "错误：没有任何数值或事实锚点，完全是空泛表达"
    }
}

# ===== V7 增强：忠实改写正反例（继承 V6） =====
TEXT_EXAMPLES_V7 = {
    "refine": {
        "source_text": "这段文字需要精简",
        "render_type": "text",
        "render_params": {
            "text": "精简后的文字",
            "style": "concise"
        }
    },
    "faithful_rewrite_good": {
        "source_text": "2025年营收达到12.8亿元，同比增长21.9%，其中海外市场贡献3.2亿元",
        "render_type": "text",
        "render_params": {
            "text": "2025年营收12.8亿元（同比+21.9%），海外市场贡献3.2亿元",
            "style": "professional_faithful",
            "_note": "正例：保留所有数值、百分比和时间信息"
        }
    },
    "faithful_rewrite_bad": {
        "source_text": "2025年营收达到12.8亿元，同比增长21.9%，其中海外市场贡献3.2亿元",
        "render_type": "text",
        "render_params": {
            "text": "营收实现大幅增长，海外市场表现亮眼",
            "style": "WRONG_factual_drift",
            "_note": "反例：所有数值被模糊化，这是错误的改写方式"
        }
    }
}

FAITHFUL_REWRITE_CONSTRAINTS = """
8. 改写/润色时，每条输出必须保留原文中的事实锚点（数字、金额、百分比、时间、专有名词）
9. 不得将计划/预计/目标等未来态表述改写为已完成/已实现等过去态
10. 风险、限制、负面信息必须显式保留
11. 条目数量和顺序保持不变，不合并、不拆分
12. 区间数据不可被压缩为单一数值
"""
