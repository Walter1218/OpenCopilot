"""
批量处理界面组件
支持文件列表管理、批量处理控制、结果汇总
"""
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QComboBox, QCheckBox,
    QSpinBox, QSplitter, QWidget, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QIcon, QAction


class FileStatus(Enum):
    """文件处理状态"""
    PENDING = "pending"        # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    SKIPPED = "skipped"        # 已跳过


class BatchStatus(Enum):
    """批量处理状态"""
    IDLE = "idle"              # 空闲
    RUNNING = "running"        # 运行中
    PAUSED = "paused"          # 已暂停
    COMPLETED = "completed"    # 已完成
    CANCELLED = "cancelled"    # 已取消


@dataclass
class FileItem:
    """文件项数据"""
    file_path: str
    file_name: str
    file_size: int
    file_type: str = ""
    status: FileStatus = FileStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.file_type:
            ext = os.path.splitext(self.file_name)[1].lower()
            self.file_type = ext if ext else "unknown"
    
    def get_duration(self) -> Optional[float]:
        """获取处理时长（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def get_size_str(self) -> str:
        """获取文件大小字符串"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


class BatchDialog(QDialog):
    """批量处理对话框"""
    
    # 信号
    file_added = pyqtSignal(str)  # 文件添加信号
    file_removed = pyqtSignal(str)  # 文件移除信号
    processing_started = pyqtSignal()  # 处理开始信号
    processing_finished = pyqtSignal()  # 处理完成信号
    file_status_changed = pyqtSignal(str, str)  # 文件状态改变信号
    
    def __init__(self, parent=None):
        """初始化"""
        super().__init__(parent)
        self.setWindowTitle("批量处理")
        self.setMinimumSize(800, 600)
        
        # 数据
        self.file_items: List[FileItem] = []
        self.batch_status = BatchStatus.IDLE
        self.process_callback: Optional[Callable] = None
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.btn_add_files = QPushButton("添加文件")
        self.btn_add_files.clicked.connect(self._on_add_files)
        toolbar_layout.addWidget(self.btn_add_files)
        
        self.btn_add_folder = QPushButton("添加文件夹")
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        toolbar_layout.addWidget(self.btn_add_folder)
        
        self.btn_remove_selected = QPushButton("移除选中")
        self.btn_remove_selected.clicked.connect(self._on_remove_selected)
        toolbar_layout.addWidget(self.btn_remove_selected)
        
        self.btn_clear_all = QPushButton("清空全部")
        self.btn_clear_all.clicked.connect(self._on_clear_all)
        toolbar_layout.addWidget(self.btn_clear_all)
        
        toolbar_layout.addStretch()
        
        # 处理选项
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["翻译", "润色", "文档处理", "格式转换"])
        toolbar_layout.addWidget(QLabel("处理模式:"))
        toolbar_layout.addWidget(self.combo_mode)
        
        layout.addLayout(toolbar_layout)
        
        # 文件列表
        self.table_files = QTableWidget()
        self.table_files.setColumnCount(6)
        self.table_files.setHorizontalHeaderLabels([
            "文件名", "大小", "类型", "状态", "进度", "操作"
        ])
        self.table_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_files.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_files.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table_files)
        
        # 进度区域
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("就绪")
        progress_layout.addWidget(self.lbl_status)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.lbl_total = QLabel("总计: 0")
        self.lbl_completed = QLabel("完成: 0")
        self.lbl_failed = QLabel("失败: 0")
        self.lbl_pending = QLabel("待处理: 0")
        stats_layout.addWidget(self.lbl_total)
        stats_layout.addWidget(self.lbl_completed)
        stats_layout.addWidget(self.lbl_failed)
        stats_layout.addWidget(self.lbl_pending)
        stats_layout.addStretch()
        progress_layout.addLayout(stats_layout)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("开始处理")
        self.btn_start.clicked.connect(self._on_start)
        btn_layout.addWidget(self.btn_start)
        
        self.btn_pause = QPushButton("暂停")
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_pause.setEnabled(False)
        btn_layout.addWidget(self.btn_pause)
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_cancel)
        
        btn_layout.addStretch()
        
        self.btn_export = QPushButton("导出结果")
        self.btn_export.clicked.connect(self._on_export)
        self.btn_export.setEnabled(False)
        btn_layout.addWidget(self.btn_export)
        
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
    
    def add_file(self, item: FileItem):
        """添加单个文件"""
        # 检查是否已存在
        for existing in self.file_items:
            if existing.file_path == item.file_path:
                return
        
        self.file_items.append(item)
        self._update_table()
        self._update_statistics()
        self.file_added.emit(item.file_path)
    
    def add_files(self, items: List[FileItem]):
        """添加多个文件"""
        for item in items:
            # 检查是否已存在
            exists = False
            for existing in self.file_items:
                if existing.file_path == item.file_path:
                    exists = True
                    break
            
            if not exists:
                self.file_items.append(item)
        
        self._update_table()
        self._update_statistics()
    
    def remove_file(self, file_path: str):
        """移除文件"""
        self.file_items = [item for item in self.file_items if item.file_path != file_path]
        self._update_table()
        self._update_statistics()
        self.file_removed.emit(file_path)
    
    def clear_files(self):
        """清空所有文件"""
        self.file_items.clear()
        self._update_table()
        self._update_statistics()
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        total = len(self.file_items)
        completed = sum(1 for item in self.file_items if item.status == FileStatus.COMPLETED)
        failed = sum(1 for item in self.file_items if item.status == FileStatus.FAILED)
        pending = sum(1 for item in self.file_items if item.status == FileStatus.PENDING)
        processing = sum(1 for item in self.file_items if item.status == FileStatus.PROCESSING)
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "processing": processing
        }
    
    def set_process_callback(self, callback: Callable):
        """设置处理回调函数"""
        self.process_callback = callback
    
    def _update_table(self):
        """更新表格显示"""
        self.table_files.setRowCount(len(self.file_items))
        
        for row, item in enumerate(self.file_items):
            # 文件名
            self.table_files.setItem(row, 0, QTableWidgetItem(item.file_name))
            
            # 大小
            self.table_files.setItem(row, 1, QTableWidgetItem(item.get_size_str()))
            
            # 类型
            self.table_files.setItem(row, 2, QTableWidgetItem(item.file_type))
            
            # 状态
            status_item = QTableWidgetItem(item.status.value)
            if item.status == FileStatus.COMPLETED:
                status_item.setForeground(QColor("green"))
            elif item.status == FileStatus.FAILED:
                status_item.setForeground(QColor("red"))
            elif item.status == FileStatus.PROCESSING:
                status_item.setForeground(QColor("blue"))
            self.table_files.setItem(row, 3, status_item)
            
            # 进度
            progress_item = QTableWidgetItem(f"{item.progress:.1f}%")
            self.table_files.setItem(row, 4, progress_item)
            
            # 操作
            btn_remove = QPushButton("移除")
            btn_remove.clicked.connect(lambda checked, path=item.file_path: self.remove_file(path))
            self.table_files.setCellWidget(row, 5, btn_remove)
    
    def _update_statistics(self):
        """更新统计信息"""
        stats = self.get_statistics()
        self.lbl_total.setText(f"总计: {stats['total']}")
        self.lbl_completed.setText(f"完成: {stats['completed']}")
        self.lbl_failed.setText(f"失败: {stats['failed']}")
        self.lbl_pending.setText(f"待处理: {stats['pending']}")
        
        # 更新进度条
        if stats['total'] > 0:
            progress = (stats['completed'] + stats['failed']) / stats['total'] * 100
            self.progress_bar.setValue(int(progress))
        else:
            self.progress_bar.setValue(0)
    
    def _on_add_files(self):
        """添加文件按钮点击"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "", 
            "所有文件 (*);;文本文件 (*.txt);;Word文档 (*.docx);;PDF文件 (*.pdf)"
        )
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            item = FileItem(file_path=file_path, file_name=file_name, file_size=file_size)
            self.add_file(item)
    
    def _on_add_folder(self):
        """添加文件夹按钮点击"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            for root, dirs, files in os.walk(folder):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_size = os.path.getsize(file_path)
                    item = FileItem(file_path=file_path, file_name=file_name, file_size=file_size)
                    self.add_file(item)
    
    def _on_remove_selected(self):
        """移除选中文件"""
        selected_rows = set()
        for item in self.table_files.selectedItems():
            selected_rows.add(item.row())
        
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.file_items):
                self.remove_file(self.file_items[row].file_path)
    
    def _on_clear_all(self):
        """清空所有文件"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有文件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_files()
    
    def _on_start(self):
        """开始处理"""
        if not self.file_items:
            QMessageBox.warning(self, "警告", "没有要处理的文件")
            return
        
        self.batch_status = BatchStatus.RUNNING
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        
        self.processing_started.emit()
        self._process_next_file()
    
    def _on_pause(self):
        """暂停处理"""
        if self.batch_status == BatchStatus.RUNNING:
            self.batch_status = BatchStatus.PAUSED
            self.btn_pause.setText("继续")
            self.lbl_status.setText("已暂停")
        elif self.batch_status == BatchStatus.PAUSED:
            self.batch_status = BatchStatus.RUNNING
            self.btn_pause.setText("暂停")
            self._process_next_file()
    
    def _on_cancel(self):
        """取消处理"""
        reply = QMessageBox.question(
            self, "确认", "确定要取消处理吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.batch_status = BatchStatus.CANCELLED
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.lbl_status.setText("已取消")
    
    def _on_export(self):
        """导出结果"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出结果", "", "JSON文件 (*.json);;CSV文件 (*.csv)"
        )
        
        if file_path:
            self._export_results(file_path)
    
    def _process_next_file(self):
        """处理下一个文件"""
        if self.batch_status != BatchStatus.RUNNING:
            return
        
        # 查找下一个待处理的文件
        next_item = None
        for item in self.file_items:
            if item.status == FileStatus.PENDING:
                next_item = item
                break
        
        if next_item is None:
            # 所有文件处理完成
            self._on_processing_finished()
            return
        
        # 开始处理
        next_item.status = FileStatus.PROCESSING
        next_item.start_time = datetime.now()
        self._update_table()
        self.file_status_changed.emit(next_item.file_path, FileStatus.PROCESSING.value)
        
        # 调用处理回调
        if self.process_callback:
            try:
                result = self.process_callback(next_item)
                next_item.status = FileStatus.COMPLETED
                next_item.progress = 100.0
            except Exception as e:
                next_item.status = FileStatus.FAILED
                next_item.error_message = str(e)
        else:
            # 模拟处理
            next_item.status = FileStatus.COMPLETED
            next_item.progress = 100.0
        
        next_item.end_time = datetime.now()
        self._update_table()
        self._update_statistics()
        self.file_status_changed.emit(next_item.file_path, next_item.status.value)
        
        # 继续处理下一个
        QTimer.singleShot(100, self._process_next_file)
    
    def _on_processing_finished(self):
        """处理完成"""
        self.batch_status = BatchStatus.COMPLETED
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_export.setEnabled(True)
        
        stats = self.get_statistics()
        self.lbl_status.setText(f"处理完成: {stats['completed']}成功, {stats['failed']}失败")
        
        self.processing_finished.emit()
    
    def _export_results(self, file_path: str):
        """导出处理结果"""
        import json
        
        results = []
        for item in self.file_items:
            results.append({
                "file_name": item.file_name,
                "file_path": item.file_path,
                "file_size": item.file_size,
                "file_type": item.file_type,
                "status": item.status.value,
                "progress": item.progress,
                "error_message": item.error_message,
                "duration": item.get_duration()
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        QMessageBox.information(self, "成功", f"结果已导出到: {file_path}")
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        action_remove = menu.addAction("移除")
        action_remove.triggered.connect(self._on_remove_selected)
        
        action_retry = menu.addAction("重试失败项")
        action_retry.triggered.connect(self._on_retry_failed)
        
        menu.exec(self.table_files.viewport().mapToGlobal(position))
    
    def _on_retry_failed(self):
        """重试失败的文件"""
        for item in self.file_items:
            if item.status == FileStatus.FAILED:
                item.status = FileStatus.PENDING
                item.error_message = None
                item.progress = 0.0
        
        self._update_table()
        self._update_statistics()
