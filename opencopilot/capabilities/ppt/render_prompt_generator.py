"""
渲染指令 Prompt 生成器

根据用户指令和上下文动态生成针对性的 Prompt，提高 AI 理解渲染指令的成功率。
"""

import re
from typing import List, Dict, Any, Optional


class RenderPromptGenerator:
    """
    渲染指令 Prompt 生成器
    
    根据用户指令类型，生成针对性的示例和说明。
    """
    
    # 指令类型 → 渲染类型映射
    INSTRUCTION_TYPE_MAP = {
        # 图表相关
        "柱状图": "chart",
        "折线图": "chart",
        "饼图": "chart",
        "图表": "chart",
        "数据可视化": "chart",
        "趋势": "chart",
        "占比": "chart",
        
        # 表格相关
        "表格": "table",
        "对比": "table",
        "列表": "table",
        "整理": "table",
        
        # 流程图相关
        "流程图": "flowchart",
        "步骤": "flowchart",
        "流程": "flowchart",
        "过程": "flowchart",
        
        # 文本相关
        "精简": "text",
        "提炼": "text",
        "改写": "text",
        "扩写": "text",
        "总结": "text",
    }
    
    # 渲染类型 → 示例
    RENDER_TYPE_EXAMPLES = {
        "chart": {
            "bar": {
                "source_text": "2025年营收12.8亿元，2024年营收10.5亿元",
                "render_type": "chart",
                "render_params": {
                    "chart_type": "bar",
                    "title": "营收对比",
                    "chart_data": {
                        "labels": ["2024年", "2025年"],
                        "values": [10.5, 12.8]
                    }
                }
            },
            "line": {
                "source_text": "Q1营收2.8亿，Q2营收3.1亿，Q3营收3.5亿，Q4营收3.4亿",
                "render_type": "chart",
                "render_params": {
                    "chart_type": "line",
                    "title": "季度营收趋势",
                    "chart_data": {
                        "labels": ["Q1", "Q2", "Q3", "Q4"],
                        "values": [2.8, 3.1, 3.5, 3.4]
                    }
                }
            },
            "pie": {
                "source_text": "市场份额：A公司35%，B公司25%，C公司20%，其他20%",
                "render_type": "chart",
                "render_params": {
                    "chart_type": "pie",
                    "title": "市场份额分布",
                    "chart_data": {
                        "labels": ["A公司", "B公司", "C公司", "其他"],
                        "values": [35, 25, 20, 20]
                    }
                }
            }
        },
        "table": {
            "comparison": {
                "source_text": "方案A：成本低、周期长；方案B：成本高、周期短",
                "render_type": "table",
                "render_params": {
                    "title": "方案对比",
                    "table_data": {
                        "headers": ["维度", "方案A", "方案B"],
                        "rows": [
                            ["成本", "低", "高"],
                            ["周期", "长", "短"]
                        ]
                    }
                }
            },
            "list": {
                "source_text": "团队成员：张三-前端，李四-后端，王五-设计",
                "render_type": "table",
                "render_params": {
                    "title": "团队成员",
                    "table_data": {
                        "headers": ["姓名", "角色"],
                        "rows": [
                            ["张三", "前端"],
                            ["李四", "后端"],
                            ["王五", "设计"]
                        ]
                    }
                }
            }
        },
        "flowchart": {
            "process": {
                "source_text": "1.需求分析 2.架构设计 3.编码实现 4.测试验证 5.部署上线",
                "render_type": "flowchart",
                "render_params": {
                    "title": "开发流程",
                    "flowchart_data": {
                        "nodes": [
                            {"id": "1", "label": "需求分析", "type": "start"},
                            {"id": "2", "label": "架构设计", "type": "process"},
                            {"id": "3", "label": "编码实现", "type": "process"},
                            {"id": "4", "label": "测试验证", "type": "process"},
                            {"id": "5", "label": "部署上线", "type": "end"}
                        ],
                        "edges": [
                            {"from": "1", "to": "2"},
                            {"from": "2", "to": "3"},
                            {"from": "3", "to": "4"},
                            {"from": "4", "to": "5"}
                        ]
                    }
                }
            }
        },
        "text": {
            "refine": {
                "source_text": "这段文字需要精简",
                "render_type": "text",
                "render_params": {
                    "text": "精简后的文字",
                    "style": "concise"
                }
            }
        }
    }
    
    @classmethod
    def detect_instruction_type(cls, instruction: str) -> Optional[str]:
        """
        检测用户指令类型
        
        Returns:
            渲染类型（chart/table/flowchart/text）或 None
        """
        for keyword, render_type in cls.INSTRUCTION_TYPE_MAP.items():
            if keyword in instruction:
                return render_type
        return None
    
    @classmethod
    def generate_example_for_type(cls, render_type: str) -> Dict[str, Any]:
        """
        为指定渲染类型生成示例
        
        Returns:
            示例数据
        """
        examples = cls.RENDER_TYPE_EXAMPLES.get(render_type, {})
        if examples:
            # 返回第一个示例
            return list(examples.values())[0]
        return {}
    
    @classmethod
    def generate_prompt(
        cls,
        instruction: str,
        current_slide: Dict[str, Any],
        original_text: str = "",
        selected_text: str = ""
    ) -> str:
        """
        生成针对性的 Prompt
        
        Args:
            instruction: 用户指令
            current_slide: 当前幻灯片数据
            original_text: 原始文档文本
            selected_text: 用户选中的文本
            
        Returns:
            生成的 Prompt
        """
        # 检测指令类型
        render_type = cls.detect_instruction_type(instruction)
        
        # 构建 Prompt
        parts = []
        
        # 基础信息
        parts.append(f"用户指令：{instruction}")
        
        if selected_text:
            parts.append(f"\n用户选中的原文：\n{selected_text}")
        
        # 针对性示例
        if render_type:
            example = cls.generate_example_for_type(render_type)
            if example:
                parts.append(f"\n## 输出示例（{render_type}类型）")
                parts.append(f"```json\n{{\n  \"render_commands\": [{cls._format_example(example)}]\n}}\n```")
        
        # 通用格式说明
        parts.append("""
## 输出格式要求

必须返回 JSON 格式的渲染指令：

```json
{
  "render_commands": [
    {
      "source_text": "原文片段（必填，用于定位）",
      "render_type": "chart|table|flowchart|text",
      "render_params": {
        "title": "标题",
        // 根据 render_type 提供相应参数
      },
      "slide_index": -1,
      "slot": "body"
    }
  ]
}
```

重要：
1. source_text 必须是原文中的完整片段
2. render_type 必须是以下之一：chart, table, flowchart, text
3. chart 类型需要提供 chart_type（bar/line/pie）和 chart_data
4. table 类型需要提供 table_data（含 headers 和 rows）
5. flowchart 类型需要提供 flowchart_data（含 nodes 和 edges）
6. 默认只修改当前正在编辑的页，除非用户明确要求新增页面；此时 slide_index 必须使用当前页索引或 -1
7. 如果用户要求修改标题、headline 或结论型标题，必须输出 slot=title，并将标题文本放在 render_params.title
""")
        
        return "\n".join(parts)
    
    @classmethod
    def _format_example(cls, example: Dict[str, Any]) -> str:
        """格式化示例为 JSON 字符串"""
        import json
        return json.dumps(example, ensure_ascii=False, indent=2)


# 便捷函数
def generate_render_prompt(
    instruction: str,
    current_slide: Dict[str, Any],
    original_text: str = "",
    selected_text: str = ""
) -> str:
    """生成渲染指令 Prompt"""
    return RenderPromptGenerator.generate_prompt(
        instruction, current_slide, original_text, selected_text
    )
