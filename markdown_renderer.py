"""Markdown 渲染工具：将 AI 回复文本转换为带语法高亮的 HTML。

使用 markdown 库 + Pygments 代码高亮，
输出适配 QTextEdit 暗色主题的 HTML。
"""

import re
import html as html_module

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension

# Pygments 暗色主题 CSS（精简版，适配 ASU 暗色 UI）
PYGMENTS_DARK_CSS = """
<style>
.codehilite { background: #1e1e2e; border-radius: 8px; padding: 12px 14px; margin: 8px 0; overflow-x: auto; }
.codehilite pre { margin: 0; font-family: 'SF Mono', 'Menlo', 'Monaco', monospace; font-size: 12px; line-height: 1.5; }
.codehilite .hll { background-color: #49483e }
.codehilite .c { color: #6c7086 } /* Comment */
.codehilite .k { color: #cba6f7 } /* Keyword */
.codehilite .s { color: #a6e3a1 } /* String */
.codehilite .n { color: #cdd6f4 } /* Name */
.codehilite .o { color: #89b4fa } /* Operator */
.codehilite .p { color: #bac2de } /* Punctuation */
.codehilite .mi { color: #fab387 } /* Number */
.codehilite .nb { color: #f38ba8 } /* Builtin */
.codehilite .nf { color: #89b4fa } /* Function */
.codehilite .nc { color: #f9e2af } /* Class */
.codehilite .nd { color: #f9e2af } /* Decorator */
.codehilite .bp { color: #f38ba8 } /* Builtin pseudo */
.codehilite .ow { color: #cba6f7 } /* Operator word */
.codehilite .err { color: #f38ba8; background-color: #1e1e2e } /* Error */
</style>
"""

# 全局 markdown 转换器实例
_md = markdown.Markdown(
    extensions=[
        FencedCodeExtension(),
        CodeHiliteExtension(
            noclasses=False,
            pygments_style='default',
            guess_lang=True,
        ),
        'tables',
    ]
)


def render(text: str) -> str:
    """将 Markdown 文本转换为暗色主题 HTML。

    处理 AI 回复中常见的格式：
    - ```代码块``` → 语法高亮
    - **粗体**、*斜体*
    - `行内代码`
    - 无序/有序列表
    - 表格
    """
    if not text:
        return ""
    # 重置转换器状态（markdown 库有内部状态）
    _md.reset()
    # HTML 实体转义后转换
    body = _md.convert(text)
    return PYGMENTS_DARK_CSS + body
