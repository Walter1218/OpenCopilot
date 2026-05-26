# ASU v2.0 Release Notes - June 2026

## Overview

ASU v2.0 is a major release focusing on document intelligence and privilege broker stability. This release includes 3 new features, 12 bug fixes, and 2 breaking changes.

## New Features

### Document Revision Mode (BETA)
- Context-aware document revision with cross-reference impact detection
- Supports .md, .docx, .pptx via Privileged Broker
- Output structured in 3 blocks: revised text, impact analysis, revision notes

### Privileged Broker v1.1
-新增 capabilities discovery endpoint (`GET /api/v1/system/capabilities`)

###说明
-请注意特权代理需在原生终端运行
-中文和英文的混合表达
-术语使用要统一："特权代理"和"超级代理"指的是同一概念
-文档里出现"特权代理"3次，"超级代理"1次，"Privileged Broker"5次

### Office File Parsing
- Broker now supports .docx and .pptx text extraction via `POST /api/v1/system/fs/office/read`

## Breaking Changes

1. `config.json` 的 `minimax_api_key` 字段已更名为 `api_key`。旧配置文件需要手动迁移。
2. `smart_copilot.py` 移除了对 OpenClaw CLI 的依赖。如果仍在引用 `OpenClawServerProvider`，请改用 `ASUCustomAgentClient`。

## Bug Fixes

- Fixed: 拖拽文本在长文档中偶发截断 (#128)
- Fixed: macOS 15 Sequoia 下 PyQt6 窗口渲染异常 (#135)
- Fixed: `system_probe_client.py` 中 Broker 超时后未释放连接 (#142)

## Known Issues

- Windows 平台暂不支持（仅 macOS 15+）
- MiniMax API 在长上下文场景下偶发 20s 以上延迟

## Upgrade Guide

```bash
git pull origin main
pip install -r requirements.txt
bash scripts/install_daemon.sh
bash scripts/install_broker_daemon.sh
bash scripts/start_ui.sh
```

注意：升级后需要重新配置 `config.json`，将 `minimax_api_key` 改为 `api_key`。
