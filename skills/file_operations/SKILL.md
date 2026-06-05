---
name: file_operations
version: "1.0.0"
description: 读取、列出、搜索项目文件
eligibility:
  os: [darwin, linux, win32]
tools:
  - name: list_directory
    description: 列出目录中的文件和子目录
    parameters:
      path:
        type: string
        description: 目录路径
        required: true
      pattern:
        type: string
        description: 文件匹配模式 (如 *.py)
        required: false
  - name: read_file
    description: 读取文件内容
    parameters:
      filepath:
        type: string
        description: 文件路径
        required: true
      max_lines:
        type: int
        description: 最大读取行数
        default: 500
  - name: search_content
    description: 在文件中搜索文本内容
    parameters:
      pattern:
        type: string
        description: 搜索模式 (支持正则)
        required: true
      directory:
        type: string
        description: 搜索目录
        required: false
      file_pattern:
        type: string
        description: 文件名过滤 (如 *.py)
        required: false
---

# File Operations Skill

## 使用方法
当用户需要浏览项目文件、读取代码、搜索内容时使用此 Skill。

## 触发条件
- 用户问"查看 XX 文件"、"列出目录"
- 用户要求"搜索包含 XX 的文件"
- 用户需要"读取配置"、"查看日志"

## 安全策略
- 仅限项目工作区内的文件访问
- 禁止访问系统敏感目录 (/etc, /usr, ~/.ssh 等)
- 大文件自动截断显示
