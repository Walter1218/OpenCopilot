"""
AI 建议气泡组件

功能：
- 显示AI对幻灯片内容的优化建议
- 支持接受、修改、忽略三种操作
- 提供预览功能
- 响应式动画效果
"""

import json
from typing import Optional, Dict, Any, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QTimer, QPoint, QSize, QRectF
)
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QIcon


class SuggestionBubble(QWidget):
    """
    AI 建议气泡组件
    
    当用户编辑幻灯片内容时，AI自动分析内容，主动推荐最佳展示方式。
    气泡会显示在编辑区域附近，用户可以选择接受、修改或忽略建议。
    """
    
    # 信号定义
    accepted = pyqtSignal(dict)   # 接受建议
    dismissed = pyqtSignal()      # 忽略建议
    modified = pyqtSignal(dict)   # 修改建议
    
    # 建议类型配置
    SUGGESTION_STYLES = {
        "visual_enhance": {
            "icon": "🎨",
            "color": "#4a9eff",
            "title": "视觉增强"
        },
        "content_optimize": {
            "icon": "📝",
            "color": "#4caf50",
            "title": "内容优化"
        },
        "structure_improve": {
            "icon": "🏗️",
            "color": "#ff9800",
            "title": "结构改进"
        },
        "style_consistent": {
            "icon": "✨",
            "color": "#9c27b0",
            "title": "风格统一"
        },
        "data_to_chart": {
            "icon": "📊",
            "color": "#2196f3",
            "title": "数据可视化"
        },
        "text_to_table": {
            "icon": "📋",
            "color": "#607d8b",
            "title": "表格转换"
        },
        "steps_to_flowchart": {
            "icon": "🔄",
            "color": "#795548",
            "title": "流程图转换"
        },
        "content_too_long": {
            "icon": "✂️",
            "color": "#f44336",
            "title": "内容精简"
        },
        "default": {
            "icon": "💡",
            "color": "#4a9eff",
            "title": "AI建议"
        }
    }
    
    def __init__(self, suggestion: Dict[str, Any], parent=None):
        """
        初始化建议气泡
        
        Args:
            suggestion: 建议数据，包含以下字段：
                - type: 建议类型（visual_enhance, content_optimize等）
                - title: 建议标题
                - description: 建议详细描述
                - preview: 预览内容（可选）
                - action: 建议动作（可选）
                - confidence: 置信度（0-1，可选）
            parent: 父组件
        """
        super().__init__(parent)
        self.suggestion = suggestion
        self._is_dismissed = False
        self._init_ui()
        self._setup_animations()
    
    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 气泡容器
        self.container = QFrame()
        self.container.setObjectName("suggestion_container")
        self.container.setStyleSheet("""
            QFrame#suggestion_container {
                background-color: #2a2a2a;
                border: 1px solid #4a9eff;
                border-radius: 12px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)
        
        # 头部：图标和标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 获取样式配置
        suggestion_type = self.suggestion.get("type", "default")
        style = self.SUGGESTION_STYLES.get(suggestion_type, self.SUGGESTION_STYLES["default"])
        
        # 图标
        icon_label = QLabel(style["icon"])
        icon_label.setFixedSize(24, 24)
        icon_label.setStyleSheet("font-size: 18px; background: transparent;")
        header_layout.addWidget(icon_label)
        
        # 标题
        title_text = self.suggestion.get("title", style["title"])
        title_label = QLabel(title_text)
        title_label.setStyleSheet(f"""
            font-weight: bold;
            color: {style['color']};
            font-size: 13px;
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        # 置信度（如果有）
        confidence = self.suggestion.get("confidence")
        if confidence is not None:
            confidence_label = QLabel(f"{int(confidence * 100)}%")
            confidence_label.setStyleSheet("""
                color: #888;
                font-size: 11px;
                background: transparent;
            """)
            header_layout.addWidget(confidence_label)
        
        header_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 16px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #444;
                color: #fff;
            }
        """)
        close_btn.clicked.connect(self._on_dismiss)
        header_layout.addWidget(close_btn)
        
        container_layout.addLayout(header_layout)
        
        # 描述内容
        description = self.suggestion.get("description", "")
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                color: #e0e0e0;
                font-size: 12px;
                background: transparent;
                margin: 4px 0;
            """)
            container_layout.addWidget(desc_label)
        
        # 预览区域（如果有）
        preview_data = self.suggestion.get("preview")
        if preview_data:
            preview_widget = self._create_preview(preview_data)
            if preview_widget:
                container_layout.addWidget(preview_widget)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # 接受按钮
        accept_btn = QPushButton("✓ 应用")
        accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a8eef;
            }
            QPushButton:pressed {
                background-color: #2a7edf;
            }
        """)
        accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        accept_btn.clicked.connect(self._on_accept)
        buttons_layout.addWidget(accept_btn)
        
        # 修改按钮
        modify_btn = QPushButton("✏️ 修改")
        modify_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #666;
            }
        """)
        modify_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        modify_btn.clicked.connect(self._on_modify)
        buttons_layout.addWidget(modify_btn)
        
        # 忽略按钮
        dismiss_btn = QPushButton("忽略")
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #e0e0e0;
            }
        """)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss_btn.clicked.connect(self._on_dismiss)
        buttons_layout.addWidget(dismiss_btn)
        
        container_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(self.container)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
    
    def _create_preview(self, preview_data: Any) -> Optional[QWidget]:
        """创建预览组件"""
        if not preview_data:
            return None
        
        preview_frame = QFrame()
        preview_frame.setFixedHeight(80)
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 6px;
                border: 1px solid #444;
            }
        """)
        
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        
        # 根据预览数据类型创建不同的预览内容
        if isinstance(preview_data, dict):
            # 图表预览
            if "chart_type" in preview_data:
                preview_label = QLabel(f"📊 {preview_data['chart_type']}预览")
                preview_label.setStyleSheet("color: #4a9eff; font-size: 11px;")
                preview_layout.addWidget(preview_label)
            # 表格预览
            elif "rows" in preview_data:
                preview_label = QLabel(f"📋 表格预览 ({len(preview_data['rows'])}行)")
                preview_label.setStyleSheet("color: #4a9eff; font-size: 11px;")
                preview_layout.addWidget(preview_label)
        elif isinstance(preview_data, str):
            preview_label = QLabel(preview_data)
            preview_label.setStyleSheet("color: #aaa; font-size: 11px;")
            preview_label.setWordWrap(True)
            preview_layout.addWidget(preview_label)
        
        return preview_frame
    
    def _setup_animations(self):
        """设置动画效果"""
        # 淡入动画
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(200)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 淡出动画
        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(150)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_animation.finished.connect(self._on_fade_out_finished)
    
    def show_at(self, position: QPoint, parent_size: QSize = None):
        """
        在指定位置显示气泡
        
        Args:
            position: 显示位置（相对于父组件）
            parent_size: 父组件大小（用于调整位置）
        """
        # 调整位置，确保气泡完全可见
        adjusted_pos = self._adjust_position(position, parent_size)
        self.move(adjusted_pos)
        
        # 显示并播放淡入动画
        self.show()
        self.fade_in_animation.start()
    
    def _adjust_position(self, position: QPoint, parent_size: Optional[QSize]) -> QPoint:
        """调整位置确保气泡完全可见"""
        # 获取屏幕几何信息
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
        else:
            screen_geometry = None
        
        # 获取气泡大小
        bubble_size = self.sizeHint()
        
        # 调整X坐标
        x = position.x()
        if screen_geometry:
            # 确保不超出右边界
            if x + bubble_size.width() > screen_geometry.right():
                x = screen_geometry.right() - bubble_size.width() - 10
            # 确保不超出左边界
            if x < screen_geometry.left():
                x = screen_geometry.left() + 10
        
        # 调整Y坐标
        y = position.y()
        if screen_geometry:
            # 优先显示在上方
            if y - bubble_size.height() > screen_geometry.top():
                y = y - bubble_size.height() - 10
            else:
                # 显示在下方
                y = y + 10
        
        return QPoint(x, y)
    
    def _on_accept(self):
        """处理接受操作"""
        if not self._is_dismissed:
            self._is_dismissed = True
            self.accepted.emit(self.suggestion)
            self._dismiss_with_animation()
    
    def _on_modify(self):
        """处理修改操作"""
        if not self._is_dismissed:
            self.modified.emit(self.suggestion)
    
    def _on_dismiss(self):
        """处理忽略操作"""
        if not self._is_dismissed:
            self._is_dismissed = True
            self.dismissed.emit()
            self._dismiss_with_animation()
    
    def _dismiss_with_animation(self):
        """带动画关闭"""
        self.fade_out_animation.start()
    
    def _on_fade_out_finished(self):
        """淡出动画完成"""
        self.hide()
        self.deleteLater()
    
    def paintEvent(self, event):
        """绘制事件 - 添加圆角效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制半透明背景
        path = QPainterPath()
        # QRect 需要转换为 QRectF 才能传给 addRoundedRect
        path.addRoundedRect(QRectF(self.container.geometry()), 12, 12)
        painter.fillPath(path, QColor(42, 42, 42, 230))


class SuggestionBubbleManager:
    """
    建议气泡管理器
    
    管理多个建议气泡的显示和交互。
    """
    
    def __init__(self, parent_widget: QWidget):
        """
        初始化管理器
        
        Args:
            parent_widget: 父组件（通常是编辑区域）
        """
        self.parent_widget = parent_widget
        self.active_bubbles = []
        self.max_bubbles = 3  # 同时显示的最大气泡数
    
    def show_suggestion(self, suggestion: Dict[str, Any], position: QPoint,
                       on_accept: Callable = None, on_modify: Callable = None,
                       on_dismiss: Callable = None):
        """
        显示建议气泡
        
        Args:
            suggestion: 建议数据
            position: 显示位置
            on_accept: 接受回调
            on_modify: 修改回调
            on_dismiss: 忽略回调
        """
        # 限制同时显示的气泡数量
        if len(self.active_bubbles) >= self.max_bubbles:
            # 移除最早的气泡
            oldest = self.active_bubbles.pop(0)
            oldest._on_dismiss()
        
        # 创建新气泡
        bubble = SuggestionBubble(suggestion, self.parent_widget)
        
        # 连接信号
        if on_accept:
            bubble.accepted.connect(on_accept)
        if on_modify:
            bubble.modified.connect(on_modify)
        if on_dismiss:
            bubble.dismissed.connect(on_dismiss)
        
        # 气泡关闭时从列表移除
        bubble.dismissed.connect(lambda: self._remove_bubble(bubble))
        bubble.accepted.connect(lambda _: self._remove_bubble(bubble))
        
        # 显示气泡
        bubble.show_at(position, self.parent_widget.size())
        self.active_bubbles.append(bubble)
    
    def _remove_bubble(self, bubble: SuggestionBubble):
        """从活动列表移除气泡"""
        if bubble in self.active_bubbles:
            self.active_bubbles.remove(bubble)
    
    def dismiss_all(self):
        """关闭所有气泡"""
        for bubble in self.active_bubbles[:]:
            bubble._on_dismiss()
        self.active_bubbles.clear()
    
    def has_active_bubbles(self) -> bool:
        """是否有活动的气泡"""
        return len(self.active_bubbles) > 0


# 便捷函数
def create_suggestion_bubble(suggestion: Dict[str, Any], parent=None) -> SuggestionBubble:
    """
    创建建议气泡的便捷函数
    
    Args:
        suggestion: 建议数据
        parent: 父组件
    
    Returns:
        SuggestionBubble实例
    """
    return SuggestionBubble(suggestion, parent)


if __name__ == "__main__":
    # 测试代码
    import sys
    app = QApplication(sys.argv)
    
    # 测试建议数据
    test_suggestions = [
        {
            "type": "data_to_chart",
            "title": "数据可视化建议",
            "description": "这段内容包含数据对比，建议用柱状图展示会更直观。",
            "confidence": 0.85,
            "preview": {"chart_type": "柱状图"}
        },
        {
            "type": "content_too_long",
            "title": "内容精简建议",
            "description": "这页内容较多（450字），建议精简到200字以内或拆分为多页。",
            "confidence": 0.92
        },
        {
            "type": "style_consistent",
            "title": "风格统一建议",
            "description": "这页的配色方案与其他页面不一致，建议使用统一的蓝色主题。",
            "confidence": 0.78
        }
    ]
    
    # 创建测试窗口
    test_widget = QWidget()
    test_widget.setWindowTitle("SuggestionBubble 测试")
    test_widget.resize(400, 300)
    test_widget.show()
    
    # 显示建议气泡
    manager = SuggestionBubbleManager(test_widget)
    
    for i, suggestion in enumerate(test_suggestions):
        position = QPoint(50 + i * 120, 150)
        manager.show_suggestion(suggestion, position)
    
    sys.exit(app.exec())
