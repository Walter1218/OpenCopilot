# OpenCopilot UI 组件集成与运行指南

> **版本**：v2.0 | **日期**：2026-05-28 | **分支**：ai-assistant-dev-office  
> **状态**：阶段1-4已实现，文件拖拽功能已验证通过

---

## 一、新组件概览

本次迭代开发的 UI 组件：

| 组件 | 文件 | 功能 |
|------|------|------|
| ThemeManager | `core/theme_manager.py` | 主题管理（暗色/亮色/办公） |
| ShortcutManager | `core/shortcut_manager.py` | 快捷键管理 |
| FileDropZone | `widgets/file_drop_zone.py` | 文件拖拽区 |
| ProgressWidget | `widgets/progress_widget.py` | 单步/多步骤进度条 |
| ContextMenu | `widgets/context_menu.py` | 右键上下文菜单 |
| SettingsDialog | `widgets/settings_dialog.py` | 设置对话框 |
| BatchDialog | `widgets/batch_dialog.py` | 批量处理界面 |
| TerminologyDialog | `widgets/terminology_dialog.py` | 术语库管理 |
| TranslationMemory | `widgets/translation_memory.py` | 翻译记忆系统 |

---

## 二、组件独立运行

### 2.1 主题系统

```python
from core.theme_manager import ThemeManager

# 初始化
theme_manager = ThemeManager()

# 获取当前主题
current = theme_manager.get_current_theme()
print(f"当前主题: {current['name']}")

# 切换主题
theme_manager.switch_theme("light")  # 可选: dark, light, office

# 获取主题配置
config = theme_manager.get_theme_config("dark")
print(config)  # {'background': '#2b2b2b', 'text': '#ffffff', ...}
```

### 2.2 快捷键系统

```python
from core.shortcut_manager import ShortcutManager

# 初始化
shortcut_manager = ShortcutManager()

# 注册快捷键
shortcut_manager.register_shortcut(
    "cmd+shift+t",
    name="翻译模式",
    action="open_translation"
)

# 检查冲突
has_conflict = shortcut_manager.check_conflict("cmd+shift+space")

# 获取所有快捷键
all_shortcuts = shortcut_manager.get_all_shortcuts()
```

### 2.3 文件拖拽区

```python
from PyQt6.QtWidgets import QApplication, QMainWindow
from widgets.file_drop_zone import FileDropZone
import sys

app = QApplication(sys.argv)

# 创建拖拽区
drop_zone = FileDropZone()
drop_zone.show()

# 监听文件拖入信号
drop_zone.file_dropped.connect(lambda file_info: print(f"拖入文件: {file_info}"))

app.exec()
```

### 2.4 进度组件

```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from widgets.progress_widget import ProgressWidget, MultiStepProgressWidget
import sys

app = QApplication(sys.argv)
window = QMainWindow()
central = QWidget()
layout = QVBoxLayout(central)

# 单步进度条
progress = ProgressWidget()
progress.set_total(100)
progress.start("正在处理...")
progress.update(50)  # 更新到50%
progress.complete("完成!")

# 多步骤进度条
multi_progress = MultiStepProgressWidget()
multi_progress.add_step("步骤1", "读取文件")
multi_progress.add_step("步骤2", "解析内容")
multi_progress.add_step("步骤3", "生成结果")
multi_progress.start()

layout.addWidget(progress)
layout.addWidget(multi_progress)
window.setCentralWidget(central)
window.show()
app.exec()
```

### 2.5 右键菜单

```python
from PyQt6.QtWidgets import QApplication, QMainWindow
from widgets.context_menu import TextContextMenu, FileContextMenu, CodeContextMenu
import sys

app = QApplication(sys.argv)

# 文本右键菜单
text_menu = TextContextMenu()
text_menu.set_selected_text("Hello World")
action = text_menu.exec(QCursor.pos())
if action:
    print(f"选择了: {action.text()}")

# 文件右键菜单
file_menu = FileContextMenu("/path/to/file.docx")
action = file_menu.exec(QCursor.pos())

# 代码右键菜单
code_menu = CodeContextMenu("print('hello')", "python")
action = code_menu.exec(QCursor.pos())
```

### 2.6 设置对话框

```python
from PyQt6.QtWidgets import QApplication
from widgets.settings_dialog import SettingsDialog
import sys

app = QApplication(sys.argv)

# 打开设置对话框
dialog = SettingsDialog()
dialog.show()

# 监听设置变更信号
dialog.settings_changed.connect(lambda settings: print(f"设置变更: {settings}"))

app.exec()
```

### 2.7 批量处理

```python
from PyQt6.QtWidgets import QApplication
from widgets.batch_dialog import BatchDialog
import sys

app = QApplication(sys.argv)

# 打开批量处理对话框
dialog = BatchDialog()
dialog.show()

# 添加文件
dialog.add_file("/path/to/file1.docx")
dialog.add_file("/path/to/file2.pdf")

# 监听处理完成信号
dialog.processing_finished.connect(lambda results: print(f"处理完成: {len(results)}个文件"))

app.exec()
```

### 2.8 术语库管理

```python
from PyQt6.QtWidgets import QApplication
from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
import sys

app = QApplication(sys.argv)

# 打开术语库对话框
dialog = TerminologyDialog()
dialog.show()

# 添加术语
entry = TerminologyEntry(
    source="人工智能",
    target="Artificial Intelligence",
    category="技术"
)
dialog.add_entry(entry)

# 搜索术语
results = dialog.search_entries("人工智能")
print(f"找到 {len(results)} 个结果")

app.exec()
```

### 2.9 翻译记忆

```python
from widgets.translation_memory import TranslationMemory, TranslationUnit

# 初始化
memory = TranslationMemory()

# 添加翻译单元
unit = TranslationUnit(
    source="Hello",
    target="你好",
    source_lang="en",
    target_lang="zh"
)
memory.add_unit(unit)

# 搜索相似翻译
results = memory.search("Hello", threshold=0.8)
for result in results:
    print(f"{result.source} -> {result.target} (相似度: {result.score})")

# 导出/导入
memory.export_json("memory.json")
memory.import_json("memory.json")
```

---

## 三、集成到主界面

### 3.1 在 smart_copilot.py 中集成

```python
# 在 smart_copilot.py 顶部添加导入
from core.theme_manager import ThemeManager
from core.shortcut_manager import ShortcutManager
from widgets.file_drop_zone import FileDropZone
from widgets.progress_widget import ProgressWidget, MultiStepProgressWidget
from widgets.context_menu import TextContextMenu
from widgets.settings_dialog import SettingsDialog
from widgets.batch_dialog import BatchDialog

class AICardWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化快捷键管理器
        self.shortcut_manager = ShortcutManager()
        
        # 创建文件拖拽区
        self.file_drop_zone = FileDropZone()
        self.file_drop_zone.file_dropped.connect(self.on_file_dropped)
        
        # 创建进度条
        self.progress_widget = ProgressWidget()
        
        # ... 其他初始化代码
    
    def on_file_dropped(self, file_info):
        """处理文件拖入"""
        # 自动识别文件类型并进入对应模式
        if file_info.endswith('.docx'):
            self.open_document_revision(file_info)
        elif file_info.endswith('.pdf'):
            self.open_pdf_processing(file_info)
        # ...
    
    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog()
        dialog.settings_changed.connect(self.apply_settings)
        dialog.exec()
    
    def open_batch_processing(self):
        """打开批量处理"""
        dialog = BatchDialog()
        dialog.exec()
```

### 3.2 应用主题

```python
def apply_theme(self, theme_name):
    """应用主题到所有组件"""
    config = self.theme_manager.get_theme_config(theme_name)
    
    # 更新主窗口样式
    self.setStyleSheet(f"""
        QWidget {{
            background-color: {config['background']};
            color: {config['text']};
        }}
        QPushButton {{
            background-color: {config['button']};
            border-radius: 4px;
            padding: 8px;
        }}
    """)
    
    # 更新所有子组件
    for widget in self.findChildren(QWidget):
        widget.update()
```

### 3.3 注册快捷键

```python
def setup_shortcuts(self):
    """设置快捷键"""
    shortcuts = {
        "cmd+shift+space": self.toggle_visibility,
        "cmd+shift+t": self.open_translation_mode,
        "cmd+shift+p": self.open_polish_mode,
        "cmd+shift+r": self.open_revision_mode,
        "cmd+shift+s": self.open_settings,
    }
    
    for key, callback in shortcuts.items():
        self.shortcut_manager.register_shortcut(key, callback)
```

---

## 四、测试运行

### 4.1 运行单元测试

```bash
# 运行所有测试
python -m pytest tests/unit/ -v

# 运行覆盖率提升测试
python -m pytest tests/unit/test_coverage_boost.py -v

# 运行真实环境测试
python -m pytest tests/unit/test_real_environment.py -v
```

### 4.2 统计覆盖率

```bash
# 运行覆盖率统计
python -m coverage run -m pytest tests/unit/ -q

# 查看覆盖率报告
python -m coverage report --include="core/*,widgets/*,dialogs/*"

# 生成HTML报告
python -m coverage html
```

### 4.3 测试覆盖率结果

| 模块 | 覆盖率 |
|------|--------|
| `core/theme_manager.py` | 86% |
| `widgets/progress_widget.py` | 90% |
| `widgets/settings_dialog.py` | 84% |
| `widgets/context_menu.py` | 82% |
| `widgets/file_drop_zone.py` | 70% |
| `widgets/terminology_dialog.py` | 68% |
| `widgets/batch_dialog.py` | 63% |
| `widgets/translation_memory.py` | 43% |
| **总计** | **64%** |

---

## 五、组件交互示例

### 5.1 文件拖拽 + 进度条 + 批量处理

```python
def on_file_dropped(self, file_info):
    """文件拖入处理流程"""
    # 显示进度条
    self.progress_widget.show()
    self.progress_widget.start(f"正在处理: {file_info.name}")
    
    # 处理文件
    try:
        result = self.process_file(file_info)
        self.progress_widget.complete("处理完成!")
        
        # 显示结果
        self.show_result(result)
    except Exception as e:
        self.progress_widget.set_error(f"处理失败: {str(e)}")
```

### 5.2 翻译 + 术语库 + 翻译记忆

```python
def translate_with_context(self, text):
    """带术语库和翻译记忆的翻译"""
    # 1. 检查翻译记忆
    memory_results = self.translation_memory.search(text, threshold=0.9)
    if memory_results:
        return memory_results[0].target
    
    # 2. 获取术语库
    terms = self.terminology_dialog.get_all_terms()
    
    # 3. 调用翻译API
    result = self.call_translation_api(text, terms=terms)
    
    # 4. 保存到翻译记忆
    unit = TranslationUnit(
        source=text,
        target=result,
        source_lang="en",
        target_lang="zh"
    )
    self.translation_memory.add_unit(unit)
    
    return result
```

---

## 六、配置说明

### 6.1 主题配置

配置文件位置：`~/.asu_copilot/themes.json`

```json
{
  "themes": {
    "dark": {
      "name": "暗色主题",
      "background": "#2b2b2b",
      "text": "#ffffff",
      "button": "#3d3d3d",
      "accent": "#4a9eff"
    },
    "light": {
      "name": "亮色主题",
      "background": "#ffffff",
      "text": "#333333",
      "button": "#f0f0f0",
      "accent": "#007aff"
    },
    "office": {
      "name": "办公主题",
      "background": "#f5f5f5",
      "text": "#2c3e50",
      "button": "#e8e8e8",
      "accent": "#2b579a"
    }
  },
  "current": "dark"
}
```

### 6.2 快捷键配置

配置文件位置：`~/.asu_copilot/shortcuts.json`

```json
{
  "shortcuts": {
    "cmd+shift+space": {
      "name": "唤醒/隐藏卡片",
      "action": "toggle_visibility"
    },
    "cmd+shift+t": {
      "name": "翻译模式",
      "action": "open_translation"
    },
    "cmd+shift+p": {
      "name": "润色模式",
      "action": "open_polish"
    },
    "cmd+shift+r": {
      "name": "文档修订模式",
      "action": "open_revision"
    },
    "cmd+shift+s": {
      "name": "打开设置",
      "action": "open_settings"
    }
  }
}
```

### 6.3 翻译记忆配置

配置文件位置：`~/.asu_copilot/translation_memory/`

```
translation_memory/
├── memory.json          # 翻译记忆数据
├── memory.json.bak      # 备份文件
└── exports/             # 导出文件目录
```

---

## 七、故障排查

### 7.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 主题切换无效 | 样式表未更新 | 调用 `apply_theme()` |
| 快捷键冲突 | 系统快捷键占用 | 检查系统偏好设置 |
| 文件拖拽无反应 | 权限问题 | 检查辅助功能权限 |
| 进度条不更新 | 线程问题 | 使用信号槽机制 |
| 术语库导入失败 | 文件格式错误 | 检查JSON/TMX格式 |

### 7.2 调试模式

```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看组件状态
print(f"当前主题: {theme_manager.current_theme}")
print(f"快捷键列表: {shortcut_manager.get_all_shortcuts()}")
print(f"翻译记忆数量: {len(memory.units)}")
```

---

## 附录：快速命令速查

| 命令 | 说明 |
|------|------|
| `python -m pytest tests/unit/ -v` | 运行所有测试 |
| `python -m pytest tests/unit/test_coverage_boost.py -v` | 运行覆盖率测试 |
| `python -m coverage run -m pytest tests/unit/ -q` | 统计覆盖率 |
| `python -m coverage report --include="core/*,widgets/*,dialogs/*"` | 查看覆盖率报告 |
