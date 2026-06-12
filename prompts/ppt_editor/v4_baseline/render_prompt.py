"""
render_prompt_generator 快照 — V4 Baseline

此文件是当前生产版本 RenderPromptGenerator 的完整副本，
用于 prompt 迭代实验的基准对比和随时回滚。

快照时间: 2026-06-11
来源: opencopilot/capabilities/ppt/render_prompt_generator.py
"""

# 完整副本请参见 opencopilot/capabilities/ppt/render_prompt_generator.py
# 此快照文件仅记录关键配置，完整代码回滚时从 git 或此目录恢复

RENDER_PROMPT_VERSION = "v4_baseline"

INSTRUCTION_TYPE_MAP = {
    "柱状图": "chart", "折线图": "chart", "饼图": "chart",
    "图表": "chart", "数据可视化": "chart", "趋势": "chart", "占比": "chart",
    "表格": "table", "对比": "table", "列表": "table", "整理": "table",
    "流程图": "flowchart", "步骤": "flowchart", "流程": "flowchart", "过程": "flowchart",
    "精简": "text", "提炼": "text", "改写": "text", "扩写": "text", "总结": "text",
}

# V4 版本 text 类型仅有 1 个简单示例，无忠实改写正反例
TEXT_EXAMPLES_V4 = {
    "refine": {
        "source_text": "这段文字需要精简",
        "render_type": "text",
        "render_params": {
            "text": "精简后的文字",
            "style": "concise"
        }
    }
}

# V4 版本无复合任务示例、无 headline_rewrite 专项示例
# 这些将在 v5/v6/v7 迭代中逐步增强
