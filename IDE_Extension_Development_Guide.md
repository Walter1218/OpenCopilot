# ASU IDE Extension 开发指南

> **版本**: 1.0.0
> **更新日期**: 2026-05-30
> **兼容 VS Code**: ^1.70.0

## 概述

ASU IDE Companion 是一个 VS Code/Trae 扩展，为 OpenCopilot 提供本地 IDE 上下文获取能力。它通过 HTTP 服务器暴露当前编辑器的状态，使 OpenCopilot 能够：

- 获取当前打开的文件内容
- 读取选中的文本
- 获取诊断信息（错误、警告）
- 获取 Git diff 信息
- 获取光标所在的 AST 符号（函数、类等）
- 将修改内容回写到编辑器

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    VS Code/Trae IDE                      │
├─────────────────────────────────────────────────────────┤
│  ASU IDE Companion Extension                             │
│  ┌─────────────────────────────────────────────────────┐│
│  │  HTTP Server (127.0.0.1:随机端口)                    ││
│  │  - GET /context      获取当前文件内容                ││
│  │  - GET /selection    获取选中文本                    ││
│  │  - GET /diagnostics  获取诊断信息                    ││
│  │  - GET /git-diff     获取 Git diff                  ││
│  │  - GET /symbol       获取光标位置的符号              ││
│  │  - POST /apply       回写修改内容                    ││
│  └─────────────────────────────────────────────────────┘│
│                         │                                │
│                         ▼                                │
│              /tmp/asu_ide_port.txt                       │
│              (端口号写入临时文件)                         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              OpenCopilot Broker/Agent                    │
│              (读取端口号，调用 API)                       │
└─────────────────────────────────────────────────────────┘
```

## API 端点详解

### 1. GET /context - 获取当前文件内容

**响应格式**:
```json
{
  "fileName": "/path/to/file.py",
  "languageId": "python",
  "content": "文件完整内容..."
}
```

**使用场景**: 获取当前编辑器打开的文件，用于代码分析、重构建议等。

### 2. GET /selection - 获取选中文本

**响应格式**:
```json
{
  "text": "选中的文本内容",
  "range": {
    "startLine": 10,
    "startCol": 0,
    "endLine": 15,
    "endCol": 20
  },
  "fileName": "/path/to/file.py",
  "languageId": "python"
}
```

**使用场景**: 获取用户选中的代码片段，用于翻译、解释、重构等。

### 3. GET /diagnostics - 获取诊断信息

**响应格式**:
```json
{
  "fileName": "/path/to/file.py",
  "diagnostics": [
    {
      "severity": 0,
      "message": "Undefined variable 'x'",
      "source": "python",
      "code": "reportUndefinedVariable",
      "line": 10,
      "character": 5
    }
  ]
}
```

**severity 值说明**:
- `0`: Error（错误）
- `1`: Warning（警告）
- `2`: Information（信息）
- `3`: Hint（提示）

**使用场景**: 获取代码错误和警告，用于自动修复建议。

### 4. GET /git-diff - 获取 Git diff

**响应格式**:
```json
{
  "fileName": "/path/to/file.py",
  "diff": "diff --git a/file.py b/file.py\n...",
  "error": null
}
```

**使用场景**: 获取文件的 Git 变更，用于代码审查、变更总结等。

### 5. GET /symbol - 获取光标位置的符号

**响应格式**:
```json
{
  "name": "my_function",
  "kind": 11,
  "text": "def my_function():\n    pass",
  "range": {
    "startLine": 10,
    "startCol": 0,
    "endLine": 12,
    "endCol": 8
  }
}
```

**kind 值说明** (VS Code SymbolKind):
- `0`: File
- `1`: Module
- `2`: Namespace
- `3`: Package
- `4`: Class
- `5`: Method
- `6`: Property
- `7`: Field
- `8`: Constructor
- `9`: Enum
- `10`: Interface
- `11`: Function
- `12`: Variable
- `13`: Constant
- `14`: String
- `15`: Number
- `16`: Boolean
- `17`: Array
- `18`: Object
- `19`: Key
- `20`: Null
- `21`: EnumMember
- `22`: Struct
- `23`: Event
- `24`: Operator
- `25`: TypeParameter

**使用场景**: 获取光标所在的函数或类，用于精确的代码分析。

### 6. POST /apply - 回写修改内容

**请求格式** (全文替换):
```json
{
  "content": "新的文件完整内容..."
}
```

**请求格式** (局部替换):
```json
{
  "range": {
    "startLine": 10,
    "startCol": 0,
    "endLine": 15,
    "endCol": 20
  },
  "replace": "替换后的文本..."
}
```

**响应格式**:
```json
{
  "success": true,
  "mode": "full"
}
```

**使用场景**: 将 AI 生成的代码修改应用到编辑器。

## 安装与使用

### 从 VSIX 安装

```bash
# 1. 安装依赖
cd asu-ide-extension
npm install

# 2. 打包扩展
npm run package

# 3. 安装扩展
code --install-extension asu-ide-extension-1.0.0.vsix
```

### 开发模式

```bash
# 1. 克隆项目
cd asu-ide-extension

# 2. 安装依赖
npm install

# 3. 在 VS Code 中打开
code .

# 4. 按 F5 启动调试
```

### 验证安装

```bash
# 1. 启动 VS Code/Trae
# 2. 打开一个文件
# 3. 查看端口号
cat /tmp/asu_ide_port.txt

# 4. 测试 API
curl http://127.0.0.1:<端口号>/context
```

## 与 OpenCopilot 集成

### Broker 集成

OpenCopilot Broker 通过以下步骤获取 IDE 上下文：

1. 读取 `/tmp/asu_ide_port.txt` 获取端口号
2. 调用 `http://127.0.0.1:<端口号>/context` 获取文件内容
3. 调用 `http://127.0.0.1:<端口号>/selection` 获取选中文本
4. 将上下文传递给 Agent 进行处理

### 端口管理

- 扩展启动时自动分配随机端口
- 端口号写入 `/tmp/asu_ide_port.txt`
- 多个 Trae 窗口会竞争写入，最后激活的窗口生效
- 焦点切换时自动更新端口文件

## 开发指南

### 添加新端点

```javascript
// 在 extension.js 的 server 创建部分添加
if (req.method === 'GET' && req.url === '/new-endpoint') {
    // 实现逻辑
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ /* 响应数据 */ }));
}
```

### 错误处理

```javascript
try {
    // 业务逻辑
} catch (e) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: e.message }));
}
```

### 测试

```bash
# 使用 curl 测试
curl http://127.0.0.1:<端口号>/context
curl http://127.0.0.1:<端口号>/selection
curl http://127.0.0.1:<端口号>/diagnostics

# 使用 Python 测试
python -c "
import httpx
port = open('/tmp/asu_ide_port.txt').read().strip()
resp = httpx.get(f'http://127.0.0.1:{port}/context')
print(resp.json())
"
```

## 故障排查

### 扩展未启动

1. 检查 VS Code 开发者控制台是否有错误
2. 确认扩展已激活（查看输出面板 "ASU IDE Companion"）
3. 手动执行命令 `ASU: Start Local Context Server`

### 端口文件不存在

1. 确认扩展已启动
2. 检查临时目录权限：`ls -la /tmp/asu_ide_port.txt`
3. 手动重启扩展

### API 调用失败

1. 确认端口号正确：`cat /tmp/asu_ide_port.txt`
2. 检查防火墙设置
3. 确认 VS Code 进程正在运行

## 安全注意事项

- 服务器仅监听 `127.0.0.1`，不暴露到网络
- 无认证机制，仅限本地使用
- 不要在生产环境中暴露此服务

## 相关文件

- `asu-ide-extension/extension.js` - 扩展主文件
- `asu-ide-extension/package.json` - 扩展配置
- `asu-ide-extension/asu-ide-extension-1.0.0.vsix` - 打包后的扩展

## 相关文档

- `OpenCopilot_Broker_Development_Guide.md` - Broker 开发指南
- `Smart_Copilot_API_Guide.md` - 能力平台 API 使用指南
- `OpenCopilot_Architecture_Context_Extraction.md` - 上下文提取架构
