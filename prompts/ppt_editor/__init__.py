"""
PPT Editor Prompt 版本管理

此目录管理 ppt_editor prompt 的版本快照，支持迭代实验和随时回滚。

版本历史:
  v4_baseline  -- 当前生产版本（动态 few-shot + 强规则）
  v5_fact_anchor -- 新增事实锚点硬约束
  v6_structure   -- 新增结构保持与条目粒度约束
  v7_compound_task -- 复合任务 few-shot 增强

回滚方法:
  将目标版本目录下的 system_prompt.py 内容复制回
  opencopilot/shared/prompt.py 的 CONTEXT_DESCRIPTIONS["ppt_editor"]，
  并更新 PPT_EDITOR_PROMPT_VERSION 常量。
"""
