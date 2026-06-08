---
name: content_convert
version: "1.0.0"
description: 将选定文本智能转换为表格、图表、流程图等结构化可视化形式
eligibility:
  os: [darwin, linux, win32]
tools:
  - name: analyze_and_convert
    description: 自动分析文本结构并选择最佳转换方式（表格/图表/流程图）
    parameters:
      text:
        type: string
        description: 待分析和转换的文本内容
        required: true
      title:
        type: string
        description: 转换结果的标题（可选）
        default: ""
  - name: convert_to_table
    description: 将文本转换为结构化表格（适合对比、排名、规格参数类内容）
    parameters:
      text:
        type: string
        description: 待转换的文本内容
        required: true
      title:
        type: string
        description: 表格标题
        default: ""
  - name: convert_to_chart
    description: 将文本转换为图表（柱状图/折线图/饼图，适合数值对比、趋势、占比类内容）
    parameters:
      text:
        type: string
        description: 待转换的文本内容
        required: true
      chart_type:
        type: string
        description: 图表类型 (bar/line/pie)
        default: bar
      title:
        type: string
        description: 图表标题
        default: ""
  - name: convert_to_flowchart
    description: 将文本转换为流程图（适合步骤、阶段、审批流程类内容）
    parameters:
      text:
        type: string
        description: 待转换的文本内容
        required: true
      title:
        type: string
        description: 流程图标题
        default: ""
---

# Content Convert Skill

## 使用方法
当用户要求将选定内容转换为表格、图表、流程图等可视化形式时使用此 Skill。

## 触发条件
- 用户说"把这个转成表格"、"转成图表"、"画个流程图"
- 用户说"将这段内容可视化"、"用图表展示"
- 用户提供的内容包含明显的结构化数据（数字对比、步骤流程、分类列表等）
- 用户在 PPT 共创中要求将内容转为结构化格式

## 转换策略
- **表格**：适合对比、排名、规格参数、分类汇总类内容
- **柱状图(bar)**：适合数值对比、并列比较
- **折线图(line)**：适合趋势变化、时间序列
- **饼图(pie)**：适合占比、份额类数据
- **流程图**：适合步骤、阶段、审批流程、工作流
- **自动模式(analyze_and_convert)**：根据文本结构自动选择最佳转换方式

## 输出格式
所有转换结果均为结构化 JSON，可直接用于 PPT slide 渲染或前端展示。
