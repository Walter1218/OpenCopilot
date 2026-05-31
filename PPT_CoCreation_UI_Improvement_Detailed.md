# PPT 共创界面改进详细方案

## 目录

1. [AI主动建议模式](#1-ai主动建议模式)
2. [渐进式生成模式](#2-渐进式生成模式)
3. [智能上下文感知](#3-智能上下文感知)
4. [多轮对话式协作](#4-多轮对话式协作)
5. [风格一致性保障](#5-风格一致性保障)
6. [智能内容分析面板](#6-智能内容分析面板)
7. [实时协作模式](#7-实时协作模式)
8. [智能内容补全](#8-智能内容补全)
9. [风格模板库](#9-风格模板库)
10. [智能检查和修复](#10-智能检查和修复)

---

## 1. AI主动建议模式

### 1.1 功能描述

当用户编辑幻灯片内容时，AI自动分析内容，主动推荐最佳展示方式，而不是等待用户明确指令。

### 1.2 交互流程

```
用户编辑内容
    ↓
AI自动分析（后台）
    ↓
检测到可优化内容
    ↓
显示建议气泡
    ↓
用户选择：接受/忽略/修改
    ↓
应用建议或继续编辑
```

### 1.3 UI设计

#### 建议气泡组件

```python
class SuggestionBubble(QWidget):
    """AI建议气泡"""
    
    # 信号
    accepted = pyqtSignal(dict)  # 接受建议
    dismissed = pyqtSignal()     # 忽略建议
    modified = pyqtSignal(dict)  # 修改建议
    
    def __init__(self, suggestion: dict, parent=None):
        super().__init__(parent)
        self.suggestion = suggestion
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 建议图标和标题
        header = QHBoxLayout()
        icon = QLabel("💡")
        icon.setFixedSize(20, 20)
        title = QLabel("AI建议")
        title.setStyleSheet("font-weight: bold; color: #4a9eff;")
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # 建议内容
        content = QLabel(self.suggestion.get("message", ""))
        content.setWordWrap(True)
        content.setStyleSheet("color: #e0e0e0; margin: 8px 0;")
        layout.addWidget(content)
        
        # 预览（如果有）
        if self.suggestion.get("preview"):
            preview = self._create_preview()
            layout.addWidget(preview)
        
        # 操作按钮
        buttons = QHBoxLayout()
        
        accept_btn = QPushButton("✓ 应用")
        accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3a8eef; }
        """)
        accept_btn.clicked.connect(self._on_accept)
        
        modify_btn = QPushButton("✏️ 修改")
        modify_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        modify_btn.clicked.connect(self._on_modify)
        
        dismiss_btn = QPushButton("✗ 忽略")
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888;
                border: none;
                padding: 6px 16px;
            }
            QPushButton:hover { color: #e0e0e0; }
        """)
        dismiss_btn.clicked.connect(self._on_dismiss)
        
        buttons.addWidget(accept_btn)
        buttons.addWidget(modify_btn)
        buttons.addWidget(dismiss_btn)
        layout.addLayout(buttons)
        
        # 样式
        self.setStyleSheet("""
            SuggestionBubble {
                background-color: #2a2a2a;
                border: 1px solid #4a9eff;
                border-radius: 8px;
            }
        """)
    
    def _create_preview(self):
        """创建预览组件"""
        preview = QFrame()
        preview.setFixedHeight(60)
        preview.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        # 根据建议类型显示不同的预览
        return preview
    
    def _on_accept(self):
        self.accepted.emit(self.suggestion)
        self.hide()
    
    def _on_modify(self):
        self.modified.emit(self.suggestion)
    
    def _on_dismiss(self):
        self.dismissed.emit()
        self.hide()
```

### 1.4 建议触发条件

```python
class SuggestionEngine:
    """建议引擎 - 检测内容并生成建议"""
    
    # 建议类型
    SUGGESTION_TYPES = {
        "data_to_chart": {
            "trigger": "检测到数值对比数据",
            "message": "这段内容包含数据对比，建议用{chart_type}展示会更直观",
            "priority": 1
        },
        "text_to_table": {
            "trigger": "检测到结构化数据",
            "message": "这段内容适合用表格展示，是否要转换？",
            "priority": 2
        },
        "steps_to_flowchart": {
            "trigger": "检测到流程步骤",
            "message": "这段内容描述了一个流程，建议用流程图展示",
            "priority": 3
        },
        "content_too_long": {
            "trigger": "内容超过阈值",
            "message": "这页内容较多，建议精简或拆分为多页",
            "priority": 4
        },
        "style_inconsistent": {
            "trigger": "风格与整体不一致",
            "message": "这页的风格与其他页面不一致，建议调整",
            "priority": 5
        }
    }
    
    def analyze_slide(self, slide_data: dict, all_slides: list) -> list:
        """分析幻灯片，生成建议"""
        suggestions = []
        
        # 检测数据对比
        data_suggestion = self._detect_data_comparison(slide_data)
        if data_suggestion:
            suggestions.append(data_suggestion)
        
        # 检测结构化数据
        table_suggestion = self._detect_structured_data(slide_data)
        if table_suggestion:
            suggestions.append(table_suggestion)
        
        # 检测流程步骤
        flow_suggestion = self._detect_flow_steps(slide_data)
        if flow_suggestion:
            suggestions.append(flow_suggestion)
        
        # 检测内容长度
        length_suggestion = self._check_content_length(slide_data)
        if length_suggestion:
            suggestions.append(length_suggestion)
        
        # 检测风格一致性
        style_suggestion = self._check_style_consistency(slide_data, all_slides)
        if style_suggestion:
            suggestions.append(style_suggestion)
        
        # 按优先级排序
        suggestions.sort(key=lambda x: x.get("priority", 99))
        
        return suggestions
    
    def _detect_data_comparison(self, slide_data: dict) -> dict:
        """检测数据对比"""
        # 分析要点中的数值
        items = slide_data.get("items", [])
        data_points = []
        
        for item in items:
            text = item.get("text", "")
            # 提取数值和标签
            matches = re.findall(r'(\w+)[：:]\s*(\d+\.?\d*)', text)
            if matches:
                data_points.extend(matches)
        
        if len(data_points) >= 2:
            # 推荐图表类型
            chart_type = "bar"  # 默认柱状图
            if any("增长" in str(dp) or "趋势" in str(dp) for dp in data_points):
                chart_type = "line"
            elif len(data_points) <= 5:
                chart_type = "pie"
            
            return {
                "type": "data_to_chart",
                "chart_type": chart_type,
                "data_points": data_points,
                "message": f"检测到{len(data_points)}个数据点，建议用{chart_type}图表展示",
                "priority": 1
            }
        
        return None
    
    def _detect_structured_data(self, slide_data: dict) -> dict:
        """检测结构化数据"""
        items = slide_data.get("items", [])
        
        # 检测键值对模式
        key_value_count = 0
        for item in items:
            text = item.get("text", "")
            if re.match(r'^[\u4e00-\u9fa5a-zA-Z]+\s*[：:]\s*.+$', text.strip()):
                key_value_count += 1
        
        if key_value_count >= 3:
            return {
                "type": "text_to_table",
                "message": f"检测到{key_value_count}个键值对，建议用表格展示",
                "priority": 2
            }
        
        return None
    
    def _detect_flow_steps(self, slide_data: dict) -> dict:
        """检测流程步骤"""
        items = slide_data.get("items", [])
        
        # 检测流程关键词
        flow_keywords = ['首先', '然后', '接着', '最后', '步骤', '第']
        flow_count = 0
        
        for item in items:
            text = item.get("text", "")
            if any(kw in text for kw in flow_keywords):
                flow_count += 1
        
        if flow_count >= 2:
            return {
                "type": "steps_to_flowchart",
                "message": f"检测到{flow_count}个流程步骤，建议用流程图展示",
                "priority": 3
            }
        
        return None
    
    def _check_content_length(self, slide_data: dict) -> dict:
        """检查内容长度"""
        items = slide_data.get("items", [])
        total_text = sum(len(item.get("text", "")) for item in items)
        
        if total_text > 500:  # 超过500字
            return {
                "type": "content_too_long",
                "message": f"内容较长（{total_text}字），建议精简或拆分",
                "priority": 4
            }
        
        return None
    
    def _check_style_consistency(self, slide_data: dict, all_slides: list) -> dict:
        """检查风格一致性"""
        # 检查版式一致性
        current_layout = slide_data.get("layout", "text_only")
        layouts = [s.get("layout", "text_only") for s in all_slides]
        
        # 如果当前版式与多数不同
        from collections import Counter
        layout_counts = Counter(layouts)
        most_common = layout_counts.most_common(1)[0][0]
        
        if current_layout != most_common and layout_counts[most_common] > len(all_slides) * 0.6:
            return {
                "type": "style_inconsistent",
                "message": f"建议使用{most_common}版式以保持风格一致",
                "priority": 5
            }
        
        return None
```

### 1.5 实现步骤

1. **创建SuggestionBubble组件**
   - 设计UI样式
   - 实现接受/忽略/修改操作
   - 添加动画效果

2. **实现SuggestionEngine**
   - 添加内容检测算法
   - 实现建议生成逻辑
   - 设置优先级排序

3. **集成到PreviewPanel**
   - 监听内容变化
   - 显示建议气泡
   - 处理用户选择

4. **添加设置选项**
   - 允许用户开启/关闭主动建议
   - 设置建议频率
   - 自定义建议类型

---

## 2. 渐进式生成模式

### 2.1 功能描述

AI逐步生成幻灯片，每页生成后暂停等待用户确认或调整，而不是一次性生成整个PPT。

### 2.2 交互流程

```
用户输入主题/大纲
    ↓
AI生成第1页
    ↓
显示预览 + 操作按钮
    ↓
用户选择：继续/修改/跳过/重新生成
    ↓
根据选择继续或调整
    ↓
重复直到完成
```

### 2.3 UI设计

#### 渐进式生成控制面板

```python
class ProgressiveGenerationPanel(QWidget):
    """渐进式生成控制面板"""
    
    # 信号
    continue_requested = pyqtSignal()
    modify_requested = pyqtSignal(dict)
    skip_requested = pyqtSignal()
    regenerate_requested = pyqtSignal()
    finish_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 0
        self.total_pages = 0
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # 进度显示
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("生成中...")
        self.progress_label.setStyleSheet("color: #e0e0e0; font-size: 14px;")
        self.page_counter = QLabel("0/0")
        self.page_counter.setStyleSheet("color: #888; font-size: 12px;")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addStretch()
        progress_layout.addWidget(self.page_counter)
        layout.addLayout(progress_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3c3c3c;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 状态信息
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; margin-top: 4px;")
        layout.addWidget(self.status_label)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.continue_btn = self._create_button("▶ 继续生成", "#4a9eff", self._on_continue)
        self.modify_btn = self._create_button("✏️ 修改此页", "#3c3c3c", self._on_modify)
        self.skip_btn = self._create_button("⏭ 跳过", "transparent", self._on_skip)
        self.regenerate_btn = self._create_button("🔄 重新生成", "#3c3c3c", self._on_regenerate)
        self.finish_btn = self._create_button("✓ 完成", "#28a745", self._on_finish)
        
        buttons_layout.addWidget(self.continue_btn)
        buttons_layout.addWidget(self.modify_btn)
        buttons_layout.addWidget(self.skip_btn)
        buttons_layout.addWidget(self.regenerate_btn)
        buttons_layout.addWidget(self.finish_btn)
        layout.addLayout(buttons_layout)
        
        # 初始状态
        self._update_buttons_state(False)
    
    def _create_button(self, text: str, bg_color: str, callback) -> QPushButton:
        """创建按钮"""
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {'white' if bg_color != 'transparent' else '#888'};
                border: {'none' if bg_color != 'transparent' else '1px solid #555'};
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {'#3a8eef' if bg_color == '#4a9eff' else '#4a4a4a'};
            }}
        """)
        btn.clicked.connect(callback)
        return btn
    
    def set_progress(self, current: int, total: int):
        """设置进度"""
        self.current_page = current
        self.total_pages = total
        self.page_counter.setText(f"{current}/{total}")
        self.progress_bar.setValue(int(current / total * 100))
        self._update_buttons_state(True)
    
    def set_status(self, status: str):
        """设置状态"""
        self.status_label.setText(status)
    
    def _update_buttons_state(self, has_content: bool):
        """更新按钮状态"""
        self.continue_btn.setEnabled(has_content)
        self.modify_btn.setEnabled(has_content)
        self.skip_btn.setEnabled(has_content)
        self.regenerate_btn.setEnabled(has_content)
        self.finish_btn.setEnabled(has_content and self.current_page > 0)
    
    def _on_continue(self):
        self.continue_requested.emit()
        self.set_status("正在生成下一页...")
    
    def _on_modify(self):
        self.modify_requested.emit({"page": self.current_page})
    
    def _on_skip(self):
        self.skip_requested.emit()
        self.set_status("已跳过，正在生成下一页...")
    
    def _on_regenerate(self):
        self.regenerate_requested.emit()
        self.set_status("正在重新生成...")
    
    def _on_finish(self):
        self.finish_requested.emit()
```

### 2.4 AI提示词增强

```python
def _build_progressive_system_prompt(self) -> str:
    """构建渐进式生成的系统提示"""
    return """你是一个 PPT 编辑助手，采用渐进式生成模式。

工作流程：
1. 用户提供主题或大纲
2. 你逐页生成幻灯片
3. 每页生成后，等待用户确认
4. 根据用户反馈调整或继续

生成规则：
- 每次只生成1页幻灯片
- 生成后询问用户是否满意
- 支持用户修改当前页
- 支持用户跳过或重新生成

响应格式：
{
    "action": "add_slide",
    "slide": {
        "title": "页面标题",
        "type": "content",
        "layout": "text_only",
        "items": [
            {"text": "要点1", "level": 0, "content_type": "text"},
            {"text": "要点2", "level": 0, "content_type": "text"}
        ]
    },
    "message": "已生成第X页，是否继续？",
    "suggestions": ["建议1", "建议2"]
}

用户指令：{user_input}

请生成第{page_number}页幻灯片。"""
```

### 2.5 实现步骤

1. **创建ProgressiveGenerationPanel**
   - 设计进度显示
   - 实现操作按钮
   - 添加动画效果

2. **修改AI对话逻辑**
   - 支持渐进式生成模式
   - 解析单页响应
   - 处理用户反馈

3. **集成到CoCreationDialog**
   - 添加渐进式生成入口
   - 管理生成状态
   - 处理完成回调

---

## 3. 智能上下文感知

### 3.1 功能描述

AI理解整个PPT的结构、主题、风格，基于全局视角给出建议，而不仅仅是当前幻灯片。

### 3.2 数据结构

```python
class PPTContext:
    """PPT上下文信息"""
    
    def __init__(self):
        self.title = ""  # PPT标题
        self.theme = ""  # 主题
        self.style = ""  # 风格
        self.audience = ""  # 目标受众
        self.purpose = ""  # 用途
        self.slides_summary = []  # 各页摘要
        self.key_topics = []  # 关键主题
        self.data_points = []  # 数据点
        self.visual_style = {}  # 视觉风格
    
    def to_prompt_context(self) -> str:
        """转换为提示词上下文"""
        return f"""PPT整体信息：
- 标题：{self.title}
- 主题：{self.theme}
- 风格：{self.style}
- 目标受众：{self.audience}
- 用途：{self.purpose}

关键主题：{', '.join(self.key_topics)}

各页内容摘要：
{self._format_slides_summary()}

视觉风格：
- 主色调：{self.visual_style.get('primary_color', '#007bff')}
- 字体：{self.visual_style.get('font', 'Helvetica Neue')}
- 版式偏好：{self.visual_style.get('layout_preference', 'text_only')}
"""
    
    def _format_slides_summary(self) -> str:
        """格式化各页摘要"""
        summaries = []
        for i, slide in enumerate(self.slides_summary, 1):
            title = slide.get('title', '无标题')
            items_count = len(slide.get('items', []))
            summaries.append(f"  第{i}页：{title}（{items_count}个要点）")
        return '\n'.join(summaries)
```

### 3.3 上下文收集

```python
class ContextCollector:
    """上下文收集器"""
    
    def __init__(self):
        self.context = PPTContext()
    
    def collect_from_slides(self, slides: list):
        """从幻灯片数据收集上下文"""
        self.context.slides_summary = []
        self.context.key_topics = []
        self.context.data_points = []
        
        for i, slide in enumerate(slides):
            # 提取标题
            title = slide.get('title', '')
            
            # 提取要点
            items = slide.get('items', [])
            item_texts = [item.get('text', '') for item in items]
            
            # 添加到摘要
            self.context.slides_summary.append({
                'title': title,
                'items': items,
                'index': i
            })
            
            # 提取关键主题
            if title:
                self.context.key_topics.append(title)
            
            # 提取数据点
            for text in item_texts:
                data_matches = re.findall(r'(\w+)[：:]\s*(\d+\.?\d*)', text)
                self.context.data_points.extend(data_matches)
        
        # 分析主题
        self._analyze_theme()
        
        # 分析视觉风格
        self._analyze_visual_style(slides)
    
    def _analyze_theme(self):
        """分析主题"""
        # 从标题和关键主题中推断主题
        all_text = ' '.join(self.context.key_topics)
        
        # 简单的主题推断
        theme_keywords = {
            '产品': '产品介绍',
            '销售': '销售报告',
            '市场': '市场分析',
            '技术': '技术方案',
            '项目': '项目汇报',
            '公司': '公司介绍'
        }
        
        for keyword, theme in theme_keywords.items():
            if keyword in all_text:
                self.context.theme = theme
                break
        
        if not self.context.theme:
            self.context.theme = '通用演示'
    
    def _analyze_visual_style(self, slides: list):
        """分析视觉风格"""
        # 统计版式使用
        layouts = [s.get('layout', 'text_only') for s in slides]
        from collections import Counter
        layout_counts = Counter(layouts)
        
        self.context.visual_style = {
            'primary_color': '#007bff',  # 默认蓝色
            'font': 'Helvetica Neue',
            'layout_preference': layout_counts.most_common(1)[0][0] if layout_counts else 'text_only'
        }
    
    def get_context_for_slide(self, slide_index: int) -> str:
        """获取特定幻灯片的上下文"""
        # 基础上下文
        context = self.context.to_prompt_context()
        
        # 添加相邻幻灯片信息
        if slide_index > 0:
            prev_slide = self.context.slides_summary[slide_index - 1]
            context += f"\n上一页内容：{prev_slide.get('title', '')}"
        
        if slide_index < len(self.context.slides_summary) - 1:
            next_slide = self.context.slides_summary[slide_index + 1]
            context += f"\n下一页内容：{next_slide.get('title', '')}"
        
        return context
```

### 3.4 智能建议

```python
class ContextAwareSuggestionEngine:
    """上下文感知的建议引擎"""
    
    def __init__(self, context_collector: ContextCollector):
        self.context_collector = context_collector
    
    def analyze_with_context(self, current_slide: dict, slide_index: int) -> list:
        """基于上下文分析并生成建议"""
        suggestions = []
        context = self.context_collector.context
        
        # 1. 检测内容重复
        duplicate_suggestion = self._check_content_duplication(
            current_slide, slide_index, context.slides_summary
        )
        if duplicate_suggestion:
            suggestions.append(duplicate_suggestion)
        
        # 2. 检测逻辑跳跃
        logic_suggestion = self._check_logic_flow(
            current_slide, slide_index, context.slides_summary
        )
        if logic_suggestion:
            suggestions.append(logic_suggestion)
        
        # 3. 检测风格一致性
        style_suggestion = self._check_style_consistency(
            current_slide, context.visual_style
        )
        if style_suggestion:
            suggestions.append(style_suggestion)
        
        # 4. 基于主题的建议
        theme_suggestion = self._generate_theme_based_suggestion(
            current_slide, context.theme
        )
        if theme_suggestion:
            suggestions.append(theme_suggestion)
        
        return suggestions
    
    def _check_content_duplication(self, current_slide: dict, 
                                    slide_index: int, 
                                    all_slides: list) -> dict:
        """检查内容重复"""
        current_title = current_slide.get('title', '')
        current_items = [item.get('text', '') for item in current_slide.get('items', [])]
        
        for i, slide in enumerate(all_slides):
            if i == slide_index:
                continue
            
            other_title = slide.get('title', '')
            other_items = [item.get('text', '') for item in slide.get('items', [])]
            
            # 检查标题相似度
            if current_title and other_title:
                similarity = self._calculate_similarity(current_title, other_title)
                if similarity > 0.8:
                    return {
                        "type": "content_duplication",
                        "message": f"第{i+1}页的标题'{other_title}'与当前页相似，建议合并或区分",
                        "related_slide": i,
                        "priority": 1
                    }
            
            # 检查要点重复
            for current_text in current_items:
                for other_text in other_items:
                    if current_text and other_text:
                        similarity = self._calculate_similarity(current_text, other_text)
                        if similarity > 0.7:
                            return {
                                "type": "content_duplication",
                                "message": f"与第{i+1}页有重复内容，建议整合",
                                "related_slide": i,
                                "priority": 1
                            }
        
        return None
    
    def _check_logic_flow(self, current_slide: dict, 
                           slide_index: int, 
                           all_slides: list) -> dict:
        """检查逻辑流程"""
        # 检查是否有逻辑跳跃
        if slide_index > 0:
            prev_slide = all_slides[slide_index - 1]
            prev_title = prev_slide.get('title', '')
            curr_title = current_slide.get('title', '')
            
            # 简单的逻辑检测
            if prev_title and curr_title:
                # 检查是否有过渡
                if not self._has_logical_connection(prev_title, curr_title):
                    return {
                        "type": "logic_jump",
                        "message": f"从'{prev_title}'到'{curr_title}'的过渡不够自然，建议添加过渡页",
                        "priority": 2
                    }
        
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 简单的相似度计算
        if text1 == text2:
            return 1.0
        
        # 使用编辑距离
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _has_logical_connection(self, title1: str, title2: str) -> bool:
        """检查是否有逻辑连接"""
        # 简单的逻辑连接检测
        connection_keywords = ['因此', '所以', '接下来', '然后', '最后']
        return any(kw in title2 for kw in connection_keywords)
    
    def _check_style_consistency(self, current_slide: dict, 
                                   visual_style: dict) -> dict:
        """检查风格一致性"""
        current_layout = current_slide.get('layout', 'text_only')
        preferred_layout = visual_style.get('layout_preference', 'text_only')
        
        if current_layout != preferred_layout:
            return {
                "type": "style_inconsistent",
                "message": f"建议使用{preferred_layout}版式以保持风格一致",
                "priority": 3
            }
        
        return None
    
    def _generate_theme_based_suggestion(self, current_slide: dict, 
                                           theme: str) -> dict:
        """基于主题生成建议"""
        # 根据主题推荐内容结构
        theme_suggestions = {
            '产品介绍': {
                "message": "产品介绍页建议包含：产品特点、优势、应用场景",
                "recommended_items": ["产品特点", "核心优势", "应用场景", "客户案例"]
            },
            '销售报告': {
                "message": "销售报告页建议包含：销售数据、趋势分析、关键指标",
                "recommended_items": ["销售数据", "同比增长", "环比变化", "关键指标"]
            },
            '市场分析': {
                "message": "市场分析页建议包含：市场规模、竞争格局、机会分析",
                "recommended_items": ["市场规模", "竞争格局", "机会分析", "威胁分析"]
            }
        }
        
        if theme in theme_suggestions:
            suggestion = theme_suggestions[theme]
            return {
                "type": "theme_based",
                "message": suggestion["message"],
                "recommended_items": suggestion["recommended_items"],
                "priority": 4
            }
        
        return None
```

### 3.5 实现步骤

1. **实现PPTContext数据结构**
   - 定义上下文信息
   - 实现序列化方法
   - 添加更新机制

2. **实现ContextCollector**
   - 从幻灯片数据收集上下文
   - 分析主题和风格
   - 提取关键信息

3. **实现ContextAwareSuggestionEngine**
   - 基于上下文生成建议
   - 检测内容重复和逻辑跳跃
   - 提供风格一致性建议

4. **集成到AI对话**
   - 在提示词中包含上下文
   - 基于上下文优化响应
   - 提供更有针对性的建议

---

## 4. 多轮对话式协作

### 4.1 功能描述

AI和用户进行多轮对话，AI可以追问、澄清、提供选项，而不是单次指令-响应模式。

### 4.2 交互流程

```
用户输入模糊指令
    ↓
AI分析并追问
    ↓
用户澄清
    ↓
AI提供选项
    ↓
用户选择
    ↓
AI执行并确认
```

### 4.3 UI设计

#### 对话状态管理

```python
class ConversationState:
    """对话状态"""
    
    def __init__(self):
        self.current_intent = None  # 当前意图
        self.collected_info = {}  # 已收集的信息
        self.pending_questions = []  # 待问问题
        self.options = []  # 可选项
        self.history = []  # 对话历史
    
    def update(self, user_input: str, ai_response: str):
        """更新状态"""
        self.history.append({
            "user": user_input,
            "ai": ai_response,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_pending_question(self, question: str, options: list = None):
        """添加待问问题"""
        self.pending_questions.append({
            "question": question,
            "options": options or []
        })
    
    def get_next_question(self) -> dict:
        """获取下一个问题"""
        if self.pending_questions:
            return self.pending_questions.pop(0)
        return None
    
    def set_options(self, options: list):
        """设置可选项"""
        self.options = options
    
    def to_context(self) -> str:
        """转换为上下文"""
        context = "对话历史：\n"
        for entry in self.history[-3:]:  # 只保留最近3轮
            context += f"用户：{entry['user']}\n"
            context += f"AI：{entry['ai']}\n"
        
        if self.collected_info:
            context += f"\n已收集信息：{json.dumps(self.collected_info, ensure_ascii=False)}\n"
        
        return context
```

#### 选项卡片组件

```python
class OptionsCard(QWidget):
    """选项卡片"""
    
    # 信号
    option_selected = pyqtSignal(str)
    
    def __init__(self, title: str, options: list, parent=None):
        super().__init__(parent)
        self.title = title
        self.options = options
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #e0e0e0; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title_label)
        
        # 选项按钮
        for option in self.options:
            btn = QPushButton(option)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    padding: 10px 16px;
                    border-radius: 6px;
                    text-align: left;
                    margin: 2px 0;
                }
                QPushButton:hover {
                    background-color: #4a9eff;
                    border-color: #4a9eff;
                }
            """)
            btn.clicked.connect(lambda checked, opt=option: self.option_selected.emit(opt))
            layout.addWidget(btn)
        
        # 样式
        self.setStyleSheet("""
            OptionsCard {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
```

### 4.4 AI提示词增强

```python
def _build_multi_turn_system_prompt(self) -> str:
    """构建多轮对话的系统提示"""
    return """你是一个 PPT 编辑助手，采用多轮对话模式。

对话规则：
1. 理解用户意图，如果模糊则追问
2. 提供选项让用户选择，而不是直接执行
3. 确认后再执行操作
4. 执行后询问是否满意

响应格式（追问）：
{
    "action": "ask",
    "message": "你想用哪种图表展示？",
    "options": ["柱状图", "折线图", "饼图"],
    "context": "检测到数据对比，需要确认图表类型"
}

响应格式（执行）：
{
    "action": "execute",
    "operations": [...],
    "message": "已按照你的选择生成图表，是否满意？",
    "follow_up": "需要调整颜色或样式吗？"
}

用户输入：{user_input}
对话上下文：{conversation_context}

请根据上下文理解用户意图，必要时追问。"""
```

### 4.5 实现步骤

1. **实现ConversationState**
   - 管理对话状态
   - 记录对话历史
   - 跟踪已收集信息

2. **创建OptionsCard组件**
   - 显示选项列表
   - 处理用户选择
   - 支持多种选项样式

3. **修改AI对话逻辑**
   - 支持追问响应
   - 解析选项响应
   - 处理多轮对话

4. **集成到AIChatWidget**
   - 显示选项卡片
   - 管理对话状态
   - 处理用户选择

---

## 5. 风格一致性保障

### 5.1 功能描述

AI自动保持整个PPT的风格统一，包括颜色、字体、版式、动画等。

### 5.2 数据结构

```python
class StyleProfile:
    """风格配置"""
    
    def __init__(self):
        self.colors = {
            "primary": "#007bff",
            "secondary": "#6c757d",
            "success": "#28a745",
            "danger": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
            "light": "#f8f9fa",
            "dark": "#343a40"
        }
        self.fonts = {
            "title": "Helvetica Neue",
            "body": "Helvetica Neue",
            "caption": "Helvetica Neue"
        }
        self.font_sizes = {
            "title": 32,
            "subtitle": 24,
            "body": 18,
            "caption": 14
        }
        self.layouts = {
            "cover": "center",
            "content": "text_only",
            "data": "two_columns",
            "summary": "text_only"
        }
        self.animations = {
            "entrance": "fade",
            "emphasis": "none",
            "exit": "fade"
        }
    
    def apply_to_slide(self, slide_data: dict) -> dict:
        """应用风格到幻灯片"""
        # 根据幻灯片类型应用不同的风格
        slide_type = slide_data.get("type", "content")
        
        if slide_type == "title":
            slide_data["layout"] = self.layouts.get("cover", "center")
        else:
            slide_data["layout"] = self.layouts.get("content", "text_only")
        
        # 应用字体
        for item in slide_data.get("items", []):
            if item.get("level", 0) == 0:
                item["font_size"] = self.font_sizes.get("body", 18)
            else:
                item["font_size"] = self.font_sizes.get("caption", 14)
        
        return slide_data
    
    def to_prompt_context(self) -> str:
        """转换为提示词上下文"""
        return f"""风格规范：
- 主色调：{self.colors['primary']}
- 标题字体：{self.fonts['title']} {self.font_sizes['title']}px
- 正文字体：{self.fonts['body']} {self.font_sizes['body']}px
- 封面版式：{self.layouts['cover']}
- 内容版式：{self.layouts['content']}
"""
```

### 5.3 风格检测和修复

```python
class StyleChecker:
    """风格检查器"""
    
    def __init__(self, style_profile: StyleProfile):
        self.style_profile = style_profile
    
    def check_slide(self, slide_data: dict) -> list:
        """检查幻灯片风格"""
        issues = []
        
        # 检查版式
        layout_issue = self._check_layout(slide_data)
        if layout_issue:
            issues.append(layout_issue)
        
        # 检查颜色
        color_issue = self._check_colors(slide_data)
        if color_issue:
            issues.append(color_issue)
        
        # 检查字体
        font_issue = self._check_fonts(slide_data)
        if font_issue:
            issues.append(font_issue)
        
        return issues
    
    def _check_layout(self, slide_data: dict) -> dict:
        """检查版式"""
        current_layout = slide_data.get("layout", "text_only")
        expected_layout = self.style_profile.layouts.get("content", "text_only")
        
        if current_layout != expected_layout:
            return {
                "type": "layout_mismatch",
                "message": f"建议使用{expected_layout}版式",
                "current": current_layout,
                "expected": expected_layout
            }
        
        return None
    
    def _check_colors(self, slide_data: dict) -> dict:
        """检查颜色"""
        # 检查是否有自定义颜色
        for item in slide_data.get("items", []):
            if "color" in item:
                return {
                    "type": "custom_color",
                    "message": "检测到自定义颜色，建议使用主题色",
                    "color": item["color"]
                }
        
        return None
    
    def _check_fonts(self, slide_data: dict) -> dict:
        """检查字体"""
        # 检查是否有自定义字体
        for item in slide_data.get("items", []):
            if "font" in item:
                expected_font = self.style_profile.fonts.get("body", "Helvetica Neue")
                if item["font"] != expected_font:
                    return {
                        "type": "font_mismatch",
                        "message": f"建议使用{expected_font}字体",
                        "current": item["font"],
                        "expected": expected_font
                    }
        
        return None
    
    def fix_slide(self, slide_data: dict) -> dict:
        """修复幻灯片风格"""
        # 应用风格配置
        return self.style_profile.apply_to_slide(slide_data)
```

### 5.4 实现步骤

1. **实现StyleProfile**
   - 定义风格配置
   - 实现应用方法
   - 支持自定义配置

2. **实现StyleChecker**
   - 检查风格问题
   - 提供修复建议
   - 自动修复功能

3. **集成到AI对话**
   - 在提示词中包含风格规范
   - 生成符合风格的内容
   - 检查并修复风格问题

4. **添加风格设置界面**
   - 允许用户自定义风格
   - 预览风格效果
   - 保存风格配置

---

## 6. 智能内容分析面板

### 6.1 功能描述

实时显示AI对当前内容的分析结果，包括内容类型、推荐展示方式、优化建议等。

### 6.2 UI设计

```python
class ContentAnalysisPanel(QWidget):
    """内容分析面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 标题
        header = QHBoxLayout()
        title = QLabel("📊 内容分析")
        title.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # 分析结果区域
        self.analysis_area = QWidget()
        self.analysis_layout = QVBoxLayout(self.analysis_area)
        self.analysis_layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(self.analysis_area)
        
        # 样式
        self.setStyleSheet("""
            ContentAnalysisPanel {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
    
    def update_analysis(self, analysis: dict):
        """更新分析结果"""
        # 清除旧内容
        while self.analysis_layout.count():
            child = self.analysis_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 内容类型
        content_type = analysis.get("content_type", "text")
        type_label = QLabel(f"内容类型：{self._get_type_name(content_type)}")
        type_label.setStyleSheet("color: #4a9eff; margin-bottom: 8px;")
        self.analysis_layout.addWidget(type_label)
        
        # 推荐展示方式
        recommendation = analysis.get("recommendation", {})
        if recommendation:
            rec_label = QLabel(f"推荐展示：{recommendation.get('type', '无')}")
            rec_label.setStyleSheet("color: #28a745; margin-bottom: 4px;")
            self.analysis_layout.addWidget(rec_label)
            
            reason_label = QLabel(f"原因：{recommendation.get('reason', '')}")
            reason_label.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 8px;")
            self.analysis_layout.addWidget(reason_label)
        
        # 优化建议
        suggestions = analysis.get("suggestions", [])
        if suggestions:
            suggestions_label = QLabel("优化建议：")
            suggestions_label.setStyleSheet("color: #e0e0e0; margin-bottom: 4px;")
            self.analysis_layout.addWidget(suggestions_label)
            
            for suggestion in suggestions:
                suggestion_label = QLabel(f"• {suggestion}")
                suggestion_label.setStyleSheet("color: #888; font-size: 12px; margin-left: 8px;")
                self.analysis_layout.addWidget(suggestion_label)
        
        # 数据提取
        extracted_data = analysis.get("extracted_data")
        if extracted_data:
            data_label = QLabel("提取的数据：")
            data_label.setStyleSheet("color: #e0e0e0; margin-top: 8px; margin-bottom: 4px;")
            self.analysis_layout.addWidget(data_label)
            
            data_preview = QLabel(json.dumps(extracted_data, ensure_ascii=False, indent=2))
            data_preview.setStyleSheet("""
                color: #888;
                font-size: 11px;
                background-color: #1e1e1e;
                padding: 8px;
                border-radius: 4px;
                font-family: monospace;
            """)
            data_preview.setWordWrap(True)
            self.analysis_layout.addWidget(data_preview)
    
    def _get_type_name(self, content_type: str) -> str:
        """获取类型名称"""
        type_names = {
            "text": "纯文本",
            "data": "数据内容",
            "flow": "流程步骤",
            "list": "列表内容",
            "comparison": "对比内容"
        }
        return type_names.get(content_type, "未知类型")
```

### 6.3 实时分析

```python
class RealTimeAnalyzer:
    """实时分析器"""
    
    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.suggestion_engine = SuggestionEngine()
    
    def analyze_content(self, content: str, slide_data: dict) -> dict:
        """分析内容"""
        # 使用TextAnalyzer分析
        analysis_result = self.text_analyzer.analyze(content)
        
        # 生成建议
        suggestions = self.suggestion_engine.analyze_slide(slide_data, [])
        
        return {
            "content_type": self._detect_content_type(content),
            "recommendation": analysis_result.get("best_match"),
            "suggestions": [s.get("message", "") for s in suggestions[:3]],
            "extracted_data": analysis_result.get("extracted_data"),
            "confidence": analysis_result.get("best_match", {}).get("confidence", 0)
        }
    
    def _detect_content_type(self, content: str) -> str:
        """检测内容类型"""
        # 检测数据类型
        if re.search(r'\d+\.?\d*%?', content):
            return "data"
        
        # 检测流程类型
        flow_keywords = ['首先', '然后', '接着', '最后', '步骤']
        if any(kw in content for kw in flow_keywords):
            return "flow"
        
        # 检测列表类型
        if re.match(r'^[-•·*]\s+', content, re.MULTILINE):
            return "list"
        
        # 检测对比类型
        comparison_keywords = ['vs', '对比', '比较', '优于']
        if any(kw in content for kw in comparison_keywords):
            return "comparison"
        
        return "text"
```

### 6.4 实现步骤

1. **创建ContentAnalysisPanel**
   - 设计UI布局
   - 实现实时更新
   - 添加交互功能

2. **实现实时分析器**
   - 集成TextAnalyzer
   - 实时内容检测
   - 生成分析结果

3. **集成到CoCreationDialog**
   - 添加分析面板
   - 监听内容变化
   - 显示分析结果

---

## 7. 实时协作模式

### 7.1 功能描述

AI和用户可以同时编辑不同的部分，实时同步，实现真正的协作。

### 7.2 数据结构

```python
class CollaborationState:
    """协作状态"""
    
    def __init__(self):
        self.user_editing = None  # 用户正在编辑的部分
        self.ai_editing = None  # AI正在编辑的部分
        self.locked_elements = {}  # 锁定的元素
        self.pending_changes = []  # 待应用的更改
    
    def lock_element(self, element_id: str, owner: str):
        """锁定元素"""
        self.locked_elements[element_id] = {
            "owner": owner,
            "locked_at": datetime.now().isoformat()
        }
    
    def unlock_element(self, element_id: str):
        """解锁元素"""
        if element_id in self.locked_elements:
            del self.locked_elements[element_id]
    
    def is_locked(self, element_id: str) -> bool:
        """检查元素是否被锁定"""
        return element_id in self.locked_elements
    
    def get_owner(self, element_id: str) -> str:
        """获取元素所有者"""
        return self.locked_elements.get(element_id, {}).get("owner")
    
    def add_pending_change(self, change: dict):
        """添加待应用的更改"""
        self.pending_changes.append(change)
    
    def apply_pending_changes(self) -> list:
        """应用待应用的更改"""
        changes = self.pending_changes.copy()
        self.pending_changes.clear()
        return changes
```

### 7.3 协作UI

```python
class CollaborationIndicator(QWidget):
    """协作指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # AI状态
        self.ai_status = QLabel("🤖 AI：空闲")
        self.ai_status.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.ai_status)
        
        layout.addStretch()
        
        # 用户状态
        self.user_status = QLabel("👤 你：空闲")
        self.user_status.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.user_status)
        
        # 样式
        self.setStyleSheet("""
            CollaborationIndicator {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)
    
    def update_ai_status(self, status: str, element: str = None):
        """更新AI状态"""
        if element:
            self.ai_status.setText(f"🤖 AI：正在编辑{element}")
            self.ai_status.setStyleSheet("color: #4a9eff; font-size: 12px;")
        else:
            self.ai_status.setText(f"🤖 AI：{status}")
            self.ai_status.setStyleSheet("color: #888; font-size: 12px;")
    
    def update_user_status(self, status: str, element: str = None):
        """更新用户状态"""
        if element:
            self.user_status.setText(f"👤 你：正在编辑{element}")
            self.user_status.setStyleSheet("color: #28a745; font-size: 12px;")
        else:
            self.user_status.setText(f"👤 你：{status}")
            self.user_status.setStyleSheet("color: #888; font-size: 12px;")
```

### 7.4 实现步骤

1. **实现CollaborationState**
   - 管理锁定状态
   - 跟踪编辑状态
   - 处理待应用更改

2. **创建CollaborationIndicator**
   - 显示协作状态
   - 实时更新
   - 处理冲突提示

3. **实现锁定机制**
   - 元素级锁定
   - 冲突检测
   - 自动解锁

4. **集成到编辑流程**
   - 编辑前检查锁定
   - 编辑时更新状态
   - 编辑后释放锁定

---

## 8. 智能内容补全

### 8.1 功能描述

用户输入部分内容，AI自动补全，提供智能建议。

### 8.2 补全类型

```python
class CompletionType:
    """补全类型"""
    
    TITLE = "title"  # 标题补全
    SUBTITLE = "subtitle"  # 副标题补全
    BULLET_POINT = "bullet_point"  # 要点补全
    DATA = "data"  # 数据补全
    FLOW_STEP = "flow_step"  # 流程步骤补全
```

### 8.3 补全引擎

```python
class CompletionEngine:
    """补全引擎"""
    
    def __init__(self):
        self.context_collector = ContextCollector()
    
    def get_completions(self, partial_text: str, 
                         completion_type: str,
                         context: dict) -> list:
        """获取补全建议"""
        # 基于类型选择补全策略
        if completion_type == CompletionType.TITLE:
            return self._complete_title(partial_text, context)
        elif completion_type == CompletionType.SUBTITLE:
            return self._complete_subtitle(partial_text, context)
        elif completion_type == CompletionType.BULLET_POINT:
            return self._complete_bullet_point(partial_text, context)
        elif completion_type == CompletionType.DATA:
            return self._complete_data(partial_text, context)
        elif completion_type == CompletionType.FLOW_STEP:
            return self._complete_flow_step(partial_text, context)
        
        return []
    
    def _complete_title(self, partial_text: str, context: dict) -> list:
        """补全标题"""
        # 基于主题生成标题建议
        theme = context.get("theme", "")
        
        title_templates = {
            "产品介绍": ["产品概述", "核心优势", "产品特点", "应用场景"],
            "销售报告": ["销售业绩", "市场表现", "关键指标", "增长趋势"],
            "市场分析": ["市场规模", "竞争格局", "机会分析", "发展趋势"]
        }
        
        templates = title_templates.get(theme, ["概述", "分析", "总结"])
        
        # 过滤匹配的模板
        completions = []
        for template in templates:
            if partial_text in template or not partial_text:
                completions.append(template)
        
        return completions[:5]  # 最多返回5个建议
    
    def _complete_bullet_point(self, partial_text: str, context: dict) -> list:
        """补全要点"""
        # 基于上下文生成要点建议
        slide_title = context.get("slide_title", "")
        
        # 根据标题生成相关要点
        if "优势" in slide_title:
            suggestions = [
                "性能提升30%",
                "成本降低20%",
                "用户满意度95%",
                "响应时间缩短50%"
            ]
        elif "流程" in slide_title:
            suggestions = [
                "需求收集与分析",
                "方案设计与评审",
                "开发实现与测试",
                "部署上线与运维"
            ]
        else:
            suggestions = []
        
        # 过滤匹配的建议
        completions = []
        for suggestion in suggestions:
            if partial_text in suggestion or not partial_text:
                completions.append(suggestion)
        
        return completions[:3]  # 最多返回3个建议
    
    def _complete_data(self, partial_text: str, context: dict) -> list:
        """补全数据"""
        # 基于已有数据生成建议
        data_points = context.get("data_points", [])
        
        # 生成数据建议
        suggestions = []
        for data_point in data_points[:3]:
            label, value = data_point
            suggestions.append(f"{label}：{value}")
        
        return suggestions
    
    def _complete_flow_step(self, partial_text: str, context: dict) -> list:
        """补全流程步骤"""
        # 基于已有步骤生成建议
        existing_steps = context.get("existing_steps", [])
        
        # 生成步骤建议
        step_templates = [
            "需求分析",
            "方案设计",
            "开发实现",
            "测试验证",
            "部署上线"
        ]
        
        # 过滤已存在的步骤
        suggestions = []
        for step in step_templates:
            if step not in existing_steps and (partial_text in step or not partial_text):
                suggestions.append(step)
        
        return suggestions[:3]  # 最多返回3个建议
```

### 8.4 UI集成

```python
class CompletionPopup(QWidget):
    """补全弹窗"""
    
    # 信号
    completion_selected = pyqtSignal(str)
    
    def __init__(self, completions: list, parent=None):
        super().__init__(parent)
        self.completions = completions
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # 补全选项
        for completion in self.completions:
            btn = QPushButton(completion)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #e0e0e0;
                    border: none;
                    padding: 6px 12px;
                    text-align: left;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4a9eff;
                }
            """)
            btn.clicked.connect(lambda checked, c=completion: self.completion_selected.emit(c))
            layout.addWidget(btn)
        
        # 样式
        self.setStyleSheet("""
            CompletionPopup {
                background-color: #2a2a2a;
                border: 1px solid #4a9eff;
                border-radius: 6px;
            }
        """)
        self.setWindowFlags(Qt.Popup)
    
    def show_at(self, position: QPoint):
        """在指定位置显示"""
        self.move(position)
        self.show()
```

### 8.5 实现步骤

1. **实现CompletionEngine**
   - 定义补全策略
   - 实现各种补全类型
   - 集成上下文信息

2. **创建CompletionPopup**
   - 设计UI样式
   - 实现选择功能
   - 添加键盘导航

3. **集成到编辑组件**
   - 监听输入事件
   - 触发补全
   - 应用补全结果

---

## 9. 风格模板库

### 9.1 功能描述

提供预设的风格模板，用户可以一键应用，快速统一PPT风格。

### 9.2 模板定义

```python
class StyleTemplate:
    """风格模板"""
    
    def __init__(self, name: str, description: str, 
                 colors: dict, fonts: dict, layouts: dict):
        self.name = name
        self.description = description
        self.colors = colors
        self.fonts = fonts
        self.layouts = layouts
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "colors": self.colors,
            "fonts": self.fonts,
            "layouts": self.layouts
        }

# 预设模板
TEMPLATES = {
    "business_blue": StyleTemplate(
        name="商务蓝",
        description="专业商务风格，适合正式场合",
        colors={
            "primary": "#007bff",
            "secondary": "#6c757d",
            "accent": "#17a2b8"
        },
        fonts={
            "title": "Helvetica Neue",
            "body": "Helvetica Neue"
        },
        layouts={
            "cover": "center",
            "content": "text_only",
            "data": "two_columns"
        }
    ),
    "tech_purple": StyleTemplate(
        name="科技紫",
        description="现代科技风格，适合技术演示",
        colors={
            "primary": "#6f42c1",
            "secondary": "#e83e8c",
            "accent": "#20c997"
        },
        fonts={
            "title": "SF Pro Display",
            "body": "SF Pro Text"
        },
        layouts={
            "cover": "center",
            "content": "text_only",
            "data": "two_columns"
        }
    ),
    "minimal_white": StyleTemplate(
        name="简约白",
        description="极简风格，适合清晰展示",
        colors={
            "primary": "#333333",
            "secondary": "#666666",
            "accent": "#007bff"
        },
        fonts={
            "title": "Helvetica Neue",
            "body": "Helvetica Neue"
        },
        layouts={
            "cover": "center",
            "content": "text_only",
            "data": "two_columns"
        }
    ),
    "creative_orange": StyleTemplate(
        name="创意橙",
        description="活泼创意风格，适合营销演示",
        colors={
            "primary": "#fd7e14",
            "secondary": "#ffc107",
            "accent": "#28a745"
        },
        fonts={
            "title": "Helvetica Neue",
            "body": "Helvetica Neue"
        },
        layouts={
            "cover": "center",
            "content": "image_right",
            "data": "three_columns"
        }
    )
}
```

### 9.3 模板选择UI

```python
class TemplateSelector(QWidget):
    """模板选择器"""
    
    # 信号
    template_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 标题
        header = QHBoxLayout()
        title = QLabel("🎨 风格模板")
        title.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # 模板网格
        grid = QGridLayout()
        grid.setSpacing(12)
        
        row, col = 0, 0
        for template_id, template in TEMPLATES.items():
            card = self._create_template_card(template_id, template)
            grid.addWidget(card, row, col)
            
            col += 1
            if col >= 2:  # 每行2个
                col = 0
                row += 1
        
        layout.addLayout(grid)
        
        # 样式
        self.setStyleSheet("""
            TemplateSelector {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
    
    def _create_template_card(self, template_id: str, 
                                template: StyleTemplate) -> QWidget:
        """创建模板卡片"""
        card = QWidget()
        card.setFixedSize(120, 100)
        card.setStyleSheet("""
            QWidget {
                background-color: #3c3c3c;
                border: 2px solid #444;
                border-radius: 8px;
            }
            QWidget:hover {
                border-color: #4a9eff;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 颜色预览
        color_preview = QWidget()
        color_preview.setFixedHeight(30)
        color_preview.setStyleSheet(f"""
            background-color: {template.colors['primary']};
            border-radius: 4px;
        """)
        layout.addWidget(color_preview)
        
        # 模板名称
        name_label = QLabel(template.name)
        name_label.setStyleSheet("color: #e0e0e0; font-size: 12px; font-weight: bold;")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        # 描述
        desc_label = QLabel(template.description)
        desc_label.setStyleSheet("color: #888; font-size: 10px;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 点击事件
        card.mousePressEvent = lambda e: self.template_selected.emit(template_id)
        
        return card
```

### 9.4 实现步骤

1. **定义StyleTemplate**
   - 设计模板数据结构
   - 创建预设模板
   - 支持自定义模板

2. **创建TemplateSelector**
   - 设计模板卡片
   - 实现选择功能
   - 添加预览效果

3. **实现模板应用**
   - 应用到整个PPT
   - 应用到单页
   - 保存自定义模板

---

## 10. 智能检查和修复

### 10.1 功能描述

AI自动检查PPT质量，包括内容完整性、风格一致性、逻辑流畅性等，并提供修复建议。

### 10.2 检查项目

```python
class CheckItem:
    """检查项"""
    
    def __init__(self, name: str, description: str, 
                 check_func: callable, fix_func: callable = None):
        self.name = name
        self.description = description
        self.check_func = check_func
        self.fix_func = fix_func
        self.status = "pending"  # pending, pass, warning, fail
        self.message = ""
        self.details = []
    
    def check(self, slides: list) -> bool:
        """执行检查"""
        try:
            result = self.check_func(slides)
            self.status = result.get("status", "pass")
            self.message = result.get("message", "")
            self.details = result.get("details", [])
            return self.status == "pass"
        except Exception as e:
            self.status = "fail"
            self.message = f"检查失败: {str(e)}"
            return False
    
    def fix(self, slides: list) -> list:
        """执行修复"""
        if self.fix_func:
            return self.fix_func(slides)
        return slides

# 检查项定义
CHECK_ITEMS = [
    CheckItem(
        name="内容完整性",
        description="检查每页是否有标题和内容",
        check_func=lambda slides: _check_content_completeness(slides)
    ),
    CheckItem(
        name="风格一致性",
        description="检查整个PPT的风格是否一致",
        check_func=lambda slides: _check_style_consistency(slides)
    ),
    CheckItem(
        name="逻辑流畅性",
        description="检查各页之间的逻辑关系",
        check_func=lambda slides: _check_logic_flow(slides)
    ),
    CheckItem(
        name="文字密度",
        description="检查每页文字是否过多",
        check_func=lambda slides: _check_text_density(slides)
    ),
    CheckItem(
        name="数据准确性",
        description="检查数据是否有明显错误",
        check_func=lambda slides: _check_data_accuracy(slides)
    )
]
```

### 10.3 检查实现

```python
def _check_content_completeness(slides: list) -> dict:
    """检查内容完整性"""
    issues = []
    
    for i, slide in enumerate(slides):
        title = slide.get("title", "")
        items = slide.get("items", [])
        
        if not title:
            issues.append(f"第{i+1}页缺少标题")
        
        if not items:
            issues.append(f"第{i+1}页缺少内容")
    
    if issues:
        return {
            "status": "warning",
            "message": f"发现{len(issues)}个内容问题",
            "details": issues
        }
    
    return {"status": "pass", "message": "内容完整"}

def _check_style_consistency(slides: list) -> dict:
    """检查风格一致性"""
    layouts = [s.get("layout", "text_only") for s in slides]
    
    from collections import Counter
    layout_counts = Counter(layouts)
    most_common = layout_counts.most_common(1)[0]
    
    # 如果某种版式占比超过70%，认为是主导风格
    if most_common[1] > len(slides) * 0.7:
        inconsistent = [i for i, l in enumerate(layouts) if l != most_common[0]]
        if inconsistent:
            return {
                "status": "warning",
                "message": f"第{', '.join([str(i+1) for i in inconsistent])}页与主导风格不一致",
                "details": [f"第{i+1}页使用{layouts[i]}，建议使用{most_common[0]}" for i in inconsistent]
            }
    
    return {"status": "pass", "message": "风格一致"}

def _check_text_density(slides: list) -> dict:
    """检查文字密度"""
    issues = []
    
    for i, slide in enumerate(slides):
        items = slide.get("items", [])
        total_chars = sum(len(item.get("text", "")) for item in items)
        
        if total_chars > 500:
            issues.append(f"第{i+1}页文字过多（{total_chars}字）")
    
    if issues:
        return {
            "status": "warning",
            "message": f"发现{len(issues)}页文字过密",
            "details": issues
        }
    
    return {"status": "pass", "message": "文字密度适中"}
```

### 10.4 检查UI

```python
class QualityCheckPanel(QWidget):
    """质量检查面板"""
    
    # 信号
    fix_requested = pyqtSignal(str)  # 请求修复
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.check_items = CHECK_ITEMS.copy()
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 标题
        header = QHBoxLayout()
        title = QLabel("🔍 质量检查")
        title.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        
        # 一键检查按钮
        check_btn = QPushButton("一键检查")
        check_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #3a8eef; }
        """)
        check_btn.clicked.connect(self._run_all_checks)
        header.addStretch()
        header.addWidget(check_btn)
        layout.addLayout(header)
        
        # 检查结果区域
        self.results_area = QWidget()
        self.results_layout = QVBoxLayout(self.results_area)
        self.results_layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(self.results_area)
        
        # 样式
        self.setStyleSheet("""
            QualityCheckPanel {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
    
    def _run_all_checks(self):
        """运行所有检查"""
        # 清除旧结果
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 运行检查
        for check_item in self.check_items:
            # 这里需要传入slides数据
            # check_item.check(slides)
            
            # 显示结果
            result_widget = self._create_result_widget(check_item)
            self.results_layout.addWidget(result_widget)
    
    def _create_result_widget(self, check_item: CheckItem) -> QWidget:
        """创建结果组件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # 状态图标
        status_icon = QLabel()
        if check_item.status == "pass":
            status_icon.setText("✅")
        elif check_item.status == "warning":
            status_icon.setText("⚠️")
        else:
            status_icon.setText("❌")
        layout.addWidget(status_icon)
        
        # 检查项名称
        name_label = QLabel(check_item.name)
        name_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # 状态消息
        message_label = QLabel(check_item.message)
        message_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(message_label)
        
        # 修复按钮（如果有问题）
        if check_item.status in ["warning", "fail"] and check_item.fix_func:
            fix_btn = QPushButton("修复")
            fix_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #218838; }
            """)
            fix_btn.clicked.connect(lambda: self.fix_requested.emit(check_item.name))
            layout.addWidget(fix_btn)
        
        return widget
```

### 10.5 实现步骤

1. **定义检查项**
   - 实现各种检查函数
   - 定义修复函数
   - 设置优先级

2. **创建QualityCheckPanel**
   - 设计结果展示
   - 实现一键检查
   - 添加修复功能

3. **集成到CoCreationDialog**
   - 添加检查入口
   - 显示检查结果
   - 执行修复操作

---

## 实施计划

### 第一阶段：核心功能（1-2周）

1. **AI主动建议模式**
   - 实现SuggestionEngine
   - 创建SuggestionBubble
   - 集成到PreviewPanel

2. **智能上下文感知**
   - 实现ContextCollector
   - 增强AI提示词
   - 添加上下文分析

3. **多轮对话支持**
   - 实现ConversationState
   - 创建OptionsCard
   - 修改AI对话逻辑

### 第二阶段：增强功能（2-3周）

4. **渐进式生成模式**
   - 创建ProgressiveGenerationPanel
   - 修改AI生成逻辑
   - 添加进度管理

5. **风格一致性保障**
   - 实现StyleProfile
   - 创建StyleChecker
   - 集成到AI对话

6. **智能内容分析面板**
   - 创建ContentAnalysisPanel
   - 实现实时分析
   - 添加交互功能

### 第三阶段：高级功能（3-4周）

7. **智能内容补全**
   - 实现CompletionEngine
   - 创建CompletionPopup
   - 集成到编辑组件

8. **风格模板库**
   - 定义StyleTemplate
   - 创建TemplateSelector
   - 实现模板应用

9. **智能检查和修复**
   - 定义检查项
   - 创建QualityCheckPanel
   - 实现修复功能

### 第四阶段：协作功能（4-5周）

10. **实时协作模式**
    - 实现CollaborationState
    - 创建CollaborationIndicator
    - 实现锁定机制

---

## 技术要点

### 1. 状态管理

使用状态机管理复杂的交互状态：

```python
class CoCreationStateMachine:
    """共创状态机"""
    
    STATES = {
        "idle": "空闲",
        "editing": "编辑中",
        "ai_generating": "AI生成中",
        "ai_suggesting": "AI建议中",
        "collaborating": "协作中"
    }
    
    def __init__(self):
        self.current_state = "idle"
        self.state_data = {}
    
    def transition(self, new_state: str, data: dict = None):
        """状态转换"""
        if new_state in self.STATES:
            self.current_state = new_state
            self.state_data = data or {}
```

### 2. 事件驱动

使用事件总线解耦组件：

```python
class CoCreationEventBus:
    """共创事件总线"""
    
    def __init__(self):
        self.listeners = {}
    
    def on(self, event: str, callback: callable):
        """监听事件"""
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)
    
    def emit(self, event: str, data: dict = None):
        """触发事件"""
        if event in self.listeners:
            for callback in self.listeners[event]:
                callback(data)
```

### 3. 异步处理

使用异步处理避免UI阻塞：

```python
class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self):
        self.tasks = {}
    
    async def execute(self, task_id: str, func: callable, *args, **kwargs):
        """执行异步任务"""
        task = asyncio.create_task(func(*args, **kwargs))
        self.tasks[task_id] = task
        return await task
    
    def cancel(self, task_id: str):
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
            del self.tasks[task_id]
```

---

## 总结

这个改进方案从**人机协作**和**放大AI能力**两个角度，详细设计了10个核心功能。每个功能都包含了：

1. **功能描述**：清晰定义功能目标
2. **交互流程**：设计用户交互方式
3. **UI设计**：提供具体的组件实现
4. **技术实现**：给出核心代码示例
5. **实现步骤**：规划开发路径

通过这些改进，PPT共创界面将从"工具"升级为"智能伙伴"，真正实现人机协作，放大AI能力。