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
    QSlider, QSpinBox, QFrame, QDialog, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QKeySequence, QShortcut, QGuiApplication
)

# 导入 PPT 生成器
from ppt_generator import generate_ppt_from_json, clean_markdown


class SlideRenderer(QWidget):
    """PyQt 自绘幻灯片渲染器"""
    
    # 信号
    element_clicked = pyqtSignal(str, int)  # (元素类型, 元素索引)
    title_double_clicked = pyqtSignal()
    edit_requested = pyqtSignal(str, int, str)  # (元素类型, 元素索引, 当前文本)
    
    # 幻灯片尺寸（16:9，与 ppt_generator.py 一致）
    SLIDE_WIDTH = 1333
    SLIDE_HEIGHT = 750
    
    # 拖放相关信号
    text_dropped = pyqtSignal(str, str, int)  # (文本, 元素类型, 元素索引)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_slide = None
        self.scale_factor = 1.0
        self._offset_x = 0
        self._offset_y = 0
        
        # 设置固定比例
        self.setMinimumSize(400, 225)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)  # 启用拖放
        
        # 颜色方案（与 ppt_generator.py 一致）
        self.bg_color = QColor(250, 250, 252)
        self.accent_color = QColor(0, 82, 204)
        self.title_color = QColor(15, 25, 45)
        self.text_color = QColor(60, 64, 67)
        self.light_bg = QColor(235, 240, 248)
        
        # 悬停状态
        self._hover_element = None  # (type, index) 或 None
        self._drop_target = None  # 拖放目标元素
    
    def set_slide(self, slide_data: dict):
        """设置当前幻灯片数据"""
        self.current_slide = slide_data
        self.update()
    
    def _hit_test(self, pos) -> tuple:
        """检测点击位置对应的元素
        
        Returns:
            (element_type, element_index) 或 (None, -1)
            element_type: "title", "subtitle", "item", "chart", "table"
            element_index: 元素索引（标题为-1）
        """
        if not self.current_slide:
            return (None, -1)
        
        # 将 widget 坐标转换为幻灯片坐标
        slide_x = (pos.x() - self._offset_x) / self.scale_factor
        slide_y = (pos.y() - self._offset_y) / self.scale_factor
        
        # 检查是否在幻灯片区域内
        if not (0 <= slide_x <= self.SLIDE_WIDTH and 0 <= slide_y <= self.SLIDE_HEIGHT):
            return (None, -1)
        
        slide_type = self.current_slide.get('type', 'content')
        
        if slide_type == 'title':
            # 封面页：标题区域 (100, 250, 800, 100)
            if 100 <= slide_x <= 900 and 250 <= slide_y <= 350:
                return ("title", -1)
            # 副标题区域 (100, 380, 800, 60)
            if 100 <= slide_x <= 900 and 380 <= slide_y <= 440:
                return ("subtitle", -1)
        else:
            # 内容页：标题区域 (100, 50, 1133, 120)
            if 100 <= slide_x <= 1233 and 50 <= slide_y <= 170:
                return ("title", -1)
            
            # 检查是否是图表或表格
            items = self.current_slide.get('items', [])
            if items:
                first_item = items[0]
                content_type = first_item.get('content_type', 'text')
                
                if content_type == 'table':
                    # 表格区域 (100, 200, table_width, table_height)
                    table_data = first_item.get('table_data', {})
                    columns = table_data.get('columns', [])
                    if columns:
                        col_width = min(200, (self.SLIDE_WIDTH - 200) // len(columns))
                        table_width = col_width * len(columns)
                        rows = table_data.get('rows', [])
                        table_height = 45 * (1 + len(rows))
                        if 100 <= slide_x <= 100 + table_width and 200 <= slide_y <= 200 + table_height:
                            return ("table", 0)
                
                elif content_type in ('chart', 'flowchart'):
                    # 图表区域 (150, 220, 1000, 450)
                    if 150 <= slide_x <= 1150 and 220 <= slide_y <= 670:
                        return ("chart", 0)
            
            # 内容项区域
            y = 180
            layout_type = self.current_slide.get('layout', 'text_only')
            
            if layout_type == 'three_columns':
                # 三栏布局
                col_width = 350
                col_spacing = 30
                start_x = 100
                for i, item in enumerate(items[:3]):
                    x = start_x + i * (col_width + col_spacing)
                    if x <= slide_x <= x + col_width and 120 <= slide_y <= 600:
                        return ("item", i)
            elif layout_type in ('image_right', 'image_left'):
                # 图文混排
                text_start_x = 100 if layout_type == 'image_right' else 483
                text_end_x = 850 if layout_type == 'image_right' else 1233
                for i, item in enumerate(items):
                    if text_start_x <= slide_x <= text_end_x and y <= slide_y <= y + 40:
                        return ("item", i)
                    y += 50
            else:
                # 纯文本布局
                for i, item in enumerate(items):
                    level = item.get('level', 0)
                    indent = 100 + level * 30
                    if indent <= slide_x <= 1233 and y <= slide_y <= y + 40:
                        return ("item", i)
                    y += 50
        
        return (None, -1)
    
    def _get_element_text(self, element_type: str, element_index: int) -> str:
        """获取元素的当前文本"""
        if not self.current_slide:
            return ""
        
        if element_type == "title":
            return self.current_slide.get('title', '')
        elif element_type == "subtitle":
            return self.current_slide.get('subtitle', '')
        elif element_type == "item":
            items = self.current_slide.get('items', [])
            if 0 <= element_index < len(items):
                return items[element_index].get('text', '')
        return ""
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            element_type, element_index = self._hit_test(event.position())
            if element_type:
                self.element_clicked.emit(element_type, element_index)
                self._hover_element = (element_type, element_index)
                self.update()
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件 - 触发编辑"""
        if event.button() == Qt.MouseButton.LeftButton:
            element_type, element_index = self._hit_test(event.position())
            if element_type:
                text = self._get_element_text(element_type, element_index)
                self.edit_requested.emit(element_type, element_index, text)
        super().mouseDoubleClickEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 更新悬停状态"""
        element_type, element_index = self._hit_test(event.position())
        new_hover = (element_type, element_index) if element_type else None
        
        if new_hover != self._hover_element:
            self._hover_element = new_hover
            self.setCursor(Qt.CursorShape.PointingHandCursor if element_type else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        if self._hover_element:
            self._hover_element = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
        super().leaveEvent(event)
    
    def contextMenuEvent(self, event):
        """右键菜单"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        element_type, element_index = self._hit_test(event.pos())
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #007bff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555;
                margin: 4px 8px;
            }
        """)
        
        if element_type == "title":
            edit_action = QAction("✏️ 编辑标题", self)
            edit_action.triggered.connect(lambda: self._on_edit_element(element_type, element_index))
            menu.addAction(edit_action)
            
            menu.addSeparator()
        
        elif element_type == "subtitle":
            edit_action = QAction("✏️ 编辑副标题", self)
            edit_action.triggered.connect(lambda: self._on_edit_element(element_type, element_index))
            menu.addAction(edit_action)
            
            menu.addSeparator()
        
        elif element_type == "item":
            edit_action = QAction("✏️ 编辑内容", self)
            edit_action.triggered.connect(lambda: self._on_edit_element(element_type, element_index))
            menu.addAction(edit_action)
            
            delete_action = QAction("🗑️ 删除此项", self)
            delete_action.triggered.connect(lambda: self._on_delete_item(element_index))
            menu.addAction(delete_action)
            
            menu.addSeparator()
        
        elif element_type in ("chart", "table"):
            edit_action = QAction("✏️ 编辑数据", self)
            edit_action.triggered.connect(lambda: self._on_edit_element(element_type, element_index))
            menu.addAction(edit_action)
            
            convert_action = QAction("🔄 转换为文本", self)
            convert_action.triggered.connect(lambda: self._on_convert_to_text(element_index))
            menu.addAction(convert_action)
            
            menu.addSeparator()
        
        # 通用操作
        add_action = QAction("➕ 添加新要点", self)
        add_action.triggered.connect(self._on_add_item)
        menu.addAction(add_action)
        
        menu.exec(event.globalPos())
    
    def _on_edit_element(self, element_type: str, element_index: int):
        """编辑元素"""
        text = self._get_element_text(element_type, element_index)
        self.edit_requested.emit(element_type, element_index, text)
    
    def _on_delete_item(self, item_index: int):
        """删除要点"""
        if not self.current_slide:
            return
        
        items = self.current_slide.get('items', [])
        if 0 <= item_index < len(items):
            items.pop(item_index)
            self.update()
    
    def _on_add_item(self):
        """添加新要点"""
        if not self.current_slide:
            return
        
        items = self.current_slide.setdefault('items', [])
        items.append({
            "text": "新要点",
            "level": 0,
            "content_type": "text"
        })
        self.update()
    
    def _on_convert_to_text(self, item_index: int):
        """将图表/表格转换为文本"""
        if not self.current_slide:
            return
        
        items = self.current_slide.get('items', [])
        if 0 <= item_index < len(items):
            item = items[item_index]
            content_type = item.get('content_type', 'text')
            
            if content_type == 'chart':
                # 将图表数据转换为文本描述
                chart_data = item.get('chart_data', {})
                title = chart_data.get('title', '')
                labels = chart_data.get('labels', [])
                datasets = chart_data.get('datasets', [])
                
                text_parts = []
                if title:
                    text_parts.append(title)
                for ds in datasets:
                    label = ds.get('label', '')
                    data = ds.get('data', [])
                    for i, val in enumerate(data):
                        if i < len(labels):
                            text_parts.append(f"{labels[i]}: {val}")
                
                items[item_index] = {
                    "text": "\n".join(text_parts),
                    "level": 0,
                    "content_type": "text"
                }
            
            elif content_type == 'table':
                # 将表格数据转换为文本
                table_data = item.get('table_data', {})
                columns = table_data.get('columns', [])
                rows = table_data.get('rows', [])
                
                text_parts = []
                if columns:
                    text_parts.append(" | ".join(str(c) for c in columns))
                    text_parts.append("-" * 40)
                for row in rows:
                    text_parts.append(" | ".join(str(c) for c in row))
                
                items[item_index] = {
                    "text": "\n".join(text_parts),
                    "level": 0,
                    "content_type": "text"
                }
            
            self.update()
    
    # 拖放事件处理
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            # 检查是否是原文面板的拖拽
            if event.mimeData().hasFormat("application/x-sourcetext"):
                event.acceptProposedAction()
                # 高亮可能的放置目标
                element_type, element_index = self._hit_test(event.position())
                self._drop_target = (element_type, element_index) if element_type else None
                self.update()
            else:
                event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            # 更新拖放目标
            element_type, element_index = self._hit_test(event.position())
            new_target = (element_type, element_index) if element_type else None
            if new_target != self._drop_target:
                self._drop_target = new_target
                self.update()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self._drop_target = None
        self.update()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        """放置事件"""
        if event.mimeData().hasText():
            text = event.mimeData().text()
            element_type, element_index = self._hit_test(event.position())
            
            if element_type:
                # 将文本添加到目标元素
                self._handle_drop(text, element_type, element_index)
                self.text_dropped.emit(text, element_type, element_index)
            
            self._drop_target = None
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def _handle_drop(self, text: str, element_type: str, element_index: int):
        """处理拖放操作"""
        if not self.current_slide:
            return
        
        if element_type == "title":
            # 追加到标题
            current = self.current_slide.get('title', '')
            self.current_slide['title'] = f"{current} {text}" if current else text
        
        elif element_type == "subtitle":
            # 追加到副标题
            current = self.current_slide.get('subtitle', '')
            self.current_slide['subtitle'] = f"{current} {text}" if current else text
        
        elif element_type == "item":
            items = self.current_slide.get('items', [])
            if 0 <= element_index < len(items):
                # 追加到现有要点
                current = items[element_index].get('text', '')
                items[element_index]['text'] = f"{current} {text}" if current else text
            else:
                # 添加为新要点
                items.append({
                    "text": text,
                    "level": 0,
                    "content_type": "text"
                })
        
        else:
            # 添加为新要点
            items = self.current_slide.setdefault('items', [])
            items.append({
                "text": text,
                "level": 0,
                "content_type": "text"
            })
        
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
        
        # 计算居中偏移（保存供 _hit_test 使用）
        self._offset_x = (widget_width - self.SLIDE_WIDTH * self.scale_factor) / 2
        self._offset_y = (widget_height - self.SLIDE_HEIGHT * self.scale_factor) / 2
        
        # 应用变换
        painter.translate(self._offset_x, self._offset_y)
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
        
        # 绘制悬停高亮效果
        if self._hover_element:
            self._draw_hover_highlight(painter, self._hover_element[0], self._hover_element[1])
        
        # 绘制拖放目标高亮效果
        if self._drop_target:
            self._draw_drop_target_highlight(painter, self._drop_target[0], self._drop_target[1])
    
    def _draw_drop_target_highlight(self, painter: QPainter, element_type: str, element_index: int):
        """绘制拖放目标高亮效果"""
        painter.save()
        
        # 设置高亮样式（绿色虚线边框）
        highlight_color = QColor(40, 167, 69, 60)  # 半透明绿色
        highlight_border = QColor(40, 167, 69, 150)
        
        painter.setPen(QPen(highlight_border, 3, Qt.PenStyle.DashLine))
        painter.setBrush(highlight_color)
        
        # 根据元素类型绘制高亮区域
        if element_type == "title":
            slide_type = self.current_slide.get('type', 'content')
            if slide_type == 'title':
                painter.drawRoundedRect(QRectF(95, 245, 810, 110), 4, 4)
            else:
                painter.drawRoundedRect(QRectF(95, 45, 1143, 130), 4, 4)
        
        elif element_type == "item":
            items = self.current_slide.get('items', [])
            if 0 <= element_index < len(items):
                layout_type = self.current_slide.get('layout', 'text_only')
                y = 180 + element_index * 50
                indent = 100
                painter.drawRoundedRect(QRectF(indent - 5, y - 5, 1133 - indent + 10, 50), 4, 4)
        
        painter.restore()
    
    def _draw_hover_highlight(self, painter: QPainter, element_type: str, element_index: int):
        """绘制悬停高亮效果"""
        # 保存当前画笔状态
        painter.save()
        
        # 设置高亮样式
        highlight_color = QColor(0, 123, 255, 40)  # 半透明蓝色
        highlight_border = QColor(0, 123, 255, 100)
        
        painter.setPen(QPen(highlight_border, 2, Qt.PenStyle.DashLine))
        painter.setBrush(highlight_color)
        
        if element_type == "title":
            slide_type = self.current_slide.get('type', 'content')
            if slide_type == 'title':
                # 封面标题区域
                painter.drawRoundedRect(QRectF(95, 245, 810, 110), 4, 4)
            else:
                # 内容页标题区域
                painter.drawRoundedRect(QRectF(95, 45, 1143, 130), 4, 4)
        
        elif element_type == "subtitle":
            painter.drawRoundedRect(QRectF(95, 375, 810, 70), 4, 4)
        
        elif element_type == "item":
            items = self.current_slide.get('items', [])
            if 0 <= element_index < len(items):
                layout_type = self.current_slide.get('layout', 'text_only')
                
                if layout_type == 'three_columns':
                    col_width = 350
                    col_spacing = 30
                    start_x = 100
                    if element_index < 3:
                        x = start_x + element_index * (col_width + col_spacing)
                        painter.drawRoundedRect(QRectF(x - 5, 115, col_width + 10, 490), 4, 4)
                
                elif layout_type == 'image_right':
                    y = 180 + element_index * 50
                    painter.drawRoundedRect(QRectF(95, y - 5, 760, 50), 4, 4)
                
                elif layout_type == 'image_left':
                    y = 180 + element_index * 50
                    painter.drawRoundedRect(QRectF(478, y - 5, 760, 50), 4, 4)
                
                else:
                    # 纯文本布局
                    level = items[element_index].get('level', 0)
                    indent = 100 + level * 30
                    y = 180 + element_index * 50
                    painter.drawRoundedRect(QRectF(indent - 5, y - 5, 1133 - indent + 10, 50), 4, 4)
        
        elif element_type == "chart":
            painter.drawRoundedRect(QRectF(145, 215, 1010, 460), 4, 4)
        
        elif element_type == "table":
            painter.drawRoundedRect(QRectF(95, 195, self.SLIDE_WIDTH - 200, 300), 4, 4)
        
        # 恢复画笔状态
        painter.restore()
    
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
        
        # 检查是否有特殊内容类型（表格/图表/流程图）
        items = self.current_slide.get('items', [])
        
        # 检查第一个 item 是否为特殊类型
        if items:
            first_item = items[0]
            content_type = first_item.get('content_type', 'text')
            
            if content_type == 'table':
                table_data = first_item.get('table_data', {})
                if table_data.get('columns'):  # 有表格数据才绘制
                    self._draw_table(painter, table_data)
                    return
            elif content_type == 'chart':
                chart_data = first_item.get('chart_data', {})
                if chart_data.get('labels') and chart_data.get('datasets'):
                    self._draw_chart(painter, chart_data,
                                   first_item.get('chart_type', 'bar'))
                    return
            elif content_type == 'flowchart':
                flowchart_data = first_item.get('flowchart_data', {})
                if flowchart_data.get('steps'):
                    self._draw_flowchart(painter, flowchart_data)
                    return
                else:
                    # flowchart_data 缺失，回退到占位符
                    self._draw_flowchart_placeholder(painter, 150, 220, 1000, 450)
                    return
        
        # 布局级回退：layout 字段指定了特殊类型但 items 中无 content_type
        if layout_type == 'table' and items:
            table_data = items[0].get('table_data', {})
            if table_data.get('columns'):
                self._draw_table(painter, table_data)
                return
        elif layout_type == 'chart' and items:
            chart_data = items[0].get('chart_data', {})
            if chart_data.get('labels') and chart_data.get('datasets'):
                self._draw_chart(painter, chart_data, items[0].get('chart_type', 'bar'))
                return
        elif layout_type == 'flowchart' and items:
            flowchart_data = items[0].get('flowchart_data', {})
            if flowchart_data.get('steps'):
                self._draw_flowchart(painter, flowchart_data)
                return
            else:
                self._draw_flowchart_placeholder(painter, 150, 220, 1000, 450)
                return
        
        # 常规布局
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
    
    def _draw_flowchart(self, painter: QPainter, flowchart_data: dict):
        """绘制流程图（基于 flowchart_data 的真实数据）
        
        支持 horizontal 和 vertical 布局。
        """
        steps = flowchart_data.get("steps", [])
        layout = flowchart_data.get("layout", "horizontal")
        fc_title = flowchart_data.get("title", "")
        
        if not steps:
            return
        
        # 流程图标题
        if fc_title:
            font = QFont("Helvetica Neue", 20, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(self.title_color)
            painter.drawText(
                QRectF(150, 170, 1000, 40),
                Qt.AlignmentFlag.AlignCenter,
                fc_title
            )
        
        num_steps = len(steps)
        
        if layout == "vertical" or (layout == "horizontal" and num_steps > 5):
            # 垂直布局
            node_width = 350
            node_height = 40
            gap = 30
            total_height = num_steps * node_height + (num_steps - 1) * gap
            start_x = int((self.SLIDE_WIDTH - node_width) / 2)
            start_y = 230
            
            for i, step_text in enumerate(steps):
                ny = start_y + i * (node_height + gap)
                
                # 节点背景（首尾用圆角矩形，中间用普通矩形）
                painter.setPen(QPen(self.accent_color, 2))
                if i == 0 or i == num_steps - 1:
                    painter.setBrush(QColor(0, 82, 204))
                    text_color = QColor(255, 255, 255)
                else:
                    painter.setBrush(QColor(235, 240, 248))
                    text_color = self.title_color
                painter.drawRoundedRect(start_x, ny, node_width, node_height, 8, 8)
                
                # 节点文字
                font = QFont("Helvetica Neue", 12)
                painter.setFont(font)
                painter.setPen(text_color)
                # 截断过长文字
                display_text = step_text[:25] + "..." if len(step_text) > 25 else step_text
                painter.drawText(
                    QRectF(start_x, ny, node_width, node_height),
                    Qt.AlignmentFlag.AlignCenter,
                    display_text
                )
                
                # 连接箭头
                if i < num_steps - 1:
                    arrow_x = start_x + node_width // 2
                    painter.setPen(QPen(self.accent_color, 2))
                    painter.drawLine(arrow_x, ny + node_height, arrow_x, ny + node_height + gap)
                    # 箭头头部
                    arrow_y = ny + node_height + gap
                    painter.drawLine(arrow_x, arrow_y, arrow_x - 6, arrow_y - 8)
                    painter.drawLine(arrow_x, arrow_y, arrow_x + 6, arrow_y - 8)
        else:
            # 水平布局
            max_node_w = 180
            node_height = 50
            gap = 40
            total_width = num_steps * max_node_w + (num_steps - 1) * gap
            # 动态调整节点宽度
            available_width = 1000
            if total_width > available_width:
                node_width = max(100, (available_width - (num_steps - 1) * gap) // num_steps)
            else:
                node_width = max_node_w
            total_width = num_steps * node_width + (num_steps - 1) * gap
            start_x = int((self.SLIDE_WIDTH - total_width) / 2)
            start_y = 350
            
            for i, step_text in enumerate(steps):
                nx = start_x + i * (node_width + gap)
                
                # 节点
                painter.setPen(QPen(self.accent_color, 2))
                if i == 0 or i == num_steps - 1:
                    painter.setBrush(QColor(0, 82, 204))
                    text_color = QColor(255, 255, 255)
                else:
                    painter.setBrush(QColor(235, 240, 248))
                    text_color = self.title_color
                painter.drawRoundedRect(nx, start_y, node_width, node_height, 8, 8)
                
                # 节点文字
                font = QFont("Helvetica Neue", 11)
                painter.setFont(font)
                painter.setPen(text_color)
                display_text = step_text[:15] + "..." if len(step_text) > 15 else step_text
                painter.drawText(
                    QRectF(nx, start_y, node_width, node_height),
                    Qt.AlignmentFlag.AlignCenter,
                    display_text
                )
                
                # 连接箭头
                if i < num_steps - 1:
                    arrow_start_x = nx + node_width
                    arrow_end_x = nx + node_width + gap
                    arrow_y = start_y + node_height // 2
                    painter.setPen(QPen(self.accent_color, 2))
                    painter.drawLine(arrow_start_x, arrow_y, arrow_end_x, arrow_y)
                    # 箭头头部
                    painter.drawLine(arrow_end_x, arrow_y, arrow_end_x - 8, arrow_y - 5)
                    painter.drawLine(arrow_end_x, arrow_y, arrow_end_x - 8, arrow_y + 5)
        
        # 步骤计数标签
        font = QFont("Helvetica Neue", 11)
        painter.setFont(font)
        painter.setPen(QColor(150, 150, 155))
        painter.drawText(
            QRectF(150, 680, 1000, 25),
            Qt.AlignmentFlag.AlignCenter,
            f"共 {num_steps} 个步骤"
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
    
    def _draw_table(self, painter: QPainter, table_data: dict):
        """绘制表格"""
        columns = table_data.get("columns", [])
        rows = table_data.get("rows", [])
        
        if not columns:
            return
        
        # 表格参数
        x_start = 100
        y_start = 200
        row_height = 45
        col_width = min(200, (self.SLIDE_WIDTH - 200) // len(columns))
        table_width = col_width * len(columns)
        
        # 绘制表头背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.accent_color)
        painter.drawRect(x_start, y_start, table_width, row_height)
        
        # 绘制表头文字
        font = QFont("Helvetica Neue", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        
        for i, col in enumerate(columns):
            col_x = x_start + i * col_width
            painter.drawText(
                QRectF(col_x + 8, y_start, col_width - 16, row_height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(col)
            )
        
        # 绘制数据行
        font = QFont("Helvetica Neue", 14)
        painter.setFont(font)
        
        for row_idx, row in enumerate(rows):
            row_y = y_start + (row_idx + 1) * row_height
            
            # 交替行背景
            if row_idx % 2 == 0:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(245, 247, 250))
                painter.drawRect(x_start, row_y, table_width, row_height)
            
            # 绘制单元格边框
            painter.setPen(QColor(220, 220, 225))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(x_start, row_y, table_width, row_height)
            
            # 绘制单元格文字
            painter.setPen(self.text_color)
            for i, cell in enumerate(row):
                if i >= len(columns):
                    break
                col_x = x_start + i * col_width
                painter.drawText(
                    QRectF(col_x + 8, row_y, col_width - 16, row_height),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    str(cell)
                )
        
        # 绘制表格边框
        painter.setPen(QPen(self.accent_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(x_start, y_start, table_width, row_height * (1 + len(rows)))
        
        # 绘制列分隔线
        painter.setPen(QPen(QColor(200, 200, 205), 1))
        for i in range(1, len(columns)):
            line_x = x_start + i * col_width
            painter.drawLine(line_x, y_start, line_x, y_start + row_height * (1 + len(rows)))
    
    def _draw_chart(self, painter: QPainter, chart_data: dict, chart_type: str):
        """绘制图表"""
        labels = chart_data.get("labels", [])
        datasets = chart_data.get("datasets", [])
        chart_title = chart_data.get("title", "")
        
        if not labels or not datasets:
            return
        
        # 图表区域
        chart_x = 150
        chart_y = 220
        chart_width = 1000
        chart_height = 450
        
        # 绘制图表标题
        if chart_title:
            font = QFont("Helvetica Neue", 20, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(self.title_color)
            painter.drawText(
                QRectF(chart_x, 170, chart_width, 40),
                Qt.AlignmentFlag.AlignCenter,
                chart_title
            )
        
        if chart_type == "bar":
            self._draw_bar_chart(painter, chart_x, chart_y, chart_width, chart_height,
                               labels, datasets)
        elif chart_type == "line":
            self._draw_line_chart(painter, chart_x, chart_y, chart_width, chart_height,
                                labels, datasets)
        elif chart_type in ("pie", "doughnut"):
            self._draw_pie_chart(painter, chart_x, chart_y, chart_width, chart_height,
                               labels, datasets, chart_type == "doughnut")
        else:
            # 默认柱状图
            self._draw_bar_chart(painter, chart_x, chart_y, chart_width, chart_height,
                               labels, datasets)
    
    def _draw_bar_chart(self, painter: QPainter, x: int, y: int, w: int, h: int,
                       labels: list, datasets: list):
        """绘制柱状图"""
        num_groups = len(labels)
        num_datasets = len(datasets)
        
        if num_groups == 0:
            return
        
        # 计算最大值
        max_val = 0
        for ds in datasets:
            for v in ds.get("data", []):
                max_val = max(max_val, float(v))
        if max_val == 0:
            max_val = 1
        
        # 绘制坐标轴
        painter.setPen(QPen(QColor(180, 180, 185), 1))
        painter.drawLine(x, y + h, x + w, y + h)  # X轴
        painter.drawLine(x, y, x, y + h)  # Y轴
        
        # 绘制网格线
        painter.setPen(QPen(QColor(230, 230, 235), 1, Qt.PenStyle.DashLine))
        for i in range(1, 5):
            grid_y = y + h - (h * i / 4)
            painter.drawLine(x, int(grid_y), x + w, int(grid_y))
            
            # Y轴标签
            val = max_val * i / 4
            font = QFont("Helvetica Neue", 11)
            painter.setFont(font)
            painter.setPen(QColor(150, 150, 155))
            painter.drawText(
                QRectF(x - 80, int(grid_y) - 10, 70, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{val:.0f}"
            )
        
        # 绘制柱状
        group_width = w / num_groups
        bar_width = group_width / (num_datasets + 1)
        bar_gap = bar_width * 0.2
        
        for g_idx, label in enumerate(labels):
            # X轴标签
            font = QFont("Helvetica Neue", 12)
            painter.setFont(font)
            painter.setPen(self.text_color)
            label_x = x + g_idx * group_width
            painter.drawText(
                QRectF(int(label_x), y + h + 5, int(group_width), 25),
                Qt.AlignmentFlag.AlignCenter,
                str(label)
            )
            
            # 绘制每组柱子
            for d_idx, dataset in enumerate(datasets):
                data = dataset.get("data", [])
                if g_idx >= len(data):
                    continue
                
                value = float(data[g_idx])
                bar_height = (value / max_val) * h * 0.9
                bar_x = label_x + (d_idx + 0.5) * bar_width + bar_gap
                bar_y = y + h - bar_height
                
                # 柱子颜色
                color_str = dataset.get("color", "#007bff")
                color = QColor(color_str)
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(
                    int(bar_x), int(bar_y),
                    int(bar_width - bar_gap * 2), int(bar_height),
                    4, 4
                )
        
        # 绘制图例
        if num_datasets > 1:
            legend_x = x + w - 200
            legend_y = y + 10
            font = QFont("Helvetica Neue", 12)
            painter.setFont(font)
            
            for d_idx, dataset in enumerate(datasets):
                color_str = dataset.get("color", "#007bff")
                color = QColor(color_str)
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRect(legend_x, legend_y + d_idx * 25, 15, 15)
                
                painter.setPen(self.text_color)
                painter.drawText(
                    QRectF(legend_x + 20, legend_y + d_idx * 25, 150, 20),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    dataset.get("label", f"系列{d_idx + 1}")
                )
    
    def _draw_line_chart(self, painter: QPainter, x: int, y: int, w: int, h: int,
                        labels: list, datasets: list):
        """绘制折线图"""
        num_points = len(labels)
        if num_points < 2:
            return
        
        # 计算最大值
        max_val = 0
        for ds in datasets:
            for v in ds.get("data", []):
                max_val = max(max_val, float(v))
        if max_val == 0:
            max_val = 1
        
        # 绘制坐标轴和网格
        painter.setPen(QPen(QColor(180, 180, 185), 1))
        painter.drawLine(x, y + h, x + w, y + h)
        painter.drawLine(x, y, x, y + h)
        
        painter.setPen(QPen(QColor(230, 230, 235), 1, Qt.PenStyle.DashLine))
        for i in range(1, 5):
            grid_y = y + h - (h * i / 4)
            painter.drawLine(x, int(grid_y), x + w, int(grid_y))
        
        # X轴标签
        font = QFont("Helvetica Neue", 11)
        painter.setFont(font)
        painter.setPen(self.text_color)
        
        point_gap = w / (num_points - 1)
        for i, label in enumerate(labels):
            lx = x + i * point_gap
            painter.drawText(
                QRectF(int(lx - 30), y + h + 5, 60, 25),
                Qt.AlignmentFlag.AlignCenter,
                str(label)
            )
        
        # 绘制折线
        for dataset in datasets:
            data = dataset.get("data", [])
            color_str = dataset.get("color", "#007bff")
            color = QColor(color_str)
            
            pen = QPen(color, 3)
            painter.setPen(pen)
            
            points = []
            for i, val in enumerate(data[:num_points]):
                px = x + i * point_gap
                py = y + h - (float(val) / max_val) * h * 0.9
                points.append(QPointF(px, py))
            
            # 绘制折线
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
            
            # 绘制数据点
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for point in points:
                painter.drawEllipse(point, 5, 5)
    
    def _draw_pie_chart(self, painter: QPainter, x: int, y: int, w: int, h: int,
                       labels: list, datasets: list, is_doughnut: bool = False):
        """绘制饼图/环形图"""
        if not datasets or not datasets[0].get("data"):
            return
        
        data = [float(v) for v in datasets[0]["data"][:len(labels)]]
        total = sum(data)
        if total == 0:
            return
        
        # 饼图区域
        radius = min(w, h) * 0.35
        center_x = x + w // 2
        center_y = y + h // 2
        
        # 默认颜色
        colors = [
            QColor("#007bff"), QColor("#28a745"), QColor("#ffc107"),
            QColor("#dc3545"), QColor("#6f42c1"), QColor("#17a2b8"),
            QColor("#fd7e14"), QColor("#20c997")
        ]
        
        # 绘制扇形
        start_angle = 0
        font = QFont("Helvetica Neue", 12)
        painter.setFont(font)
        
        for i, (value, label) in enumerate(zip(data, labels)):
            span_angle = int((value / total) * 360 * 16)  # Qt 用 1/16 度
            
            color = colors[i % len(colors)]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            
            painter.drawPie(
                int(center_x - radius), int(center_y - radius),
                int(radius * 2), int(radius * 2),
                start_angle, span_angle
            )
            
            # 标签
            mid_angle = (start_angle + span_angle / 2) / 16 * 3.14159 / 180
            label_radius = radius * 1.2
            lx = center_x + label_radius * 0.9 * __import__('math').cos(mid_angle)
            ly = center_y - label_radius * 0.9 * __import__('math').sin(mid_angle)
            
            painter.setPen(self.text_color)
            painter.drawText(
                QRectF(int(lx - 50), int(ly - 10), 100, 20),
                Qt.AlignmentFlag.AlignCenter,
                f"{label} ({value/total*100:.0f}%)"
            )
            
            start_angle += span_angle
        
        # 环形图：绘制中心白色圆
        if is_doughnut:
            inner_radius = radius * 0.5
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.bg_color)
            painter.drawEllipse(
                int(center_x - inner_radius), int(center_y - inner_radius),
                int(inner_radius * 2), int(inner_radius * 2)
            )


class InlineEditor(QLineEdit):
    """内联编辑器（悬浮在预览面板上）"""
    
    editing_finished = pyqtSignal(str, str, int)  # (element_type, new_text, element_index)
    editing_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.element_type = ""
        self.element_index = -1
        
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
        self.setWindowFlags(Qt.WindowType.Popup)
    
    def start_editing(self, element_type: str, element_index: int, text: str, rect: QRectF):
        """开始编辑"""
        self.element_type = element_type
        self.element_index = element_index
        self.setText(text)
        self.setGeometry(rect.toRect())
        self.show()
        self.setFocus()
        self.selectAll()
    
    def _on_confirm(self):
        """确认编辑"""
        self.editing_finished.emit(self.element_type, self.text(), self.element_index)
        self.hide()
    
    def keyPressEvent(self, event):
        """按键事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.editing_cancelled.emit()
            self.hide()
        else:
            super().keyPressEvent(event)


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
        
        # 内联编辑器
        self.inline_editor = InlineEditor(self)
        self.inline_editor.editing_finished.connect(self._on_edit_finished)
        self.inline_editor.editing_cancelled.connect(self._on_edit_cancelled)
        self.inline_editor.hide()
        
        # 连接渲染器信号
        self.renderer.element_clicked.connect(self._on_element_clicked)
        self.renderer.title_double_clicked.connect(self._on_title_double_clicked)
        self.renderer.edit_requested.connect(self._on_edit_requested)
        
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
        """设置幻灯片数据
        
        保留当前页码（如果有效），仅在越界时修正到合法范围。
        """
        self.slides_data = slides
        # 保留当前索引，仅在越界时修正
        if not slides:
            self.current_index = 0
        elif self.current_index >= len(slides):
            self.current_index = len(slides) - 1
        elif self.current_index < 0:
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
    
    def _on_element_clicked(self, element_type: str, element_index: int):
        """元素被点击"""
        # 可以在这里添加选中状态管理
        pass
    
    def _on_title_double_clicked(self):
        """标题被双击"""
        if not self.slides_data:
            return
        
        current_slide = self.slides_data[self.current_index]
        title = current_slide.get('title', '')
        self._show_inline_editor("title", -1, title)
    
    def _on_edit_requested(self, element_type: str, element_index: int, text: str):
        """编辑请求"""
        self._show_inline_editor(element_type, element_index, text)
    
    def _show_inline_editor(self, element_type: str, element_index: int, text: str):
        """显示内联编辑器"""
        # 计算编辑器位置（基于元素类型）
        # 这里简化处理，将编辑器放在渲染器中央
        renderer_rect = self.renderer.geometry()
        editor_width = min(400, renderer_rect.width() - 40)
        editor_height = 30
        
        x = renderer_rect.x() + (renderer_rect.width() - editor_width) / 2
        y = renderer_rect.y() + renderer_rect.height() / 2
        
        from PyQt6.QtCore import QRectF
        rect = QRectF(x, y, editor_width, editor_height)
        
        self.inline_editor.start_editing(element_type, element_index, text, rect)
    
    def _on_edit_finished(self, element_type: str, new_text: str, element_index: int):
        """编辑完成"""
        if not self.slides_data:
            return
        
        current_slide = self.slides_data[self.current_index]
        
        if element_type == "title":
            current_slide['title'] = new_text
        elif element_type == "subtitle":
            current_slide['subtitle'] = new_text
        elif element_type == "item":
            items = current_slide.get('items', [])
            if 0 <= element_index < len(items):
                items[element_index]['text'] = new_text
        
        # 更新预览
        self.renderer.update()
    
    def _on_edit_cancelled(self):
        """编辑取消"""
        pass
    
    def apply_theme(self, theme: dict):
        """应用主题样式"""
        # 更新渲染器背景色
        self.renderer.bg_color = QColor(theme['dialog_bg'])
        
        # 更新按钮样式
        for button in self.findChildren(QPushButton):
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme['button_bg']};
                    color: {theme['dialog_color']};
                    border: 1px solid {theme['border_color']};
                    border-radius: 4px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {theme['button_hover']};
                    border-color: {theme['accent_color']};
                }}
                QPushButton:pressed {{
                    background-color: {theme['button_pressed']};
                }}
            """)
        
        # 更新标签样式
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"""
                QLabel {{
                    color: {theme['dialog_color']};
                    font-size: 12px;
                    padding: 2px;
                }}
            """)
        
        # 更新页面标签样式
        if hasattr(self, 'page_label'):
            self.page_label.setStyleSheet(f"color: {theme['dialog_color']}; font-size: 12px;")
        
        # 更新渲染器样式
        self.renderer.setStyleSheet(f"""
            SlideRenderer {{
                background-color: {theme['dialog_bg']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
            }}
        """)
