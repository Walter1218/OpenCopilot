"""
PPT 生成器 - 统一从项目根目录 ppt_generator.py 导入

此文件保留为薄封装层，避免重复维护两套代码。
所有核心逻辑（JSON 解析、修复、图表注入、主题应用等）
统一由根目录 ppt_generator.py 提供。
"""

import os
import sys

# 将项目根目录加入 sys.path，以便从根目录 ppt_generator.py 导入
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

# 从根目录 ppt_generator.py 统一导入所有公开函数
from ppt_generator import (
    clean_markdown,
    apply_corporate_theme,
    format_title_slide,
    format_content_slide,
    format_chart_slide,
    generate_ppt_from_json,
    extract_json_from_text,
    generate_ppt_from_text,
    parse_inline_formatting,
    _apply_formatted_paragraph,
    add_placeholder_image,
)

# 保留向后兼容的 __all__ 声明
__all__ = [
    "clean_markdown",
    "apply_corporate_theme",
    "format_title_slide",
    "format_content_slide",
    "format_chart_slide",
    "generate_ppt_from_json",
    "extract_json_from_text",
    "generate_ppt_from_text",
    "parse_inline_formatting",
    "_apply_formatted_paragraph",
    "add_placeholder_image",
]


if __name__ == "__main__":
    pass
