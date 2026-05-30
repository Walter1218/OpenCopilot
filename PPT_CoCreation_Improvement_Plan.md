# PPT 共创模式改进计划

> 文档版本：v1.0 | 更新日期：2026-05-30

## 一、现状分析

### 1.1 当前架构

```
ppt_cocreation/
├── cocreation_dialog.py    # 主对话框（三面板布局）
├── source_panel.py         # 原文面板（选中/高亮/联动）
├── outline_panel.py        # 大纲面板（幻灯片导航+编辑表单）
├── preview_panel.py        # 预览面板（PyQt自绘渲染）
├── ai_chat_widget.py       # AI对话组件（Agent SSE流式）
└── source_matcher.py       # 原文匹配器（位置映射）
```

### 1.2 核心问题

| # | 问题 | 影响 | 严重度 |
|---|------|------|--------|
| 1 | **AI全量替换** | 修改一个标题，整个PPT重新生成，耗时长、易出错 | 高 |
| 2 | **操作繁琐** | 需在原文/大纲/预览三个面板间频繁切换 | 高 |
| 3 | **大纲面板技术性强** | 用户需理解`level`、`content_type`等概念 | 中 |
| 4 | **原文关联不直观** | 手动选中文本再添加，缺少拖拽等自然交互 | 中 |
| 5 | **缺少文本转图表能力** | 数据类文本无法直观转为图表/表格 | 中 |

---

## 二、改进方案总览

### 2.1 设计原则

```
预览为主 → 直接编辑 → AI辅助 → 快速迭代
```

### 2.2 四大改进方向

```
┌─────────────────────────────────────────────────────────────┐
│                    PPT 共创模式改进                          │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  AI局部修改  │  预览直接编辑 │  文本转图表  │  界面简化优化  │
│  (核心)      │  (体验)      │  (能力)      │  (易用性)      │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ • 局部更新   │ • 点击编辑   │ • 智能识别   │ • 隐藏技术细节 │
│ • 智能建议   │ • 右键菜单   │ • 图表转换   │ • 浮动工具栏   │
│ • 版本对比   │ • 拖拽操作   │ • 表格转换   │ • 预览为主布局 │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

---

## 三、AI局部修改（核心改进）

### 3.1 问题现状

当前 `ai_chat_widget.py` 的 AI 对话是**全量替换**：

```python
# 当前实现：AI 返回完整 slides JSON
def _build_user_message(self) -> str:
    return f"""当前幻灯片数据：
{json.dumps({"slides": self.slides_data})}
用户指令：{self.instruction}
请返回修改后的完整幻灯片 JSON 数据"""
```

### 3.2 改进方案

#### 3.2.1 修改 AI 系统提示，支持局部修改

```python
def _build_system_prompt(self) -> str:
    return """你是一个 PPT 编辑助手。优先进行局部修改，而不是重新生成整个PPT。

修改模式：
1. **局部修改**（推荐）：只修改用户指定的部分
   - 返回 {"action": "update", "slide_index": 1, "field": "title", "value": "核心优势"}
   - 返回 {"action": "add_item", "slide_index": 2, "item": {...}}
   - 返回 {"action": "update_item", "slide_index": 1, "item_index": 0, "field": "text", "value": "..."}

2. **全局修改**（仅当用户明确要求时）：
   - 返回 {"slides": [...]}

内容类型：text / image / flowchart / icon / table / chart
版式类型：center / text_only / image_right / image_left / three_columns"""
```

#### 3.2.2 新增局部更新解析器

```python
def _apply_partial_update(self, data: dict):
    """应用局部更新"""
    action = data.get("action")
    
    if action == "update":
        slide_idx = data["slide_index"]
        field = data["field"]
        value = data["value"]
        if 0 <= slide_idx < len(self.slides_data):
            self.slides_data[slide_idx][field] = value
    
    elif action == "add_item":
        slide_idx = data["slide_index"]
        item = data["item"]
        if 0 <= slide_idx < len(self.slides_data):
            self.slides_data[slide_idx].setdefault("items", []).append(item)
    
    elif action == "update_item":
        slide_idx = data["slide_index"]
        item_idx = data["item_index"]
        field = data["field"]
        value = data["value"]
        if 0 <= slide_idx < len(self.slides_data):
            items = self.slides_data[slide_idx].get("items", [])
            if 0 <= item_idx < len(items):
                items[item_idx][field] = value
    
    elif "slides" in data:
        # 全量更新（兼容旧模式）
        self.slides_data = data["slides"]
    
    self.slides_updated.emit(self.slides_data)
```

#### 3.2.3 快捷指令按钮

在 AI 对话输入框上方添加快捷指令：

```python
# 快捷指令
shortcuts = [
    ("换个标题", "请为当前幻灯片建议一个新标题"),
    ("添加要点", "在当前幻灯片添加一个新的要点"),
    ("换版式", "将当前幻灯片改为更合适的版式"),
    ("精简内容", "精简当前幻灯片的内容，保留核心信息"),
]
```

---

## 四、预览面板直接编辑

### 4.1 点击编辑

在 `SlideRenderer` 中添加点击检测和编辑能力：

```python
class SlideRenderer(QWidget):
    # 新增信号
    element_clicked = pyqtSignal(str, int)  # (元素类型, 元素索引)
    title_double_clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            element_type, element_index = self._hit_test(event.position())
            if element_type:
                self.element_clicked.emit(element_type, element_index)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if self._is_title_area(event.position()):
            self.title_double_clicked.emit()
        super().mouseDoubleClickEvent(event)
    
    def _hit_test(self, pos) -> tuple:
        """检测点击位置对应的元素"""
        # 将 widget 坐标转换为幻灯片坐标
        slide_x = (pos.x() - self._offset_x) / self.scale_factor
        slide_y = (pos.y() - self._offset_y) / self.scale_factor
        
        # 检测标题区域 (100, 50, 1133, 120)
        if 100 <= slide_x <= 1233 and 50 <= slide_y <= 170:
            return ("title", -1)
        
        # 检测内容区域
        y = 180
        for i, item in enumerate(self.current_slide.get("items", [])):
            if y <= slide_y <= y + 50:
                return ("item", i)
            y += 50
        
        return (None, -1)
```

### 4.2 右键菜单

```python
def contextMenuEvent(self, event):
    """右键菜单"""
    element_type, element_index = self._hit_test(event.pos())
    
    menu = QMenu(self)
    
    if element_type == "title":
        menu.addAction("✏️ 编辑标题", lambda: self._edit_title())
        menu.addAction("🔄 换版式", lambda: self._change_layout())
    elif element_type == "item":
        menu.addAction("✏️ 编辑内容", lambda: self._edit_item(element_index))
        menu.addAction("🗑️ 删除此项", lambda: self._delete_item(element_index))
    
    menu.addSeparator()
    menu.addAction("📋 从原文添加", lambda: self._add_from_source())
    menu.addAction("➕ 添加新要点", lambda: self._add_new_item())
    
    menu.exec(event.globalPos())
```

### 4.3 内联编辑器

```python
class InlineEditor(QLineEdit):
    """内联编辑器（悬浮在预览面板上）"""
    
    editing_finished = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: #333;
                border: 2px solid #007bff;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
        """)
        self.returnPressed.connect(self._on_confirm)
        self.escapePressed.connect(self.hide)
    
    def start_editing(self, rect: QRectF, text: str):
        """开始编辑"""
        self.setGeometry(rect)
        self.setText(text)
        self.show()
        self.setFocus()
        self.selectAll()
```

---

## 五、文本转图表/表格

### 5.1 智能识别引擎

```python
class TextAnalyzer:
    """文本结构分析器"""
    
    @staticmethod
    def analyze(text: str) -> dict:
        recommendations = []
        
        # 检测数字对比 → 柱状图/折线图
        if len(re.findall(r'\d+', text)) >= 4:
            recommendations.append({
                "type": "chart", "subtype": "bar",
                "confidence": 0.9,
                "reason": "检测到数字对比，推荐柱状图"
            })
        
        # 检测表格结构 → 表格
        if re.search(r'[\t|]+', text) or text.count('\n') >= 3:
            recommendations.append({
                "type": "table", "subtype": "data",
                "confidence": 0.8,
                "reason": "数据结构清晰，推荐表格"
            })
        
        # 检测流程步骤 → 流程图
        if re.search(r'(步骤|首先|然后|最后|→)', text):
            recommendations.append({
                "type": "flowchart", "subtype": "vertical",
                "confidence": 0.85,
                "reason": "包含流程步骤，推荐流程图"
            })
        
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "recommendations": recommendations,
            "best_match": recommendations[0] if recommendations else None
        }
```

### 5.2 转换交互流程

```
选中文本 → 智能识别 → 显示转换菜单 → 用户选择 → 生成预览 → 微调
```

**转换菜单 UI**：

```
┌─────────────────────────────────────────────────────┐
│ 🔄 转换为：                                          │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│ │ 📊 图表  │ │ 📋 表格  │ │ 📈 柱状图│ │ 🥧 饼图  │    │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│ │ 🔄 流程图│ │ ⏱️ 时间线│ │ 🔢 列表  │ │ 📊 思维导│    │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
│                                                     │
│ 💡 智能推荐：检测到数字对比，推荐使用「柱状图」       │
└─────────────────────────────────────────────────────┘
```

### 5.3 数据结构

**图表数据**：
```json
{
    "content_type": "chart",
    "chart_type": "bar",
    "chart_data": {
        "title": "季度销售对比",
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "datasets": [
            {"label": "产品A", "data": [100, 120, 150, 180], "color": "#007bff"}
        ]
    }
}
```

**表格数据**：
```json
{
    "content_type": "table",
    "table_data": {
        "title": "季度销售数据",
        "columns": ["项目", "Q1", "Q2", "Q3", "Q4"],
        "rows": [
            ["产品A", "100", "120", "150", "180"]
        ]
    }
}
```

---

## 六、界面布局优化

### 6.1 新布局设计

```
┌─────────────────────────────────────────────────────────────────┐
│  [← 上一页]  [全屏预览]  [从原文添加]  [AI修改]  [导出]  1/10  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────┐  ┌─────────────────────────┐ │
│   │                             │  │                         │ │
│   │      PPT 预览 (70%)         │  │    原文参考 (30%)       │ │
│   │                             │  │                         │ │
│   │  点击标题可直接编辑         │  │  [🎯选中模式]           │ │
│   │  右键显示操作菜单           │  │                         │ │
│   │  拖拽可调整顺序             │  │  蓝色：已提炼           │ │
│   │                             │  │  橙色：已选中           │ │
│   │                             │  │                         │ │
│   └─────────────────────────────┘  └─────────────────────────┘ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  🤖 AI助手：输入指令快速修改...  [换个标题][添加要点][换版式]   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 布局调整代码

```python
def _init_ui(self):
    # 预览为主：70% 空间
    self.splitter.setSizes([500, 300])  # 预览:原文 = 70:30
    
    # 隐藏大纲面板（简化为浮动工具栏）
    # self.outline_panel 隐藏，改为预览面板上方的浮动编辑栏
    
    # AI 对话集成快捷指令
    self.ai_chat.add_shortcut_buttons([
        "换个标题", "添加要点", "换版式", "精简内容"
    ])
```

### 6.3 简化大纲面板

隐藏技术细节，只保留用户关心的内容：

```python
# 旧版式选择（技术性强）
layout_combo.addItems(["center", "text_only", "image_right", ...])

# 新版式选择（用户友好）
layout_combo.addItems([
    "📄 纯文本", "🖼️ 图文混排", "📊 三栏对比", "🎯 封面"
])
```

---

## 七、API 设计

### 7.1 内容转换 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/content/analyze` | POST | 分析文本结构，推荐转换方式 |
| `/api/content/convert` | POST | 将文本转换为图表/表格 |
| `/api/content/update` | POST | 编辑已转换的图表/表格 |
| `/api/content/preview` | POST | 生成预览图 |
| `/api/content/styles` | GET | 获取可用样式 |

### 7.2 核心 API 详细设计

#### `POST /api/content/analyze`

**请求**：
```json
{
    "text": "2024年季度销售数据：\n产品A：Q1 100万，Q2 120万...",
    "context": {"slide_index": 1, "item_index": 0}
}
```

**响应**：
```json
{
    "success": true,
    "data": {
        "detected_patterns": [
            {"type": "number_comparison", "confidence": 0.92}
        ],
        "recommendations": [
            {"type": "chart", "subtype": "bar", "confidence": 0.92, "reason": "..."}
        ],
        "best_match": {"type": "chart", "subtype": "bar"},
        "extracted_data": {
            "labels": ["Q1", "Q2", "Q3", "Q4"],
            "datasets": [{"label": "产品A", "values": [100, 120, 150, 180]}]
        }
    }
}
```

#### `POST /api/content/convert`

**请求**：
```json
{
    "text": "...",
    "target_type": "chart",
    "target_subtype": "bar",
    "options": {
        "title": "季度销售对比",
        "style": "modern",
        "colors": ["#007bff", "#28a745"]
    }
}
```

**响应**：
```json
{
    "success": true,
    "data": {
        "content_id": "abc123",
        "content_type": "chart",
        "chart_data": {...},
        "style": {...},
        "preview_url": "/api/content/preview?content_id=abc123"
    }
}
```

---

## 八、开发优先级

### 8.1 优先级矩阵

```
                    高价值
                      │
        ┌─────────────┼─────────────┐
        │   P1 立即做  │   P2 跟进做  │
        │             │             │
  低复杂度│ • AI局部修改 │ • 文本转图表 ││ 高复杂度
        │ • 快捷指令   │ • 智能识别   ││
        │ • 界面简化   │ • 图表渲染   ││
        ├─────────────┼─────────────┤
        │   P3 可选做  │   P4 后续做  │
        │             │             │
        │ • 快捷键优化 │ • 预览直接编辑│
        │ • 样式美化   │ • 拖拽操作   │
        │             │ • 版本对比   │
        └─────────────┼─────────────┘
                      │
                    低价值
```

### 8.2 详细优先级排序

| 优先级 | 功能 | 复杂度 | 价值 | 预估工时 | 依赖 |
|--------|------|--------|------|----------|------|
| **P1-1** | AI局部修改支持 | 低 | 高 | 2h | 无 |
| **P1-2** | AI快捷指令按钮 | 低 | 高 | 1h | 无 |
| **P1-3** | 界面布局简化（预览为主） | 中 | 高 | 3h | 无 |
| **P1-4** | 大纲面板技术细节隐藏 | 低 | 中 | 1h | 无 |
| **P2-1** | 文本智能识别引擎 | 中 | 高 | 4h | 无 |
| **P2-2** | 转换菜单UI | 中 | 高 | 3h | P2-1 |
| **P2-3** | 图表数据结构定义 | 低 | 高 | 1h | 无 |
| **P2-4** | 表格渲染支持 | 中 | 中 | 4h | P2-3 |
| **P2-5** | 图表渲染支持 | 高 | 中 | 8h | P2-3 |
| **P2-6** | 内容转换API | 中 | 中 | 4h | P2-1, P2-3 |
| **P3-1** | 快捷键扩展 | 低 | 低 | 1h | 无 |
| **P3-2** | 主题/样式优化 | 中 | 低 | 4h | 无 |
| **P4-1** | 预览面板点击编辑 | 高 | 中 | 8h | P1-3 |
| **P4-2** | 预览面板右键菜单 | 中 | 中 | 3h | P4-1 |
| **P4-3** | 原文面板拖拽支持 | 高 | 中 | 6h | P1-3 |
| **P4-4** | AI版本对比功能 | 中 | 低 | 4h | P1-1 |

### 8.3 推荐开发路线

#### 第一阶段：核心体验提升（1-2天）

```
P1-1: AI局部修改 → P1-2: 快捷指令 → P1-4: 隐藏技术细节 → P1-3: 界面简化
```

**目标**：让用户能快速用 AI 修改 PPT，不需要理解技术概念

#### 第二阶段：图表能力增强（3-5天）

```
P2-3: 数据结构 → P2-1: 智能识别 → P2-2: 转换菜单 → P2-4: 表格渲染 → P2-6: API
```

**目标**：支持将文本转换为图表/表格，提升 PPT 可视化效果

#### 第三阶段：交互体验优化（可选）

```
P4-1: 点击编辑 → P4-2: 右键菜单 → P4-3: 拖拽支持
```

**目标**：提供更直观的直接编辑体验

---

## 九、实施计划

### 9.1 第一阶段任务清单

- [ ] 修改 `ai_chat_widget.py` 的 `_build_system_prompt`，支持局部修改
- [ ] 修改 `_on_ai_response`，新增 `_apply_partial_update` 解析器
- [ ] 添加快捷指令按钮到 AI 对话输入框上方
- [ ] 修改 `outline_panel.py`，简化版式选择（隐藏技术名称）
- [ ] 修改 `cocreation_dialog.py`，调整分割比例（预览70%:原文30%）
- [ ] 测试验证：局部修改、快捷指令、界面布局

### 9.2 第二阶段任务清单

- [ ] 创建 `content_converter.py`，实现 `TextAnalyzer` 智能识别引擎
- [ ] 定义图表/表格数据结构（JSON Schema）
- [ ] 创建 `ConversionMenu` 转换菜单组件
- [ ] 修改 `preview_panel.py`，支持表格和图表渲染
- [ ] 创建 `content_conversion_api.py`，实现转换 API
- [ ] 测试验证：文本分析、转换菜单、图表/表格渲染

### 9.3 测试策略

根据项目规范，测试案例**不使用 mock**，用真实代码验证：

```python
# 测试 AI 局部修改
def test_partial_update():
    widget = AICopilotChatWidget()
    widget.slides_data = [{"title": "原标题", "items": []}]
    
    # 模拟 AI 返回局部更新
    response = '{"action": "update", "slide_index": 0, "field": "title", "value": "新标题"}'
    widget._on_ai_response(response)
    
    assert widget.slides_data[0]["title"] == "新标题"

# 测试文本分析
def test_text_analyzer():
    text = "产品A：Q1 100万，Q2 120万，Q3 150万"
    result = TextAnalyzer.analyze(text)
    
    assert result["best_match"]["type"] == "chart"
    assert result["best_match"]["subtype"] == "bar"
    assert len(result["extracted_data"]["datasets"]) == 1
```

---

## 十、总结

### 核心改进点

1. **AI局部修改**：从全量替换改为局部更新，大幅提升响应速度和准确性
2. **快捷指令**：提供常用操作的一键入口，降低用户学习成本
3. **文本转图表**：智能识别文本结构，一键转换为图表/表格
4. **界面简化**：预览为主，隐藏技术细节，让用户专注于内容

### 预期效果

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| 修改单个标题耗时 | 10-30秒（全量生成） | 2-5秒（局部修改） |
| 用户操作步骤 | 5-8步（切换面板） | 1-2步（直接编辑） |
| 文本转图表 | 不支持 | 一键转换 |
| 学习成本 | 需理解技术概念 | 直觉操作 |
