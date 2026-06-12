"""
ppt_editor system prompt 快照 — V7 复合任务 few-shot 增强

V7 不改 system prompt 规则（与 V6 完全一致），
只增强 render_prompt_generator 的 few-shot 示例。
因此此文件内容与 V6 相同。

迭代时间: 2026-06-11
"""

# V7 system prompt 与 V6 完全一致
# 本轮只改 render_prompt_generator（见 render_prompt.py）
# 导入 V6 的 prompt 作为基准
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v6_structure'))
from system_prompt import PPT_EDITOR_SYSTEM_PROMPT_V6 as PPT_EDITOR_SYSTEM_PROMPT_V7
