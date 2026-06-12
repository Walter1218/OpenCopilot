"""
render_prompt_generator 快照 — V6 结构保持

V6 在 V5 基础上，为 text 类型新增「忠实改写」示例。
"""

import json

RENDER_PROMPT_VERSION = "v6_structure"

INSTRUCTION_TYPE_MAP = {
    "柱状图": "chart", "折线图": "chart", "饼图": "chart",
    "图表": "chart", "数据可视化": "chart", "趋势": "chart", "占比": "chart",
    "表格": "table", "对比": "table", "列表": "table", "整理": "table",
    "流程图": "flowchart", "步骤": "flowchart", "流程": "flowchart", "过程": "flowchart",
    "精简": "text", "提炼": "text", "改写": "text", "扩写": "text", "总结": "text",
    # V6 新增：忠实改写关键词
    "润色": "text", "专业化": "text", "正式": "text", "汇报": "text",
}

# V6 新增：忠实改写示例（before/after 对照）
TEXT_EXAMPLES_V6 = {
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

# V6 在通用格式说明末尾追加的忠实改写约束
FAITHFUL_REWRITE_CONSTRAINTS = """
8. 改写/润色时，每条输出必须保留原文中的事实锚点（数字、金额、百分比、时间、专有名词）
9. 不得将计划/预计/目标等未来态表述改写为已完成/已实现等过去态
10. 风险、限制、负面信息必须显式保留
11. 条目数量和顺序保持不变，不合并、不拆分
12. 区间数据不可被压缩为单一数值
"""
