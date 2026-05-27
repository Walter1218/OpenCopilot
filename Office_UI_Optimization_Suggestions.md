# OpenCopilot 办公场景 UI 优化建议

> **版本**：v2.0 | **日期**：2026-05-28 | **状态**：阶段1-4已实现  
> **目标**：从办公使用场景出发，分析当前UI和操作功能的不足，提出优化建议  
> **实现状态**：9个核心组件完全实现，3个对话框需要API集成

---

## 一、当前 UI 架构分析

### 1.1 技术栈
- **GUI框架**: PyQt6
- **图形效果**: QGraphicsDropShadowEffect
- **光标特效**: 自定义 CursorOverlay 层
- **鼠标监听**: pynput 库
- **通信层**: SystemProbeClient + Broker

### 1.2 当前 UI 结构
```
smart_copilot.py
├── AICardWindow (主悬浮卡片)
│   ├── 标题栏 (状态指示灯 + 设置 + 关闭)
│   ├── Tab1: 快捷划词
│   │   ├── IDE/浏览器状态栏
│   │   ├── 快捷指令按钮栏 (自动/翻译/代码解析/润色/全文修订)
│   │   ├── 自定义指令输入栏
│   │   ├── 结果显示区
│   │   └── 操作按钮栏 (复制/回写/追问)
│   └── Tab2: 连续对话
│       ├── 对话显示区
│       └── 输入发送栏
├── SettingsDialog (设置对话框)
└── CursorOverlay (光标特效层)
```

### 1.3 办公场景相关功能
1. **文档修订模式**: 支持 .docx/.pptx 文件处理
2. **Persona 系统**: 办公场景 Persona (商务邮件、学术论文、技术文档等)
3. **工具调用**: 文件处理、文本提取、格式转换
4. **全文上下文**: IDE 全文读取、浏览器 DOM 读取

---

## 二、办公场景 UI 不足分析

### 2.1 视觉设计不足

#### 2.1.1 主题单一
| 问题 | 当前状态 | 办公场景影响 |
|------|----------|--------------|
| 固定暗色主题 | 深色背景 + 蓝色高亮 | 长时间办公易视觉疲劳 |
| 无主题切换 | 仅暗色模式 | 不适应不同办公环境（会议室/办公室/居家） |
| 字体固定 | 系统默认字体 | 无法适应不同文档风格需求 |

#### 2.1.2 办公场景视觉标识缺失
| 场景 | 当前状态 | 优化建议 |
|------|----------|----------|
| 文档处理 | 通用卡片样式 | 增加文档类型图标和颜色标识 |
| 翻译模式 | 无专用界面 | 增加语言对标识和翻译进度 |
| 润色模式 | 通用按钮样式 | 增加润色风格选择器 |

### 2.2 交互体验不足

#### 2.2.1 办公场景操作流程复杂
| 操作 | 当前流程 | 优化建议 |
|------|----------|----------|
| 文档修订 | 1. 唤醒卡片 → 2. 点击"全文修订" → 3. 选择文件 → 4. 选中文本 → 5. 拖拽到卡片 | 简化为：拖拽文件到卡片自动进入修订模式 |
| 翻译操作 | 1. 唤醒卡片 → 2. 点击"翻译" → 3. 选中文本 → 4. 拖拽到卡片 | 增加快捷翻译入口，支持右键菜单 |
| 批量处理 | 无批量处理功能 | 增加文件批量拖拽和处理队列 |

#### 2.2.2 办公场景快捷操作缺失
| 快捷操作 | 当前状态 | 办公场景需求 |
|----------|----------|--------------|
| 全局快捷键 | 无 | Cmd+Shift+Space 唤醒，Cmd+Shift+T 翻译 |
| 右键菜单 | 无 | 选中文本后右键直接调用润色/翻译 |
| 手势操作 | 无 | 触控板三指滑动切换模式 |
| 文件拖拽区 | 无专用区域 | 增加明显的文件拖拽区域 |

#### 2.2.3 办公场景反馈机制不足
| 反馈类型 | 当前状态 | 优化建议 |
|----------|----------|----------|
| 处理进度 | 无进度显示 | 增加文档处理进度条和预估时间 |
| 错误提示 | 简单文本提示 | 增加办公场景专用错误提示和解决建议 |
| 成功反馈 | 无成功提示 | 增加操作成功动画和声音反馈 |

### 2.3 办公场景功能缺失

#### 2.3.1 文档处理专用界面缺失
```
当前问题：
1. 文档处理结果在通用文本框中显示，缺乏结构化展示
2. 无法预览文档原始内容和修改后内容对比
3. 缺乏文档结构导航（章节/页面选择）
4. 无法批量处理多个文档
```

#### 2.3.2 翻译专用界面缺失
```
当前问题：
1. 翻译结果在通用文本框中显示，缺乏双语对照
2. 无术语库管理和术语一致性检查
3. 无翻译记忆和重复翻译检测
4. 缺乏翻译质量评估和改进建议
```

#### 2.3.3 润色专用界面缺失
```
当前问题：
1. 润色结果缺乏原文和修改对比显示
2. 无润色风格选择（学术/商务/技术/创意）
3. 无润色历史记录和版本对比
4. 缺乏润色质量评估和改进建议
```

---

## 三、操作功能优化建议

### 3.1 办公场景专用界面

#### 3.1.1 文档处理专用界面
```
文档处理模式 UI：
├── 文件信息栏
│   ├── 文件名 + 文件类型图标
│   ├── 文件大小 + 最后修改时间
│   └── 文档结构概览（章节/页面数）
├── 文档预览区
│   ├── 缩略图导航
│   ├── 页面/章节选择器
│   └── 搜索定位功能
├── 处理选项栏
│   ├── 修订模式选择（局部修订/全文修订）
│   ├── 润色风格选择（学术/商务/技术/创意）
│   ├── 翻译选项（目标语言/术语库）
│   └── 格式保持选项
├── 结果对比区
│   ├── 原文显示
│   ├── 修改显示
│   ├── 差异高亮（绿色新增/红色删除/黄色修改）
│   └── 逐条接受/拒绝按钮
└── 操作工具栏
    ├── 应用修改到原文
    ├── 导出修改后文档
    ├── 保存修改历史
    └── 分享修改结果
```

#### 3.1.2 翻译专用界面
```
翻译模式 UI：
├── 源语言区
│   ├── 自动检测语言显示
│   ├── 手动选择语言下拉框
│   ├── 源文本输入/显示区
│   └── 源文本字符数统计
├── 翻译控制栏
│   ├── 翻译方向切换按钮
│   ├── 术语库选择器
│   ├── 翻译记忆开关
│   └── 翻译质量评估按钮
├── 目标语言区
│   ├── 目标语言选择
│   ├── 翻译结果显示
│   ├── 翻译结果字符数统计
│   └── 翻译结果发音按钮
├── 术语管理区
│   ├── 术语提取结果
│   ├── 术语库编辑
│   └── 术语一致性检查结果
└── 翻译工具栏
    ├── 复制翻译结果
    ├── 替换源文本
    ├── 保存到翻译记忆
    └── 导出双语对照
```

#### 3.1.3 润色专用界面
```
润色模式 UI：
├── 文本输入区
│   ├── 原文输入/显示
│   ├── 原文字数统计
│   └── 原文质量评估（可选）
├── 润色控制栏
│   ├── 润色风格选择
│   │   ├── 学术润色
│   │   ├── 商务润色
│   │   ├── 技术润色
│   │   └── 创意润色
│   ├── 润色强度选择
│   │   ├── 轻度润色（修正错误）
│   │   ├── 中度润色（提升表达）
│   │   └── 深度润色（重构优化）
│   └── 润色目标选择
│       ├── 提升专业度
│       ├── 增强可读性
│       └── 优化逻辑结构
├── 结果对比区
│   ├── 原文显示
│   ├── 润色结果显示
│   ├── 差异高亮显示
│   └── 润色说明
├── 润色质量评估
│   ├── 润色前后对比评分
│   ├── 具体改进点分析
│   └── 进一步优化建议
└── 操作工具栏
    ├── 应用润色结果
    ├── 复制润色结果
    ├── 保存润色历史
    └── 导出润色报告
```

### 3.2 办公场景交互优化

#### 3.2.1 快捷操作优化
| 操作 | 当前方式 | 优化方式 | 优先级 |
|------|----------|----------|--------|
| 唤醒卡片 | 双击右键 | 增加全局快捷键 (Cmd+Shift+Space) | P0 |
| 翻译操作 | 点击按钮 | 选中文本后右键菜单"翻译" | P0 |
| 润色操作 | 点击按钮 | 选中文本后右键菜单"润色" | P0 |
| 文档修订 | 点击按钮 | 拖拽文件到卡片自动进入修订模式 | P1 |
| 批量处理 | 无 | 拖拽多个文件显示批量处理界面 | P1 |

#### 3.2.2 拖拽操作优化
```
拖拽优化设计：
1. 文件拖拽区
   - 拖拽文件到卡片任意位置自动识别
   - 显示明显的拖拽提示区域
   - 支持多种文件格式（.docx/.pptx/.pdf/.txt/.md）

2. 文本拖拽优化
   - 拖拽文本时显示预览
   - 自动识别文本类型（代码/普通文本/URL）
   - 根据文本类型推荐操作

3. 图片拖拽支持
   - 支持图片拖拽进行OCR识别
   - 支持图片内容描述
   - 支持图片翻译
```

#### 3.2.3 上下文菜单优化
```
右键菜单设计：
├── 快速操作
│   ├── 复制选中文本
│   ├── 粘贴剪贴板
│   └── 清空当前内容
├── AI 操作
│   ├── ✨ 自动识别
│   ├── 🌐 翻译
│   ├── ✍️ 润色
│   ├── 💻 代码解析
│   └── 📝 全文修订
├── 办公场景
│   ├── 📧 商务邮件
│   ├── 📄 学术论文
│   ├── 📋 技术文档
│   └── 📊 商务报告
└── 设置
    ├── 主题设置
    ├── 快捷键设置
    └── 办公场景设置
```

### 3.3 办公场景个性化设置

#### 3.3.1 办公场景专用设置
```python
office_settings = {
    # 翻译设置
    "translation": {
        "default_source_lang": "auto",
        "default_target_lang": "zh-CN",
        "terminology_databases": ["tech", "business", "academic"],
        "translation_memory": True,
        "quality_evaluation": True
    },
    
    # 润色设置
    "polish": {
        "default_style": "business",  # academic/business/technical/creative
        "polish_intensity": "medium",  # light/medium/deep
        "preserve_format": True,
        "show_diff": True
    },
    
    # 文档处理设置
    "document": {
        "supported_formats": [".docx", ".pptx", ".pdf", ".txt", ".md"],
        "auto_detect_type": True,
        "batch_processing": True,
        "max_file_size_mb": 50,
        "preserve_original": True
    },
    
    # 界面设置
    "ui": {
        "show_progress": True,
        "show_word_count": True,
        "show_quality_score": True,
        "auto_save_history": True,
        "history_retention_days": 30
    }
}
```

#### 3.3.2 Persona 管理界面
```
Persona 管理 UI：
├── Persona 列表
│   ├── 内置 Persona（商务邮件、学术论文、技术文档等）
│   ├── 自定义 Persona
│   └── 收藏的 Persona
├── Persona 编辑器
│   ├── 角色定义
│   ├── 核心能力
│   ├── 工作流程
│   ├── 输出规范
│   └── 质量标准
├── Persona 测试
│   ├── 测试输入
│   ├── 测试输出
│   └── 质量评估
└── Persona 分享
    ├── 导出 Persona
    ├── 导入 Persona
    └── 分享到社区
```

---

## 四、具体优化点

### 4.1 P0 优先级（核心办公体验）

#### 4.1.1 主题系统
```python
# 实现建议
class ThemeManager:
    def __init__(self):
        self.themes = {
            "dark": {
                "background": "rgba(30, 30, 35, 240)",
                "text": "#eeeeee",
                "accent": "#4da6ff",
                "border": "rgba(100, 100, 100, 100)"
            },
            "light": {
                "background": "rgba(255, 255, 255, 240)",
                "text": "#333333",
                "accent": "#1a73e8",
                "border": "rgba(200, 200, 200, 100)"
            },
            "office": {
                "background": "rgba(245, 245, 245, 240)",
                "text": "#333333",
                "accent": "#2b579a",  # Word 蓝
                "border": "rgba(180, 180, 180, 100)"
            }
        }
        self.current_theme = "dark"
```

#### 4.1.2 快捷键系统
```python
# 实现建议
class ShortcutManager:
    def __init__(self):
        self.shortcuts = {
            "wake_up": "Cmd+Shift+Space",
            "translate": "Cmd+Shift+T",
            "polish": "Cmd+Shift+P",
            "revision": "Cmd+Shift+R",
            "settings": "Cmd+Shift+S",
            "copy_result": "Cmd+C",
            "paste_input": "Cmd+V",
            "close_card": "Esc"
        }
```

#### 4.1.3 文件拖拽区
```python
# 实现建议
class FileDropZone(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.supported_formats = [".docx", ".pptx", ".pdf", ".txt", ".md"]
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(tuple(self.supported_formats)):
                    event.acceptProposedAction()
                    self.show_drop_hint()
                    return
    
    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.process_files(files)
```

#### 4.1.4 文档处理专用界面
```python
# 实现建议
class DocumentProcessDialog(QDialog):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.setup_ui()
        
    def setup_ui(self):
        # 文件信息栏
        self.file_info_layout = QHBoxLayout()
        self.file_name_label = QLabel(os.path.basename(self.file_path))
        self.file_type_icon = self.get_file_type_icon()
        
        # 文档预览区
        self.preview_widget = DocumentPreviewWidget()
        
        # 处理选项栏
        self.options_layout = QVBoxLayout()
        self.revision_mode_combo = QComboBox()
        self.polish_style_combo = QComboBox()
        
        # 结果对比区
        self.comparison_widget = DiffComparisonWidget()
```

### 4.2 P1 优先级（办公场景增强）

#### 4.2.1 翻译专用界面
```python
# 实现建议
class TranslationDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # 源语言区
        self.source_lang_combo = QComboBox()
        self.source_text_edit = QTextEdit()
        
        # 翻译控制栏
        self.translate_direction_btn = QPushButton("⇄")
        self.terminology_combo = QComboBox()
        
        # 目标语言区
        self.target_lang_combo = QComboBox()
        self.target_text_edit = QTextEdit()
        
        # 术语管理区
        self.terminology_widget = TerminologyWidget()
```

#### 4.2.2 润色专用界面
```python
# 实现建议
class PolishDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # 文本输入区
        self.original_text_edit = QTextEdit()
        
        # 润色控制栏
        self.polish_style_combo = QComboBox()
        self.polish_intensity_combo = QComboBox()
        
        # 结果对比区
        self.comparison_widget = DiffComparisonWidget()
        
        # 润色质量评估
        self.quality_score_widget = QualityScoreWidget()
```

#### 4.2.3 右键菜单优化
```python
# 实现建议
class ContextMenuManager:
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.setup_context_menu()
        
    def setup_context_menu(self):
        self.context_menu = QMenu(self.parent)
        
        # 快速操作
        quick_actions = self.context_menu.addMenu("快速操作")
        quick_actions.addAction("复制选中文本", self.copy_selected)
        quick_actions.addAction("粘贴剪贴板", self.paste_clipboard)
        
        # AI 操作
        ai_actions = self.context_menu.addMenu("AI 操作")
        ai_actions.addAction("✨ 自动识别", lambda: self.trigger_ai("auto"))
        ai_actions.addAction("🌐 翻译", lambda: self.trigger_ai("translate"))
        ai_actions.addAction("✍️ 润色", lambda: self.trigger_ai("polish"))
        
        # 办公场景
        office_actions = self.context_menu.addMenu("办公场景")
        office_actions.addAction("📧 商务邮件", lambda: self.trigger_persona("business/email"))
        office_actions.addAction("📄 学术论文", lambda: self.trigger_persona("academic/paper"))
```

### 4.3 P2 优先级（高级办公功能）

#### 4.3.1 批量处理界面
```python
# 实现建议
class BatchProcessDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # 文件列表
        self.file_list_widget = QListWidget()
        
        # 处理控制
        self.start_btn = QPushButton("开始处理")
        self.pause_btn = QPushButton("暂停")
        self.cancel_btn = QPushButton("取消")
        
        # 结果汇总
        self.result_summary = QLabel()
        
        # 导出选项
        self.export_btn = QPushButton("导出结果")
```

#### 4.3.2 术语库管理
```python
# 实现建议
class TerminologyManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # 术语库列表
        self.terminology_list = QListWidget()
        
        # 术语编辑器
        self.term_editor = TerminologyEditor()
        
        # 术语导入导出
        self.import_btn = QPushButton("导入术语库")
        self.export_btn = QPushButton("导出术语库")
        
        # 术语一致性检查
        self.check_btn = QPushButton("检查术语一致性")
```

#### 4.3.3 翻译记忆系统
```python
# 实现建议
class TranslationMemory(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # 翻译记忆列表
        self.memory_list = QListWidget()
        
        # 翻译记忆搜索
        self.search_input = QLineEdit()
        
        # 翻译记忆编辑
        self.memory_editor = TranslationMemoryEditor()
        
        # 翻译记忆导入导出
        self.import_btn = QPushButton("导入翻译记忆")
        self.export_btn = QPushButton("导出翻译记忆")
```

---

## 五、实施优先级

### 5.1 高优先级（P0）- 核心办公体验
1. **主题系统** - 提升长时间办公的视觉舒适度
2. **快捷键系统** - 提高办公操作效率
3. **文件拖拽区** - 简化文档处理流程
4. **文档处理专用界面** - 专业文档处理体验

### 5.2 中优先级（P1）- 办公场景增强
1. **翻译专用界面** - 专业翻译需求
2. **润色专用界面** - 专业润色需求
3. **右键菜单优化** - 丰富交互方式
4. **个性化设置** - 满足不同办公偏好

### 5.3 低优先级（P2）- 高级办公功能
1. **批量处理界面** - 企业级需求
2. **术语库管理** - 专业翻译需求
3. **翻译记忆系统** - 翻译效率提升
4. **手势操作** - 高级用户需求

---

## 六、技术实现建议

### 6.1 架构设计
```
办公场景 UI 架构：
├── core/
│   ├── theme_manager.py      # 主题管理
│   ├── shortcut_manager.py   # 快捷键管理
│   ├── context_menu_manager.py # 右键菜单管理
│   └── office_settings.py    # 办公场景设置
├── dialogs/
│   ├── document_dialog.py    # 文档处理对话框
│   ├── translation_dialog.py # 翻译对话框
│   ├── polish_dialog.py      # 润色对话框
│   ├── batch_dialog.py       # 批量处理对话框
│   └── terminology_dialog.py # 术语管理对话框
├── widgets/
│   ├── file_drop_zone.py     # 文件拖拽区
│   ├── diff_comparison.py    # 差异对比组件
│   ├── quality_score.py      # 质量评估组件
│   ├── progress_widget.py    # 进度显示组件
│   └── terminology_widget.py # 术语管理组件
└── utils/
    ├── document_parser.py    # 文档解析工具
    ├── terminology_manager.py # 术语管理工具
    └── translation_memory.py # 翻译记忆工具
```

### 6.2 样式系统
```python
# QSS 样式表管理
class OfficeStyleManager:
    def __init__(self):
        self.office_styles = {
            "document": {
                "accent_color": "#2b579a",  # Word 蓝
                "icon": "📄",
                "background": "rgba(245, 245, 245, 240)"
            },
            "translation": {
                "accent_color": "#4caf50",  # 翻译绿
                "icon": "🌐",
                "background": "rgba(240, 248, 255, 240)"
            },
            "polish": {
                "accent_color": "#ff9800",  # 润色橙
                "icon": "✍️",
                "background": "rgba(255, 248, 240, 240)"
            }
        }
```

### 6.3 快捷键系统
```python
# 全局快捷键管理
class OfficeShortcutManager:
    def __init__(self):
        self.shortcuts = {
            # 全局快捷键
            "global": {
                "wake_up": "Cmd+Shift+Space",
                "translate": "Cmd+Shift+T",
                "polish": "Cmd+Shift+P",
                "revision": "Cmd+Shift+R",
                "batch_process": "Cmd+Shift+B"
            },
            
            # 卡片内快捷键
            "card": {
                "submit": "Enter",
                "new_line": "Shift+Enter",
                "close": "Esc",
                "copy": "Cmd+C",
                "paste": "Cmd+V",
                "undo": "Cmd+Z"
            },
            
            # 文档处理快捷键
            "document": {
                "accept_change": "Cmd+Y",
                "reject_change": "Cmd+N",
                "accept_all": "Cmd+Shift+Y",
                "reject_all": "Cmd+Shift+N"
            }
        }
```

---

## 七、测试计划

### 7.1 功能测试
- [ ] 主题切换功能测试
- [ ] 快捷键响应测试
- [ ] 文件拖拽处理测试
- [ ] 文档处理专用界面测试
- [ ] 翻译专用界面测试
- [ ] 润色专用界面测试
- [ ] 右键菜单功能测试
- [ ] 批量处理功能测试

### 7.2 兼容性测试
- [ ] macOS 版本兼容性（12.0+）
- [ ] 不同屏幕分辨率测试
- [ ] 多显示器配置测试
- [ ] 暗色/亮色模式切换测试

### 7.3 性能测试
- [ ] UI 响应时间测试
- [ ] 内存占用测试
- [ ] CPU 使用率测试
- [ ] 文档处理性能测试

### 7.4 用户体验测试
- [ ] 办公场景操作流程测试
- [ ] 新手引导流程测试
- [ ] 操作便捷性测试
- [ ] 错误提示友好度测试

---

## 八、后续步骤

### 8.1 短期（1-2周）
1. 设计主题系统架构
2. 实现基础快捷键系统
3. 设计文件拖拽区原型
4. 设计文档处理界面原型

### 8.2 中期（3-4周）
1. 实现主题切换功能
2. 完善文件拖拽区
3. 实现文档处理专用界面
4. 实现翻译专用界面

### 8.3 长期（5-8周）
1. 实现润色专用界面
2. 优化右键菜单系统
3. 实现批量处理界面
4. 完善术语库和翻译记忆

---

## 九、参考资源

### 9.1 设计灵感
- Microsoft Office 365 设计语言
- Google Docs 交互设计
- DeepL 翻译界面设计
- Grammarly 润色界面设计

### 9.2 技术参考
- PyQt6 官方文档
- Qt 样式表参考
- macOS Human Interface Guidelines
- 无障碍设计指南

---

## 十、实现状态（2026-05-28 更新）

### 10.1 已完成功能（阶段1-4）

#### ✅ 核心组件（9个完全实现）
| 组件 | 文件 | 状态 | 测试覆盖 |
|------|------|------|----------|
| 主题系统 | `core/theme_manager.py` | ✅ 完全实现 | 90% |
| 快捷键系统 | `core/shortcut_manager.py` | ✅ 完全实现 | 85% |
| 文件拖拽区 | `widgets/file_drop_zone.py` | ✅ 完全实现 | 70% |
| 进度组件 | `widgets/progress_widget.py` | ✅ 完全实现 | 90% |
| 右键菜单 | `widgets/context_menu.py` | ✅ 完全实现 | 82% |
| 设置对话框 | `widgets/settings_dialog.py` | ✅ 完全实现 | 84% |
| 批量处理 | `widgets/batch_dialog.py` | ✅ 完全实现 | 63% |
| 术语管理 | `widgets/terminology_dialog.py` | ✅ 完全实现 | 68% |
| 翻译记忆 | `widgets/translation_memory.py` | ✅ 完全实现 | 43% |

#### ⚠️ 对话框组件（3个需要API集成）
| 组件 | 文件 | 状态 | 待完成 |
|------|------|------|--------|
| 文档处理 | `dialogs/document_dialog.py` | UI完成 | 集成 python-docx/PyPDF2 |
| 翻译对话框 | `dialogs/translation_dialog.py` | UI完成 | 集成翻译API |
| 润色对话框 | `dialogs/polish_dialog.py` | UI完成 | 集成AI润色API |

### 10.2 近期修复（2026-05-28）

#### 文件拖拽功能修复
- **问题**: `_on_file_dropped` 信号参数不匹配导致崩溃
- **原因**: `FileDropZone.file_dropped` 发出 `(str, dict)` 两个参数，但方法只接收一个
- **修复**: 统一方法签名为 `(self, file_path, file_info)`
- **验证**: 用户测试确认拖拽 .md 文件正常工作

#### 窗口稳定性修复
- **问题**: macOS 拖拽时窗口自动消失
- **修复**: 添加 `_is_dragging` 状态标记，防止拖拽过程中隐藏窗口
- **窗口尺寸**: 调整为 680x520，支持窗口拖拽移动

### 10.3 测试统计
- **总测试用例**: 242个
- **通过率**: 100%
- **覆盖率**: 64%（UI组件）

---

*本文档为办公场景 UI 优化建议文档。阶段1-4已实现完成，文件拖拽功能已验证通过。*
