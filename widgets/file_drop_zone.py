"""
文件拖拽区组件 - 简化文档处理流程
"""

import os
from typing import List, Optional, Callable, Dict, Tuple
from dataclasses import dataclass
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QIcon, QPixmap, QPainter, QColor


@dataclass
class FileInfo:
    """文件信息"""
    name: str
    path: str
    size: int
    file_type: str
    extension: str
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "file_type": self.file_type,
            "extension": self.extension
        }
    
    @property
    def size_str(self) -> str:
        """获取格式化的文件大小"""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.1f} GB"


# 文件类型映射
FILE_TYPE_MAPPING = {
    ".docx": ("Word文档", "word"),
    ".doc": ("Word文档", "word"),
    ".pptx": ("PPT文档", "ppt"),
    ".ppt": ("PPT文档", "ppt"),
    ".xlsx": ("Excel文档", "excel"),
    ".xls": ("Excel文档", "excel"),
    ".pdf": ("PDF文档", "pdf"),
    ".txt": ("文本文件", "text"),
    ".md": ("Markdown文件", "text"),
    ".markdown": ("Markdown文件", "text"),
    ".csv": ("CSV文件", "data"),
    ".json": ("JSON文件", "data"),
    ".xml": ("XML文件", "data"),
    ".html": ("HTML文件", "web"),
    ".htm": ("HTML文件", "web"),
}

# 文件类型图标颜色
FILE_TYPE_COLORS = {
    "word": "#2B579A",
    "ppt": "#D24726",
    "excel": "#217346",
    "pdf": "#FF0000",
    "text": "#666666",
    "data": "#FFA500",
    "web": "#0078D7",
}


class FileDropZone(QFrame):
    """文件拖拽区组件"""
    
    # 文件拖入信号
    file_entered = pyqtSignal(str)  # file_path
    
    # 文件拖出信号
    file_left = pyqtSignal()
    
    # 文件放下信号
    file_dropped = pyqtSignal(str, dict)  # (file_path, file_info)
    
    # 多文件放下信号
    files_dropped = pyqtSignal(list)  # [(file_path, file_info), ...]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 接受的文件扩展名
        self._accepted_extensions: List[str] = [
            ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
            ".pdf", ".txt", ".md", ".markdown", ".csv", ".json"
        ]
        
        # 当前文件信息
        self._current_file_info: Optional[FileInfo] = None
        
        # 是否正在拖拽
        self._is_hovering = False
        
        # 拖拽进入/离开回调
        self._on_drag_enter_callback: Optional[Callable] = None
        self._on_drag_leave_callback: Optional[Callable] = None
        self._on_drop_callback: Optional[Callable] = None
        
        # 初始化UI
        self._init_ui()
        
        # 启用拖拽
        self.setAcceptDrops(True)
    
    def _init_ui(self):
        """初始化UI"""
        # 设置样式
        self.setObjectName("fileDropZone")
        self.setStyleSheet("""
            QFrame#fileDropZone {
                border: 2px dashed #666666;
                border-radius: 12px;
                background-color: rgba(102, 102, 102, 0.1);
            }
            
            QFrame#fileDropZone[hovering="true"] {
                border-color: #007AFF;
                background-color: rgba(0, 122, 255, 0.1);
            }
        """)
        
        # 布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        
        # 图标
        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_icon()
        layout.addWidget(self._icon_label)
        
        # 提示文本
        self._text_label = QLabel("拖拽文件到此处")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setStyleSheet("font-size: 14px; color: #888888;")
        layout.addWidget(self._text_label)
        
        # 支持的格式提示
        self._format_label = QLabel("支持: Word, PPT, Excel, PDF, TXT, Markdown")
        self._format_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._format_label.setStyleSheet("font-size: 12px; color: #666666;")
        layout.addWidget(self._format_label)
        
        # 文件信息标签（默认隐藏）
        self._file_info_label = QLabel()
        self._file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_info_label.setVisible(False)
        layout.addWidget(self._file_info_label)
    
    def _update_icon(self, file_type: str = None):
        """更新图标"""
        # 创建简单的图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if file_type and file_type in FILE_TYPE_COLORS:
            color = QColor(FILE_TYPE_COLORS[file_type])
        else:
            color = QColor("#666666")
        
        # 绘制文件图标
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(8, 4, 48, 56, 8, 8)
        
        # 绘制折角
        painter.setBrush(color.lighter(120))
        points = [
            (40, 4),
            (56, 20),
            (40, 20)
        ]
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF
        painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
        
        painter.end()
        
        self._icon_label.setPixmap(pixmap)
    
    def _update_file_info(self, file_info: FileInfo):
        """更新文件信息显示"""
        self._current_file_info = file_info
        
        # 更新图标
        self._update_icon(file_info.file_type)
        
        # 更新文本
        self._text_label.setText(file_info.name)
        self._format_label.setText(f"{file_info.file_type} | {file_info.size_str}")
        
        # 显示文件信息
        self._file_info_label.setVisible(True)
        self._file_info_label.setText(f"路径: {file_info.path}")
    
    def _clear_file_info(self):
        """清除文件信息显示"""
        self._current_file_info = None
        
        # 重置图标
        self._update_icon()
        
        # 重置文本
        self._text_label.setText("拖拽文件到此处")
        self._format_label.setText("支持: Word, PPT, Excel, PDF, TXT, Markdown")
        
        # 隐藏文件信息
        self._file_info_label.setVisible(False)
    
    def _set_hovering(self, hovering: bool):
        """设置悬停状态"""
        self._is_hovering = hovering
        self.setProperty("hovering", hovering)
        self.style().unpolish(self)
        self.style().polish(self)
    
    @property
    def accepted_extensions(self) -> List[str]:
        """获取接受的文件扩展名"""
        return self._accepted_extensions.copy()
    
    @accepted_extensions.setter
    def accepted_extensions(self, extensions: List[str]):
        """设置接受的文件扩展名"""
        self._accepted_extensions = extensions
    
    def get_accepted_extensions(self) -> List[str]:
        """获取接受的文件扩展名"""
        return self._accepted_extensions.copy()
    
    def set_accepted_extensions(self, extensions: List[str]):
        """设置接受的文件扩展名"""
        self._accepted_extensions = extensions
    
    def get_current_file_info(self) -> Optional[FileInfo]:
        """获取当前文件信息"""
        return self._current_file_info
    
    def clear(self):
        """清除当前文件信息"""
        self._clear_file_info()
    
    def set_on_drag_enter(self, callback: Callable):
        """设置拖拽进入回调"""
        self._on_drag_enter_callback = callback
    
    def set_on_drag_leave(self, callback: Callable):
        """设置拖拽离开回调"""
        self._on_drag_leave_callback = callback
    
    def set_on_drop(self, callback: Callable):
        """设置放下回调"""
        self._on_drop_callback = callback
    
    def _is_valid_file(self, file_path: str) -> bool:
        """检查文件是否有效"""
        if not file_path:
            return False
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False
        
        # 检查是否是文件
        if not os.path.isfile(file_path):
            return False
        
        # 检查扩展名
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self._accepted_extensions
    
    def _get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """获取文件信息"""
        if not self._is_valid_file(file_path):
            return None
        
        try:
            # 获取文件名
            name = os.path.basename(file_path)
            
            # 获取文件大小
            size = os.path.getsize(file_path)
            
            # 获取扩展名
            ext = os.path.splitext(file_path)[1].lower()
            
            # 获取文件类型
            file_type_info = FILE_TYPE_MAPPING.get(ext, ("未知文件", "unknown"))
            file_type = file_type_info[0]
            
            return FileInfo(
                name=name,
                path=file_path,
                size=size,
                file_type=file_type,
                extension=ext
            )
        except Exception as e:
            print(f"获取文件信息失败: {e}")
            return None
    
    def _get_files_from_mime(self, mime_data: QMimeData) -> List[str]:
        """从MimeData获取文件列表"""
        files = []
        
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if self._is_valid_file(file_path):
                        files.append(file_path)
        
        return files
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        mime_data = event.mimeData()
        
        # 检查是否有有效文件
        files = self._get_files_from_mime(mime_data)
        
        if files:
            # 接受拖拽
            event.acceptProposedAction()
            
            # 设置悬停状态
            self._set_hovering(True)
            
            # 调用回调
            if self._on_drag_enter_callback:
                self._on_drag_enter_callback(files[0])
            
            # 发送信号
            self.file_entered.emit(files[0])
        else:
            # 拒绝拖拽
            event.ignore()
    
    def dragLeaveEvent(self, event: QDragLeaveEvent):
        """拖拽离开事件"""
        # 取消悬停状态
        self._set_hovering(False)
        
        # 调用回调
        if self._on_drag_leave_callback:
            self._on_drag_leave_callback()
        
        # 发送信号
        self.file_left.emit()
    
    def dropEvent(self, event: QDropEvent):
        """放下事件"""
        mime_data = event.mimeData()
        
        # 获取文件列表
        files = self._get_files_from_mime(mime_data)
        
        if files:
            # 接受放下
            event.acceptProposedAction()
            
            # 取消悬停状态
            self._set_hovering(False)
            
            # 处理文件
            file_infos = []
            for file_path in files:
                file_info = self._get_file_info(file_path)
                if file_info:
                    file_infos.append((file_path, file_info.to_dict()))
            
            if file_infos:
                # 更新显示（只显示第一个文件）
                first_file_info = self._get_file_info(files[0])
                if first_file_info:
                    self._update_file_info(first_file_info)
                
                # 调用回调
                if self._on_drop_callback:
                    self._on_drop_callback(file_infos)
                
                # 发送信号
                if len(file_infos) == 1:
                    self.file_dropped.emit(file_infos[0][0], file_infos[0][1])
                else:
                    self.files_dropped.emit(file_infos)
        else:
            # 拒绝放下
            event.ignore()
            
            # 取消悬停状态
            self._set_hovering(False)