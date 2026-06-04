---
name: code_executor
version: "1.0.0"
description: 在沙箱中执行 Python/JavaScript/Shell 代码并返回结果
eligibility:
  os: [darwin, linux]
  python_version: "3.10"
tools:
  - name: execute_code
    description: 执行代码并返回输出结果
    parameters:
      code:
        type: string
        description: 要执行的代码
        required: true
      language:
        type: string
        description: 编程语言 (python/javascript/shell)
        default: python
      timeout:
        type: int
        description: 超时时间（秒）
        default: 30
  - name: analyze_code
    description: 静态分析代码质量和安全问题
    parameters:
      code:
        type: string
        description: 要分析的代码
        required: true
      language:
        type: string
        description: 编程语言
        default: python
---

# Code Executor Skill

## 使用方法
当用户要求执行代码、验证算法、测试代码片段时使用此 Skill。

## 触发条件
- 用户说"运行这段代码"、"执行这个脚本"、"测试这个函数"
- 用户提供代码要求直接执行
- 用户要求验证计算结果

## 安全策略
- 所有代码在隔离沙箱中执行
- 禁止网络访问
- 禁止文件系统写入
- 默认超时 30 秒
- 自动检测危险函数调用
