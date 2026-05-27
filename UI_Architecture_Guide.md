# OpenCopilot UI 架构说明

> **版本**：v2.0 | **日期**：2026-05-28  
> **状态**：阶段1-4已实现，文件拖拽功能已验证通过

---

## 一、组件架构总览

```
smart_copilot.py (主程序)
├── 旧组件 (保留)
│   ├── SettingsDialog (LLM引擎配置)
│   ├── ModelScannerWorker (模型扫描)
│   └── AICardWindow (主卡片窗口)
│
└── 新组件 (新增)
    ├── core/theme_manager.py (主题管理)
    ├── core/shortcut_manager.py (快捷键管理)
    ├── widgets/settings_dialog.py (个性化设置)
    ├── widgets/file_drop_zone.py (文件拖拽区)
    ├── widgets/progress_widget.py (进度条)
    ├── widgets/context_menu.py (右键菜单)
    ├── widgets/batch_dialog.py (批量处理)
    ├── widgets/terminology_dialog.py (术语库)
    └── widgets/translation_memory.py (翻译记忆)
```

---

## 二、新旧组件关系

### 2.1 设置对话框

| 组件 | 位置 | 功能 | 用途 |
|------|------|------|------|
| 旧 SettingsDialog | smart_copilot.py | LLM引擎配置 | 配置MiniMax/Ollama |
| 新 SettingsDialog | widgets/settings_dialog.py | 个性化设置 | 主题/字体/行为设置 |

**融合方式**：统一设置入口，两个标签页

```
设置对话框
├── 🔧 引擎设置 (旧)
│   ├── MiniMax配置
│   └── Ollama配置
├── 🎨 个性化 (新)
│   ├── 外观设置
│   ├── 行为设置
│   └── 办公设置
├── 🌈 主题 (新)
│   ├── 暗色主题
│   ├── 亮色主题
│   └── 办公主题
└── ⌨️ 快捷键 (新)
    └── 快捷键列表
```

### 2.2 主题系统

**旧方式**：硬编码样式表
```python
self.frame.setStyleSheet("""
    QFrame {
        background-color: rgba(30, 30, 35, 240);
        border-radius: 12px;
    }
""")
```

**新方式**：ThemeManager动态管理
```python
self.theme_manager = ThemeManager()
theme = self.theme_manager.current_theme_config
self.frame.setStyleSheet(theme.get_stylesheet())
```

**融合方案**：
- 保留旧的默认样式作为fallback
- 新组件使用ThemeManager
- 主题切换时更新所有组件

### 2.3 快捷键系统

**旧方式**：硬编码快捷键
```python
# 在AICardWindow中直接绑定
self.btn_settings.clicked.connect(self.open_settings)
```

**新方式**：ShortcutManager统一管理
```python
self.shortcut_manager = ShortcutManager()
self.shortcut_manager.register_shortcut("cmd+shift+s", self.open_settings)
```

**融合方案**：
- 新功能使用ShortcutManager
- 旧功能逐步迁移
- 保留向后兼容

---

## 三、组件集成策略

### 3.1 保留的旧组件

| 组件 | 保留原因 | 处理方式 |
|------|----------|----------|
| SettingsDialog | LLM配置功能完整 | 作为引擎设置标签页 |
| ModelScannerWorker | 模型扫描功能 | 保留不变 |
| AICardWindow | 主程序框架 | 扩展新功能 |

### 3.2 新增的组件

| 组件 | 功能 | 集成方式 |
|------|------|----------|
| ThemeManager | 主题管理 | 在__init__初始化 |
| ShortcutManager | 快捷键管理 | 在__init__初始化 |
| FileDropZone | 文件拖拽 | 添加到UI布局 |
| ProgressWidget | 进度显示 | 添加到UI布局 |
| TextContextMenu | 右键菜单 | 绑定到text_edit |
| BatchDialog | 批量处理 | 按钮触发 |
| TerminologyDialog | 术语库 | 右键菜单触发 |
| TranslationMemory | 翻译记忆 | 在__init__初始化 |

---

## 四、数据流

### 4.1 设置流程

```
用户点击设置按钮
    ↓
_open_settings()
    ↓
创建统一设置对话框
    ├── 引擎设置标签 → 旧SettingsDialog
    ├── 个性化标签 → 新SettingsDialog
    ├── 主题标签 → ThemeManager
    └── 快捷键标签 → ShortcutManager
    ↓
用户修改设置
    ↓
_apply_settings()
    ├── 应用主题 → _apply_theme()
    ├── 保存配置 → save_config()
    └── 更新UI
```

### 4.2 文件处理流程

```
用户拖入文件
    ↓
FileDropZone.file_dropped信号
    ↓
_on_file_dropped()
    ├── 显示进度条
    ├── 识别文件类型
    └── 切换处理模式
    ↓
处理完成
    └── 隐藏进度条
```

### 4.3 右键菜单流程

```
用户右键点击文本
    ↓
_show_text_context_menu()
    ├── 创建TextContextMenu
    ├── 添加自定义菜单项
    └── 显示菜单
    ↓
用户选择菜单项
    ├── 翻译 → trigger_ai("translate")
    ├── 润色 → trigger_ai("polish")
    ├── 代码解析 → trigger_ai("code")
    ├── 术语库 → _open_terminology_dialog()
    └── 翻译记忆 → _open_translation_memory_dialog()
```

---

## 五、配置文件

### 5.1 旧配置

位置：`~/.asu_copilot/config.json`
```json
{
  "minimax_api_key": "...",
  "local_api_base": "http://localhost:11434/v1",
  "local_model": "llama3"
}
```

### 5.2 新配置

位置：`~/.opencopilot/`
```
~/.opencopilot/
├── theme_config.json      # 主题配置
├── shortcut_config.json   # 快捷键配置
├── settings.json          # 个性化设置
└── translation_memory/    # 翻译记忆
```

---

## 六、迁移计划

### 6.1 短期（当前）

- ✅ 保留旧SettingsDialog
- ✅ 新增主题系统
- ✅ 新增快捷键系统
- ✅ 新增文件拖拽区
- ✅ 新增进度条
- ✅ 新增右键菜单

### 6.2 中期（1-2周）

- [ ] 统一配置文件位置
- [ ] 迁移旧配置到新格式
- [ ] 完善主题切换动画
- [ ] 添加快捷键自定义界面

### 6.3 长期（1个月）

- [ ] 完全重构设置系统
- [ ] 统一所有组件样式
- [ ] 添加插件系统
- [ ] 支持自定义主题

---

## 七、常见问题

### 7.1 为什么保留两套设置对话框？

**原因**：
- 旧的SettingsDialog功能完整，负责LLM引擎配置
- 新的SettingsDialog专注于个性化设置
- 两套系统职责不同，不宜强行合并

**解决方案**：
- 使用标签页组织
- 用户可以在一个界面访问所有设置

### 7.2 主题切换为什么没有生效？

**可能原因**：
- 旧组件使用硬编码样式
- 主题切换只更新了新组件

**解决方案**：
- 检查组件是否使用ThemeManager
- 手动调用_apply_theme()

### 7.3 快捷键冲突怎么办？

**处理方式**：
- 系统快捷键（Cmd+C/V等）不允许修改
- 用户快捷键冲突时显示警告
- 建议用户更换快捷键

---

## 八、开发指南

### 8.1 添加新组件

1. 在 `widgets/` 目录创建新文件
2. 在 `smart_copilot.py` 顶部添加导入
3. 在 `AICardWindow.__init__` 中初始化
4. 在 `initUI` 中添加到布局
5. 添加信号连接

### 8.2 使用主题

```python
# 获取当前主题
theme = self.theme_manager.current_theme_config

# 应用样式
widget.setStyleSheet(theme.get_stylesheet())

# 监听主题变化
self.theme_manager.theme_changed.connect(self._on_theme_changed)
```

### 8.3 使用快捷键

```python
# 注册快捷键
self.shortcut_manager.register_shortcut(
    "cmd+shift+t",
    name="翻译模式",
    action="open_translation",
    callback=self.trigger_ai.bind(None, "translate")
)

# 获取快捷键
shortcut = self.shortcut_manager.get_shortcut("cmd+shift+t")
```

---

## 附录：组件清单

| 组件 | 文件 | 状态 | 说明 |
|------|------|------|------|
| SettingsDialog (旧) | smart_copilot.py | 保留 | LLM引擎配置 |
| SettingsDialog (新) | widgets/settings_dialog.py | 新增 | 个性化设置 |
| ThemeManager | core/theme_manager.py | 新增 | 主题管理 |
| ShortcutManager | core/shortcut_manager.py | 新增 | 快捷键管理 |
| FileDropZone | widgets/file_drop_zone.py | 新增 | 文件拖拽 |
| ProgressWidget | widgets/progress_widget.py | 新增 | 进度条 |
| TextContextMenu | widgets/context_menu.py | 新增 | 右键菜单 |
| BatchDialog | widgets/batch_dialog.py | 新增 | 批量处理 |
| TerminologyDialog | widgets/terminology_dialog.py | 新增 | 术语库 |
| TranslationMemory | widgets/translation_memory.py | 新增 | 翻译记忆 |
