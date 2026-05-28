import os
from pptx import Presentation

text = """
# 智能体发展年度报告
这是2026年针对AI智能体发展情况的详细分析。

## 第一季度核心突破
### 算法层面
- **大模型**推理能力显著提升
- 成功解决了上下文丢失的问题
- 提出了新的强化学习路线

### 工程层面
1. 优化了系统的冷启动速度
2. 实现了 100ms 以内的响应延迟

## 未来规划
- 增加多模态支持
- 引入**视觉识别**与图文排版
"""

from ppt_generator import generate_ppt_from_text

if __name__ == "__main__":
    out_path = generate_ppt_from_text(text, "test_presentation.pptx")
    print(f"Generated at {out_path}")
