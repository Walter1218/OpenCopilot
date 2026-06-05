# OpenCopilot 知识图谱报告

## 概览

- **实体总数**: 264
- **关系总数**: 166
- **创建时间**: 2026-05-31T13:17:00.887721
- **更新时间**: 2026-05-31T13:17:01.118937

## 实体类型分布

- **document**: 52
- **component**: 9
- **config**: 103
- **feature**: 10
- **api**: 90

## 关系类型分布

- **documents**: 161
- **depends_on**: 3
- **communicates_with**: 1
- **configures**: 1

## 核心组件

- **ASU Custom Agent**: 智能体核心代码
- **Persona System**: 角色人设系统
- **Smart Copilot Platform**: 能力平台API
- **IDE Extension**: IDE扩展模块
- **Smart Copilot UI**: 主程序UI
- **Context Envelope**: 统一上下文协议
- **Context Window Manager**: 上下文窗口管理器
- **ASU Broker**: 特权代理模块
- **Smart Copilot API**: 旧版API

## API端点

共找到 90 个API端点

### REST API

- `/api/execute`
- `/health`
- `/api/execute/stream`
- `/api/probe/status`
- `/api/probe/clipboard`
- ... 还有 51 个

### Context API

- `/api/context/current`
- `/api/context/inject`
- `/api/context/history`
- `/api/context/history?limit=10`

### PPT API

- `/api/ppt/generate`
- `/api/ppt/from-context`
- `/api/ppt/analyze`
- `/api/ppt/style/check`
- `/api/ppt/suggest`
- ... 还有 8 个

### Agent API

- `/v1/agent/chat`
- `/v1/agent/session/clear`
- `/v1/agent/sessions`
- `/v1/agent/personas`
- `/v1/agent/personas/reload`
- ... 还有 2 个

### Broker API

- `/api/v1/system/frontmost`
- `/api/v1/system/clipboard`
- `/api/v1/system/selection`
- `/api/v1/system/screen/front`
- `/api/v1/system/fs/read`
- ... 还有 5 个

