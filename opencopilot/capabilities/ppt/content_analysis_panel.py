"""
内容分析面板组件

功能：
- 实时显示AI对当前内容的分析结果
- 显示内容类型、推荐展示方式、优化建议
- 支持交互功能（点击查看详情、应用建议等）
"""

import json
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QIcon


class AnalysisCard(QFrame):
    """
    分析结果卡片
    
    显示单个分析指标，如内容类型、质量评分等。
    """
    
    clicked = pyqtSignal(str)  # 卡片点击信号，传递类型
    
    def __init__(self, card_type: str, icon: str, title: str, value: str, 
                 color: str = "#4a9eff", parent=None):
        """
        初始化分析卡片
        
        Args:
            card_type: 卡片类型（用于点击事件）
            icon: 图标（emoji）
            title: 标题
            value: 值
            color: 主题颜色
            parent: 父组件
        """
        super().__init__(parent)
        self.card_type = card_type
        self._init_ui(icon, title, value, color)
    
    def _init_ui(self, icon: str, title: str, value: str, color: str):
        """初始化UI"""
        self.setFixedSize(120, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {color};
                background-color: #333;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # 图标和标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 14px; color: {color}; background: transparent;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 10px; color: #888; background: transparent;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 值
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {color};
            background: transparent;
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.clicked.emit(self.card_type)
        super().mousePressEvent(event)


class MetricItem(QWidget):
    """
    指标项组件
    
    显示单个指标，如关键点、实体等。
    """
    
    clicked = pyqtSignal(dict)  # 点击信号
    
    def __init__(self, item_data: Dict[str, Any], parent=None):
        """
        初始化指标项
        
        Args:
            item_data: 指标数据，包含：
                - icon: 图标
                - text: 文本
                - detail: 详情（可选）
                - color: 颜色（可选）
            parent: 父组件
        """
        super().__init__(parent)
        self.item_data = item_data
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 图标
        icon = self.item_data.get("icon", "•")
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(20)
        icon_label.setStyleSheet("font-size: 12px; background: transparent;")
        layout.addWidget(icon_label)
        
        # 文本
        text = self.item_data.get("text", "")
        text_label = QLabel(text)
        text_label.setStyleSheet("color: #e0e0e0; font-size: 11px; background: transparent;")
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # 颜色指示器（如果有）
        color = self.item_data.get("color")
        if color:
            color_indicator = QLabel("●")
            color_indicator.setFixedWidth(12)
            color_indicator.setStyleSheet(f"color: {color}; font-size: 8px; background: transparent;")
            layout.addWidget(color_indicator)
        
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QWidget:hover {
                background-color: #333;
                border-radius: 4px;
            }
        """)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.clicked.emit(self.item_data)
        super().mousePressEvent(event)


class ContentAnalysisPanel(QWidget):
    """
    内容分析面板
    
    实时显示AI对当前内容的分析结果，包括：
    - 内容类型识别
    - 质量评分
    - 关键点提取
    - 实体识别
    - 推荐展示方式
    - 优化建议
    """
    
    # 信号定义
    suggestion_clicked = pyqtSignal(dict)  # 建议点击
    entity_clicked = pyqtSignal(str)        # 实体点击
    key_point_clicked = pyqtSignal(str)     # 关键点点击
    
    # 内容类型配置（与 context_analyzer.py 的 ContentType 枚举保持一致）
    CONTENT_TYPE_CONFIG = {
        # 基础类型
        "text": {"icon": "📝", "label": "纯文本", "color": "#4a9eff"},
        "table": {"icon": "📋", "label": "表格", "color": "#607d8b"},
        "chart": {"icon": "📊", "label": "图表", "color": "#4caf50"},
        "flowchart": {"icon": "🔄", "label": "流程图", "color": "#9c27b0"},
        "image": {"icon": "🖼️", "label": "图片", "color": "#e91e63"},
        "list": {"icon": "📋", "label": "列表", "color": "#607d8b"},
        
        # 语义类型
        "data_comparison": {"icon": "📊", "label": "数据对比", "color": "#4caf50"},
        "time_series": {"icon": "📅", "label": "时间序列", "color": "#ff9800"},
        "process": {"icon": "🔄", "label": "流程步骤", "color": "#9c27b0"},
        "person_attributes": {"icon": "👤", "label": "人物属性", "color": "#f44336"},
        
        # 新增泛化类型
        "problem_solution": {"icon": "❓", "label": "问题-解决方案", "color": "#ff5722"},
        "pros_cons": {"icon": "⚖️", "label": "优缺点对比", "color": "#795548"},
        "feature_list": {"icon": "⭐", "label": "功能特点", "color": "#ffc107"},
        "case_study": {"icon": "📚", "label": "案例分析", "color": "#3f51b5"},
        "definition": {"icon": "📖", "label": "定义/概念", "color": "#00bcd4"},
        "summary": {"icon": "📝", "label": "总结/结论", "color": "#8bc34a"},
        "quote": {"icon": "💬", "label": "引用/名言", "color": "#9e9e9e"},
        "statistics": {"icon": "📈", "label": "统计数据", "color": "#ff9800"},
        "comparison": {"icon": "🔄", "label": "通用对比", "color": "#673ab7"},
        "organization": {"icon": "🏢", "label": "组织架构", "color": "#607d8b"},
        "timeline": {"icon": "⏰", "label": "时间线", "color": "#2196f3"},
        "argument": {"icon": "💡", "label": "论点/论据", "color": "#f44336"},
        
        "unknown": {"icon": "❓", "label": "未知类型", "color": "#888"}
    }
    
    # 可视化类型配置
    VISUAL_TYPE_CONFIG = {
        "bar_chart": {"icon": "📊", "label": "柱状图"},
        "line_chart": {"icon": "📈", "label": "折线图"},
        "pie_chart": {"icon": "🥧", "label": "饼图"},
        "table": {"icon": "📋", "label": "表格"},
        "flowchart": {"icon": "🔄", "label": "流程图"},
        "timeline": {"icon": "📅", "label": "时间线"},
        "list": {"icon": "📝", "label": "列表"},
        "text": {"icon": "📄", "label": "纯文本"}
    }
    
    def __init__(self, parent=None):
        """
        初始化内容分析面板
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._analysis_data = None
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2a2a2a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        # 内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(12)
        
        # 初始状态：空面板
        self._show_empty_state()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # 面板样式
        self.setStyleSheet("""
            ContentAnalysisPanel {
                background-color: #252525;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
    
    def _show_empty_state(self):
        """显示空状态"""
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)
        
        # 图标
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_label)
        
        # 文本
        text_label = QLabel("选择幻灯片内容\nAI将自动分析")
        text_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(text_label)
        
        self.content_layout.addWidget(empty_widget)
        self.content_layout.addStretch()
    
    def update_analysis(self, analysis_data: Dict[str, Any]):
        """
        更新分析结果
        
        Args:
            analysis_data: 分析数据，包含：
                - content_type: 内容类型
                - quality_score: 质量评分（0-1）
                - key_points: 关键点列表
                - entities: 实体列表
                - recommended_visual: 推荐可视化类型
                - suggestions: 建议列表
                - confidence: 置信度（0-1）
        """
        self._analysis_data = analysis_data
        
        # 清除旧内容
        self._clear_content()
        
        # 构建新的分析结果
        self._build_analysis_ui(analysis_data)
    
    def _clear_content(self):
        """清除内容"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _build_analysis_ui(self, data: Dict[str, Any]):
        """构建分析结果UI"""
        # 1. 标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        title_label = QLabel("📊 内容分析")
        title_label.setStyleSheet("""
            color: #e0e0e0;
            font-weight: bold;
            font-size: 14px;
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(24, 24)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 14px;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #444;
                color: #fff;
            }
        """)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(lambda: self._refresh_analysis())
        header_layout.addWidget(refresh_btn)
        
        self.content_layout.addLayout(header_layout)
        
        # 2. 指标卡片区域
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(8)
        
        # 内容类型卡片
        content_type = data.get("content_type", "unknown")
        type_config = self.CONTENT_TYPE_CONFIG.get(content_type, self.CONTENT_TYPE_CONFIG["unknown"])
        type_card = AnalysisCard(
            card_type="content_type",
            icon=type_config["icon"],
            title="类型",
            value=type_config["label"],
            color=type_config["color"]
        )
        type_card.clicked.connect(self._on_card_clicked)
        cards_layout.addWidget(type_card)
        
        # 质量评分卡片
        quality_score = data.get("quality_score", 0)
        quality_color = "#4caf50" if quality_score >= 0.8 else "#ff9800" if quality_score >= 0.6 else "#f44336"
        quality_card = AnalysisCard(
            card_type="quality_score",
            icon="⭐",
            title="质量",
            value=f"{int(quality_score * 100)}",
            color=quality_color
        )
        quality_card.clicked.connect(self._on_card_clicked)
        cards_layout.addWidget(quality_card)
        
        # 置信度卡片
        confidence = data.get("confidence", 0)
        confidence_card = AnalysisCard(
            card_type="confidence",
            icon="🎯",
            title="置信度",
            value=f"{int(confidence * 100)}%",
            color="#2196f3"
        )
        confidence_card.clicked.connect(self._on_card_clicked)
        cards_layout.addWidget(confidence_card)
        
        self.content_layout.addLayout(cards_layout)
        
        # 3. 推荐可视化类型
        recommended_visual = data.get("recommended_visual")
        if recommended_visual:
            visual_config = self.VISUAL_TYPE_CONFIG.get(recommended_visual, {})
            if visual_config:
                visual_frame = QFrame()
                visual_frame.setStyleSheet("""
                    QFrame {
                        background-color: #2a2a2a;
                        border: 1px solid #444;
                        border-radius: 6px;
                    }
                """)
                visual_layout = QHBoxLayout(visual_frame)
                visual_layout.setContentsMargins(12, 8, 12, 8)
                
                visual_icon = QLabel(visual_config.get("icon", "📊"))
                visual_icon.setStyleSheet("font-size: 16px; background: transparent;")
                visual_layout.addWidget(visual_icon)
                
                visual_text = QLabel(f"推荐展示：{visual_config.get('label', recommended_visual)}")
                visual_text.setStyleSheet("color: #4a9eff; font-size: 12px; background: transparent;")
                visual_layout.addWidget(visual_text)
                
                # 应用按钮
                apply_btn = QPushButton("应用")
                apply_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4a9eff;
                        color: white;
                        border: none;
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #3a8eef;
                    }
                """)
                apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                apply_btn.clicked.connect(lambda: self._apply_visual(recommended_visual))
                visual_layout.addWidget(apply_btn)
                
                self.content_layout.addWidget(visual_frame)
        
        # 4. 关键点
        key_points = data.get("key_points", [])
        if key_points:
            self._add_section_title("关键点")
            for point in key_points[:5]:  # 最多显示5个
                point_item = MetricItem(
                    {"icon": "•", "text": point, "color": "#4a9eff"},
                    parent=self
                )
                point_item.clicked.connect(lambda d: self.key_point_clicked.emit(d.get("text", "")))
                self.content_layout.addWidget(point_item)
        
        # 5. 实体
        entities = data.get("entities", [])
        if entities:
            self._add_section_title("识别实体")
            for entity in entities[:5]:  # 最多显示5个
                entity_type = entity.get("type", "")
                entity_text = entity.get("text", "")
                entity_item = MetricItem(
                    {"icon": self._get_entity_icon(entity_type), "text": entity_text, "color": self._get_entity_color(entity_type)},
                    parent=self
                )
                entity_item.clicked.connect(lambda d: self.entity_clicked.emit(d.get("text", "")))
                self.content_layout.addWidget(entity_item)
        
        # 6. 建议
        suggestions = data.get("suggestions", [])
        if suggestions:
            self._add_section_title("优化建议")
            for i, suggestion in enumerate(suggestions[:3]):  # 最多显示3个建议
                suggestion_widget = self._create_suggestion_widget(suggestion, i)
                self.content_layout.addWidget(suggestion_widget)
        
        # 添加弹性空间
        self.content_layout.addStretch()
    
    def _add_section_title(self, title: str):
        """添加区域标题"""
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #aaa;
            font-size: 11px;
            font-weight: bold;
            background: transparent;
            margin-top: 8px;
        """)
        self.content_layout.addWidget(title_label)
    
    def _get_entity_icon(self, entity_type: str) -> str:
        """获取实体类型图标"""
        icons = {
            "person": "👤",
            "date": "📅",
            "location": "📍",
            "organization": "🏢",
            "number": "🔢",
            "percentage": "%",
            "money": "💰"
        }
        return icons.get(entity_type, "📌")
    
    def _get_entity_color(self, entity_type: str) -> str:
        """获取实体类型颜色"""
        colors = {
            "person": "#f44336",
            "date": "#4caf50",
            "location": "#2196f3",
            "organization": "#ff9800",
            "number": "#9c27b0",
            "percentage": "#9c27b0",
            "money": "#4caf50"
        }
        return colors.get(entity_type, "#888")
    
    def _create_suggestion_widget(self, suggestion: Dict[str, Any], index: int) -> QWidget:
        """创建建议组件"""
        suggestion_frame = QFrame()
        suggestion_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
            }
            QFrame:hover {
                border-color: #4a9eff;
            }
        """)
        suggestion_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(suggestion_frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # 建议标题
        title = suggestion.get("title", f"建议 {index + 1}")
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #4a9eff; font-size: 11px; font-weight: bold; background: transparent;")
        layout.addWidget(title_label)
        
        # 建议描述
        description = suggestion.get("description", "")
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #ccc; font-size: 10px; background: transparent;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        # 点击事件
        suggestion_frame.mousePressEvent = lambda e: self.suggestion_clicked.emit(suggestion)
        
        return suggestion_frame
    
    def _apply_visual(self, visual_type: str):
        """应用可视化类型"""
        # NOTE(NYI): 触发可视化转换 — 待后续迭代实现
        print(f"Applying visual type: {visual_type}")
    
    def _refresh_analysis(self):
        """刷新分析"""
        # NOTE(NYI): 触发重新分析 — 待后续迭代实现
        print("Refreshing analysis...")
    
    def _on_card_clicked(self, card_type: str):
        """卡片点击事件"""
        # NOTE(NYI): 显示详细信息 — 待后续迭代实现
        print(f"Card clicked: {card_type}")
    
    def clear(self):
        """清空面板"""
        self._analysis_data = None
        self._clear_content()
        self._show_empty_state()


class AnalysisPanelManager:
    """
    分析面板管理器
    
    管理分析面板的更新和交互。
    """
    
    def __init__(self, panel: ContentAnalysisPanel):
        """
        初始化管理器
        
        Args:
            panel: 内容分析面板实例
        """
        self.panel = panel
        self._debounce_timer = None
        
        # 连接信号
        self.panel.suggestion_clicked.connect(self._on_suggestion_clicked)
        self.panel.entity_clicked.connect(self._on_entity_clicked)
        self.panel.key_point_clicked.connect(self._on_key_point_clicked)
    
    def update_analysis_debounced(self, analysis_data: Dict[str, Any], delay_ms: int = 300):
        """
        防抖更新分析结果
        
        Args:
            analysis_data: 分析数据
            delay_ms: 延迟毫秒数
        """
        # 停止之前的定时器
        if self._debounce_timer:
            self._debounce_timer.stop()
        
        # 创建新定时器
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(lambda: self.panel.update_analysis(analysis_data))
        self._debounce_timer.start(delay_ms)
    
    def _on_suggestion_clicked(self, suggestion: Dict[str, Any]):
        """建议点击处理"""
        print(f"Suggestion clicked: {suggestion.get('title')}")
        # NOTE(NYI): 显示建议详情或应用建议 — 待后续迭代实现
    
    def _on_entity_clicked(self, entity: str):
        """实体点击处理"""
        print(f"Entity clicked: {entity}")
        # NOTE(NYI): 搜索实体或显示详情 — 待后续迭代实现
    
    def _on_key_point_clicked(self, key_point: str):
        """关键点点击处理"""
        print(f"Key point clicked: {key_point}")
        # NOTE(NYI): 显示关键点详情 — 待后续迭代实现


# 便捷函数
def create_content_analysis_panel(parent=None) -> ContentAnalysisPanel:
    """
    创建内容分析面板的便捷函数
    
    Args:
        parent: 父组件
    
    Returns:
        ContentAnalysisPanel实例
    """
    return ContentAnalysisPanel(parent)


if __name__ == "__main__":
    # 测试代码
    import sys
    app = QApplication(sys.argv)
    
    # 测试数据
    test_analysis = {
        "content_type": "data_comparison",
        "quality_score": 0.85,
        "confidence": 0.92,
        "key_points": [
            "2024年Q1-Q4销售数据对比",
            "Q4销售额最高，达到120万",
            "同比增长25%",
            "环比增长15%"
        ],
        "entities": [
            {"type": "date", "text": "2024年Q1-Q4"},
            {"type": "number", "text": "120万"},
            {"type": "percentage", "text": "25%"}
        ],
        "recommended_visual": "bar_chart",
        "suggestions": [
            {
                "type": "data_to_chart",
                "title": "数据可视化建议",
                "description": "这段内容包含数据对比，建议用柱状图展示会更直观。"
            },
            {
                "type": "content_optimize",
                "title": "内容优化建议",
                "description": "可以添加同比增长趋势分析，让数据更有说服力。"
            }
        ]
    }
    
    # 创建测试窗口
    test_widget = QWidget()
    test_widget.setWindowTitle("ContentAnalysisPanel 测试")
    test_widget.resize(300, 500)
    
    # 创建面板
    panel = ContentAnalysisPanel(test_widget)
    panel.setGeometry(10, 10, 280, 480)
    
    # 更新分析结果
    panel.update_analysis(test_analysis)
    
    test_widget.show()
    sys.exit(app.exec())
