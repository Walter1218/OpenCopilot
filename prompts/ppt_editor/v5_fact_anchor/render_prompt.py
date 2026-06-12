"""
render_prompt_generator 快照 — V5

V5 本轮只改 system prompt（新增事实锚点硬约束），
render_prompt_generator 与 V4 baseline 完全一致，无改动。
"""

RENDER_PROMPT_VERSION = "v5_fact_anchor"

# 与 V4 baseline 完全一致，本轮无 render_prompt 改动
INSTRUCTION_TYPE_MAP = {
    "柱状图": "chart", "折线图": "chart", "饼图": "chart",
    "图表": "chart", "数据可视化": "chart", "趋势": "chart", "占比": "chart",
    "表格": "table", "对比": "table", "列表": "table", "整理": "table",
    "流程图": "flowchart", "步骤": "flowchart", "流程": "flowchart", "过程": "flowchart",
    "精简": "text", "提炼": "text", "改写": "text", "扩写": "text", "总结": "text",
}

TEXT_EXAMPLES_V5 = {
    "refine": {
        "source_text": "这段文字需要精简",
        "render_type": "text",
        "render_params": {
            "text": "精简后的文字",
            "style": "concise"
        }
    }
}
