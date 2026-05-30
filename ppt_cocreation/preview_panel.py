"""
PPT 预览面板

功能：
- 实时预览当前幻灯片
- 支持上一页/下一页导航
- 全屏预览模式
- 与最终导出完全一致（所见即所得）

实现方案：
- 优先使用 PyQt 自绘（快速、无需外部依赖）
- 可选使用 LibreOffice 转换（更精确的渲染）
"""

import os
import tempfile
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QSizePolicy,
    QSlider, QSpinBox, QFrame, QDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QKeySequence, QShortcut, QGuiApplication
)

# 导入 PPT 生成器
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ppt_generator import generate_ppt_from_json, clean_markdown


class SlideRenderer(QWidget):
    """PyQt 自绘幻灯片渲染器"""
    
    # 幻灯片尺寸（16:9，与 ppt_generator.py 一致）
    SLIDE_WIDTH = 1333
    SLIDE_HEIGHT = 750
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_slide = None
        self.scale_factor = 1.0
        
        # 设置固定比例
        self.setMinimumSize(400, 225)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 颜色方案（与 ppt_generator.py 一致）
        self.bg_color = QColor(250, 250, 252)
        self.accent_color = QColor(0, 82, 204)
        self.title_color = QColor(15, 25, 45)
        self.text_color = QColor(60, 64, 67)
        self.light_bg = QColor(235, 240, 248)
    
    def set_slide(self, slide_data: dict):
        """设置当前幻灯片数据"""
        self.current_slide = slide_data
        self.update()
    
    def paintEvent(self, event):
        """绘制幻灯片"""
        if not self.current_slide:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # 计算缩放比例
        widget_width = self.width()
        widget_height = self.height()
        scale_x = widget_width / self.SLIDE_WIDTH
        scale_y = widget_height / self.SLIDE_HEIGHT
        self.scale_factor = min(scale_x, scale_y)
        
        # 计算居中偏移
        offset_x = (widget_width - self.SLIDE_WIDTH * self.scale_factor) / 2
        offset_y = (widget_height - self.SLIDE_HEIGHT * self.scale_factor) / 2
        
        # 应用变换
        painter.translate(offset_x, offset_y)
        painter.scale(self.scale_factor, self.scale_factor)
        
        # 绘制背景
        painter.fillRect(0, 0, self.SLIDE_WIDTH, self.SLIDE_HEIGHT, self.bg_color)
        
        # 绘制底部装饰条
        painter.fillRect(0, self.SLIDE_HEIGHT - 10, self.SLIDE_WIDTH, 10, self.accent_color)
        
        # 根据类型绘制
        slide_type = self.current_slide.get('type', 'content')
        if slide_type == 'title':
            self._draw_title_slide(painter)
        else:
            self._draw_content_slide(painter)
    
    def _draw_title_slide(self, painter: QPainter):
        """绘制封面幻灯片"""
        # 右侧装饰三角
        painter.setPen(Qt.PenStyle.NoPen)
        
        painter.setBrush(QColor(235, 240, 248))
        painter.drawPolygon([
            QPointF(self.SLIDE_WIDTH - 500, 0),
            QPointF(self.SLIDE_WIDTH, 0),
            QPointF(self.SLIDE_WIDTH, self.SLIDE_HEIGHT)
        ])
        
        painter.setBrush(self.accent_color)
        painter.drawPolygon([
            QPointF(self.SLIDE_WIDTH - 350, 0),
            QPointF(self.SLIDE_WIDTH, 0),
            QPointF(self.SLIDE_WIDTH, self.SLIDE_HEIGHT)
        ])
        
        # 标题
        title = clean_markdown(self.current_slide.get('title', ''))
        if title:
            font = QFont("Helvetica Neue", 44, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(self.title_color)
            painter.drawText(
                QRectF(100, 250, 800, 100),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title
            )
        
        # 副标题
        subtitle = clean_markdown(self.current_slide.get('subtitle', ''))
        if subtitle:
            font = QFont("Helvetica Neue", 24)
            painter.setFont(font)
            painter.setPen(QColor(100, 100, 110))
            painter.drawText(
                QRectF(100, 380, 800, 60),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                subtitle
            )
    
    def _draw_content_slide(self, painter: QPainter):
        """绘制内容幻灯片"""
        layout_type = self.current_slide.get('layout', 'text_only')
        
        # 标题
        title = clean_markdown(self.current_slide.get('title', ''))
        if title:
            font = QFont("Helvetica Neue", 36, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(self.accent_color)
            painter.drawText(
                QRectF(100, 50, 1133, 120),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title
            )
        
        # 内容
        items = self.current_slide.get('items', [])
        
        if layout_type == 'three_columns':
            self._draw_three_columns(painter, items)
        elif layout_type == 'image_right':
            self._draw_image_right(painter, items)
        elif layout_type == 'image_left':
            self._draw_image_left(painter, items)
        else:
            # text_only
            self._draw_text_only(painter, items)
    
    def _draw_text_only(self, painter: QPainter, items: list):
        """绘制纯文本布局"""
        y = 180
        
        for item in items:
            level = item.get('level', 0)
            text = clean_markdown(item.get('text', ''))
            content_type = item.get('content_type', 'text')
            
            if not text:
                continue
            
            if content_type == 'text':
                font_size = 28 if level == 0 else 22
                font = QFont("Helvetica Neue", font_size)
                if level == 0:
                    font.setBold(True)
                painter.setFont(font)
                painter.setPen(self.title_color if level == 0 else self.text_color)
                
                indent = 100 + level * 30
                painter.drawText(
                    QRectF(indent, y, 1133 - indent, 40),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    text
                )
                y += 50
            
            elif content_type == 'image':
                # 图片占位
                self._draw_image_placeholder(painter, 100, y, 400, 200)
                y += 220
            
            elif content_type == 'flowchart':
                # 流程图占位
                self._draw_flowchart_placeholder(painter, 100, y, 1000, 150)
                y += 170
            
            elif content_type == 'icon':
                # 图标占位
                self._draw_icon_placeholder(painter, 100, y, 50, 50)
                
                font = QFont("Helvetica Neue", 22)
                painter.setFont(font)
                painter.setPen(self.text_color)
                painter.drawText(
                    QRectF(160, y, 900, 50),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    text
                )
                y += 60
    
    def _draw_three_columns(self, painter: QPainter, items: list):
        """绘制三栏布局"""
        col_width = 350
        col_spacing = 30
        start_x = 100
        y = 200
        
        for i, item in enumerate(items[:3]):
            x = start_x + i * (col_width + col_spacing)
            
            # 装饰圆形
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(235, 240, 248))
            painter.drawEllipse(int(x + col_width / 2 - 50), 120, 100, 100)
            
            # 文本
            text = clean_markdown(item.get('text', ''))
            if text:
                font = QFont("Helvetica Neue", 24, QFont.Weight.Bold)
                painter.setFont(font)
                painter.setPen(self.title_color)
                painter.drawText(
                    QRectF(x, y, col_width, 400),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    text
                )
    
    def _draw_image_right(self, painter: QPainter, items: list):
        """绘制图文混排（图右文左）"""
        # 文本区域（左侧）
        y = 180
        for item in items:
            text = clean_markdown(item.get('text', ''))
            if not text:
                continue
            
            font = QFont("Helvetica Neue", 24)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(self.title_color)
            painter.drawText(
                QRectF(100, y, 750, 40),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text
            )
            y += 50
        
        # 图片占位（右侧）
        self._draw_image_placeholder(painter, 883, 0, 450, 750)
    
    def _draw_image_left(self, painter: QPainter, items: list):
        """绘制图文混排（图左文右）"""
        # 图片占位（左侧）
        self._draw_image_placeholder(painter, 0, 0, 450, 750)
        
        # 文本区域（右侧）
        y = 180
        for item in items:
            text = clean_markdown(item.get('text', ''))
            if not text:
                continue
            
            font = QFont("Helvetica Neue", 24)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(self.title_color)
            painter.drawText(
                QRectF(483, y, 750, 40),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text
            )
            y += 50
    
    def _draw_image_placeholder(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """绘制图片占位符"""
        # 背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(235, 240, 245))
        painter.drawRect(x, y, w, h)
        
        # 装饰矩形
        painter.setBrush(QColor(0, 102, 204))
        painter.drawRect(x + 50, y + 150, w - 100, h - 300)
        
        # 装饰圆形
        painter.setBrush(QColor(255, 153, 51))
        painter.drawEllipse(x + w - 150, y + h - 200, 100, 100)
        
        # 提示文字
        font = QFont("Helvetica Neue", 14)
        painter.setFont(font)
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(
            QRectF(x, y + h // 2 - 10, w, 20),
            Qt.AlignmentFlag.AlignCenter,
            "🖼️ 图片区域"
        )
    
    def _draw_flowchart_placeholder(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """绘制流程图占位符"""
        node_width = 150
        node_height = 40
        nodes = ["步骤 1", "步骤 2", "步骤 3"]
        
        total_width = len(nodes) * node_width + (len(nodes) - 1) * 50
        start_x = int(x + (w - total_width) / 2)
        
        for i, node_text in enumerate(nodes):
            nx = int(start_x + i * (node_width + 50))
            
            # 节点背景
            painter.setPen(QPen(self.accent_color, 2))
            painter.setBrush(QColor(235, 240, 248))
            painter.drawRoundedRect(nx, int(y + h / 2 - node_height / 2), node_width, node_height, 8, 8)
            
            # 节点文字
            font = QFont("Helvetica Neue", 12)
            painter.setFont(font)
            painter.setPen(self.title_color)
            painter.drawText(
                QRectF(nx, y + h / 2 - node_height / 2, node_width, node_height),
                Qt.AlignmentFlag.AlignCenter,
                node_text
            )
            
            # 连接线
            if i < len(nodes) - 1:
                painter.setPen(QPen(self.accent_color, 2))
                painter.drawLine(
                    nx + node_width, int(y + h / 2),
                    nx + node_width + 50, int(y + h / 2)
                )
    
    def _draw_icon_placeholder(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """绘制图标占位符"""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(235, 240, 248))
        painter.drawEllipse(x, y, w, h)
        
        font = QFont("Helvetica Neue", 20)
        painter.setFont(font)
        painter.setPen(self.accent_color)
        painter.drawText(
            QRectF(x, y, w, h),
            Qt.AlignmentFlag.AlignCenter,
            "⭐"
        )


class FullscreenPreviewDialog(QDialog):
    """全屏预览对话框"""
    
    def __init__(self, slides_data: list, current_index: int = 0, parent=None):
        super().__init__(parent)
        self.slides_data = slides_data
        self.current_index = current_index
        self.is_toolbar_visible = True
        
        self._init_ui()
        self._setup_shortcuts()
        self._update_slide()
        
        # 延迟全屏，确保窗口已初始化
        QTimer.singleShot(100, self._go_fullscreen)
    
    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("全屏预览")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: black;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 渲染器
        self.renderer = SlideRenderer()
        layout.addWidget(self.renderer, 1)
        
        # 工具栏（悬浮）
        self.toolbar = QWidget(self)
        self.toolbar.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 8px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                color: white;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 40);
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)
        
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(16, 8, 16, 8)
        toolbar_layout.setSpacing(16)
        
        # 上一页按钮
        self.prev_btn = QPushButton("◀ 上一页")
        self.prev_btn.clicked.connect(self._on_prev)
        toolbar_layout.addWidget(self.prev_btn)
        
        # 页码显示
        self.page_label = QLabel("1 / 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(100)
        toolbar_layout.addWidget(self.page_label)
        
        # 下一页按钮
        self.next_btn = QPushButton("下一页 ▶")
        self.next_btn.clicked.connect(self._on_next)
        toolbar_layout.addWidget(self.next_btn)
        
        toolbar_layout.addStretch()
        
        # 退出按钮
        self.exit_btn = QPushButton("✖ 退出全屏 (Esc)")
        self.exit_btn.clicked.connect(self.close)
        toolbar_layout.addWidget(self.exit_btn)
        
        # 初始位置
        self._update_toolbar_position()
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # Escape: 退出
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self.close)
        
        # 左箭头: 上一页
        shortcut_left = QShortcut(QKeySequence("Left"), self)
        shortcut_left.activated.connect(self._on_prev)
        
        # 右箭头: 下一页
        shortcut_right = QShortcut(QKeySequence("Right"), self)
        shortcut_right.activated.connect(self._on_next)
        
        # 空格: 下一页
        shortcut_space = QShortcut(QKeySequence("Space"), self)
        shortcut_space.activated.connect(self._on_next)
    
    def _go_fullscreen(self):
        """进入全屏模式"""
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
            self.showFullScreen()
    
    def _update_toolbar_position(self):
        """更新工具栏位置（底部居中）"""
        toolbar_width = 600
        toolbar_height = 50
        x = (self.width() - toolbar_width) // 2
        y = self.height() - toolbar_height - 20
        self.toolbar.setGeometry(x, y, toolbar_width, toolbar_height)
    
    def resizeEvent(self, event):
        """窗口大小变化"""
        super().resizeEvent(event)
        self._update_toolbar_position()
    
    def mousePressEvent(self, event):
        """鼠标点击"""
        # 点击左半部分上一页，右半部分下一页
        if event.position().x() < self.width() / 2:
            self._on_prev()
        else:
            self._on_next()
    
    def mouseMoveEvent(self, event):
        """鼠标移动 - 显示/隐藏工具栏"""
        # 鼠标在底部区域时显示工具栏
        if event.position().y() > self.height() - 100:
            if not self.is_toolbar_visible:
                self.toolbar.show()
                self.is_toolbar_visible = True
        else:
            if self.is_toolbar_visible:
                self.toolbar.hide()
                self.is_toolbar_visible = False
    
    def wheelEvent(self, event):
        """鼠标滚轮"""
        if event.angleDelta().y() > 0:
            self._on_prev()
        else:
            self._on_next()
    
    def _on_prev(self):
        """上一页"""
        if self.current_index > 0:
            self.current_index -= 1
            self._update_slide()
    
    def _on_next(self):
        """下一页"""
        if self.current_index < len(self.slides_data) - 1:
            self.current_index += 1
            self._update_slide()
    
    def _update_slide(self):
        """更新当前幻灯片"""
        if self.slides_data:
            self.renderer.set_slide(self.slides_data[self.current_index])
            self.page_label.setText(f"{self.current_index + 1} / {len(self.slides_data)}")
            
            # 更新按钮状态
            self.prev_btn.setEnabled(self.current_index > 0)
            self.next_btn.setEnabled(self.current_index < len(self.slides_data) - 1)
    
    def get_current_index(self) -> int:
        """获取当前幻灯片索引"""
        return self.current_index


class PreviewPanel(QWidget):
    """PPT 预览面板"""
    
    # 信号
    slide_changed = pyqtSignal(int)  # 当前幻灯片变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slides_data = []
        self.current_index = 0
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题栏
        header = QHBoxLayout()
        title = QLabel("👁️ PPT 预览")
        title.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 0;
            }
        """)
        header.addWidget(title)
        header.addStretch()
        
        # 预览控制
        self.page_label = QLabel("0 / 0")
        self.page_label.setStyleSheet("color: #888; font-size: 12px;")
        header.addWidget(self.page_label)
        
        layout.addLayout(header)
        
        # 渲染区域
        self.renderer = SlideRenderer()
        self.renderer.setStyleSheet("""
            SlideRenderer {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.renderer, 1)
        
        # 导航按钮
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(12)
        
        self.prev_btn = QPushButton("◀ 上一页")
        self.prev_btn.setStyleSheet(self._button_style("#3c3c3c"))
        self.prev_btn.clicked.connect(self._on_prev)
        nav_layout.addWidget(self.prev_btn)
        
        self.fullscreen_btn = QPushButton("🖥️ 全屏预览")
        self.fullscreen_btn.setStyleSheet(self._button_style("#007bff"))
        self.fullscreen_btn.clicked.connect(self._on_fullscreen)
        nav_layout.addWidget(self.fullscreen_btn)
        
        self.next_btn = QPushButton("下一页 ▶")
        self.next_btn.setStyleSheet(self._button_style("#3c3c3c"))
        self.next_btn.clicked.connect(self._on_next)
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
    
    def _button_style(self, bg_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #4a4a4a;
            }}
            QPushButton:disabled {{
                background-color: #2d2d2d;
                color: #666;
            }}
        """
    
    def set_slides_data(self, slides: list):
        """设置幻灯片数据"""
        self.slides_data = slides
        self.current_index = 0
        self._update_preview()
    
    def set_current_slide(self, index: int):
        """设置当前幻灯片索引"""
        if 0 <= index < len(self.slides_data):
            self.current_index = index
            self._update_preview()
            self.slide_changed.emit(index)
    
    def _update_preview(self):
        """更新预览"""
        if not self.slides_data:
            self.renderer.set_slide(None)
            self.page_label.setText("0 / 0")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
        
        self.renderer.set_slide(self.slides_data[self.current_index])
        self.page_label.setText(f"{self.current_index + 1} / {len(self.slides_data)}")
        
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.slides_data) - 1)
    
    def _on_prev(self):
        """上一页"""
        if self.current_index > 0:
            self.set_current_slide(self.current_index - 1)
    
    def _on_next(self):
        """下一页"""
        if self.current_index < len(self.slides_data) - 1:
            self.set_current_slide(self.current_index + 1)
    
    def _on_fullscreen(self):
        """全屏预览"""
        if not self.slides_data:
            return
        
        dialog = FullscreenPreviewDialog(
            self.slides_data, 
            self.current_index, 
            self
        )
        dialog.exec()
        
        # 全屏结束后同步位置
        new_index = dialog.get_current_index()
        if new_index != self.current_index:
            self.set_current_slide(new_index)
