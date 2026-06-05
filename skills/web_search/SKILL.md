---
name: web_search
version: "1.0.0"
description: 联网搜索最新信息，支持中文和英文搜索
eligibility:
  os: [darwin, linux, win32]
  env:
    MIMO_API_KEY: "*"
tools:
  - name: search_web
    description: 执行联网搜索并返回结果摘要
    parameters:
      query:
        type: string
        description: 搜索查询关键词
        required: true
      max_results:
        type: int
        description: 最大返回结果数
        default: 5
      force_search:
        type: boolean
        description: 是否强制搜索（否则模型自主判断）
        default: false
  - name: fetch_page
    description: 获取指定 URL 的网页内容
    parameters:
      url:
        type: string
        description: 目标网页地址
        required: true
---

# Web Search Skill

## 使用方法
当用户需要查询实时信息、最新数据、或超出模型训练范围的知识时使用此 Skill。

## 触发条件
- 用户问"今天"、"最新"、"现在"、"当前"等时效性关键词
- 用户问具体事件、新闻、价格等需要联网确认的信息
- 搜索结果需要提供引用来源

## 注意事项
- Chat 端点默认关闭搜索（仅显式开启时启用）
- 非 Chat 端点（如 coding）禁用搜索以减少延迟
- 搜索结果会标注来源引用
