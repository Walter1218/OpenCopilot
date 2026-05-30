"""
PPT 人机共创主对话框

功能：
- 三面板布局：原文面板 + 编辑大纲面板 + PPT预览面板
- AI 对话框：底部交互式修改
- 双向联动：原文↔大纲↔预览
- 最终导出 PPT
"""

import os
import json
import subprocess
import tempfile
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QMessageBox, QFileDialog, QWidget, QSizePolicy, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QShortcut

from .source_panel import SourcePanel
from .outline_panel import OutlinePanel
from .preview_panel import PreviewPanel, FullscreenPreviewDialog
from .ai_chat_widget import AICopilotChatWidget
from .source_matcher import SourceMatcher, TextRange

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ppt_generator import generate_ppt_from_json, extract_json_from_text


class CoCreationDialog(QDialog):
    """PPT 人机共创主对话框"""
    
    def __init__(
        self,
        original_text: str,
        json_data: list,
        agent_url: str = None,
        parent=None
    ):
        super().__init__(parent)
        
        # 数据
        self.original_text = original_text
        self.json_data = json_data if isinstance(json_data, list) else json_data.get('slides', [])
        self.agent_url = agent_url
        self.output_path = None
        
        # 原文匹配器
        self.source_matcher = SourceMatcher()
        self.source_matcher.build_mappings(original_text, self.json_data)
        
        # 初始化 UI
        self._init_ui()
        
        # 连接信号
        self._connect_signals()
        
        # 初始加载
        self._load_initial_data()
    
    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("PPT 人机共创工作台")
        
        # 基于屏幕可用区域计算窗口大小（避开 macOS Dock 栏和菜单栏）
        screen = QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            # 使用可用区域的 90%，但不超过最大限制
            width = min(int(available.width() * 0.9), 1800)
            height = min(int(available.height() * 0.9), 1100)
            # 确保最小尺寸
            width = max(width, 1200)
            height = max(height, 700)
            # 居中显示
            x = available.x() + (available.width() - width) // 2
            y = available.y() + (available.height() - height) // 2
            self.setGeometry(x, y, width, height)
        else:
            # 降级方案
            self.setMinimumSize(1200, 700)
            self.resize(1400, 900)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QSplitter::handle {
                background-color: #3c3c3c;
                width: 2px;
                height: 2px;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # 顶部工具栏
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 三面板分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：原文面板
        self.source_panel = SourcePanel()
        self.source_panel.setMinimumWidth(300)
        self.splitter.addWidget(self.source_panel)
        
        # 中间：编辑大纲面板
        self.outline_panel = OutlinePanel()
        self.outline_panel.setMinimumWidth(350)
        self.splitter.addWidget(self.outline_panel)
        
        # 右侧：预览面板
        self.preview_panel = PreviewPanel()
        self.preview_panel.setMinimumWidth(400)
        self.splitter.addWidget(self.preview_panel)
        
        # 设置分割比例
        self.splitter.setSizes([400, 500, 500])
        
        main_layout.addWidget(self.splitter, 1)
        
        # 底部：AI 对话框
        self.ai_chat = AICopilotChatWidget(self.agent_url)
        self.ai_chat.setMaximumHeight(250)
        main_layout.addWidget(self.ai_chat)
        
        # 底部按钮栏
        button_bar = self._create_button_bar()
        main_layout.addWidget(button_bar)
        
        # 快捷键
        self._setup_shortcuts()
    
    def _create_toolbar(self) -> QWidget:
        """创建顶部工具栏"""
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("🎨 PPT 人机共创工作台")
        title.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # 统计信息
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.stats_label)
        
        # 帮助按钮
        help_btn = QPushButton("❓ 帮助")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        help_btn.clicked.connect(self._show_help)
        layout.addWidget(help_btn)
        
        return toolbar
    
    def _create_button_bar(self) -> QWidget:
        """创建底部按钮栏"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)
        
        layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("✖ 取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        # 预览按钮
        preview_btn = QPushButton("👁️ 全屏预览")
        preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        preview_btn.clicked.connect(self._on_fullscreen_preview)
        layout.addWidget(preview_btn)
        
        # 导出按钮
        export_btn = QPushButton("💾 导出 PPT")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        export_btn.clicked.connect(self._on_export)
        layout.addWidget(export_btn)
        
        return bar
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+S: 导出
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(self._on_export)
        
        # Escape: 取消
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self.reject)
        
        # F5: 全屏预览
        shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        shortcut_f5.activated.connect(self._on_fullscreen_preview)
    
    def _connect_signals(self):
        """连接信号"""
        # 原文面板 -> 大纲面板
        self.source_panel.text_selected.connect(self._on_source_text_selected)
        self.source_panel.new_slide_requested.connect(self._on_create_slide_from_source)
        self.source_panel.position_clicked.connect(self._on_source_position_clicked)
        
        # 大纲面板 -> 预览面板
        self.outline_panel.slide_selected.connect(self._on_slide_selected)
        self.outline_panel.slide_changed.connect(self._on_slide_changed)
        self.outline_panel.slide_added.connect(self._on_slide_added)
        self.outline_panel.slide_deleted.connect(self._on_slide_deleted)
        
        # 预览面板 -> 大纲面板
        self.preview_panel.slide_changed.connect(self._on_preview_slide_changed)
        
        # AI 对话框 -> 大纲面板
        self.ai_chat.slides_updated.connect(self._on_ai_slides_updated)
    
    def _load_initial_data(self):
        """加载初始数据"""
        # 设置原文
        self.source_panel.set_original_text(self.original_text)
        self.source_panel.set_source_matcher(self.source_matcher)
        
        # 设置大纲
        self.outline_panel.set_slides_data(self.json_data)
        
        # 设置预览
        self.preview_panel.set_slides_data(self.json_data)
        
        # 设置 AI 对话框
        self.ai_chat.set_slides_data(self.json_data)
        
        # 更新统计
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        total_slides = len(self.json_data)
        total_items = sum(len(s.get('items', [])) for s in self.json_data)
        extracted_pct = 0
        
        total_len = len(self.original_text)
        if total_len > 0:
            extracted_len = sum(r.length for r in self.source_matcher.get_extracted_ranges())
            extracted_pct = int(extracted_len / total_len * 100)
        
        self.stats_label.setText(
            f"幻灯片: {total_slides} | 要点: {total_items} | 原文提炼: {extracted_pct}%"
        )
    
    def _on_source_text_selected(self, text: str, start: int, end: int):
        """原文文本被选中"""
        # 添加到当前幻灯片
        current_index = self.outline_panel.current_index
        if current_index >= 0 and current_index < len(self.json_data):
            slide = self.json_data[current_index]
            if 'items' not in slide:
                slide['items'] = []
            
            new_item = {
                "id": f"item_{len(slide['items'])}",
                "text": text,
                "level": 0,
                "content_type": "text",
                "source_range": {"start": start, "end": end}
            }
            slide['items'].append(new_item)
            
            # 刷新大纲
            self.outline_panel._refresh_items()
            
            # 更新预览
            self.preview_panel.set_slides_data(self.json_data)
            
            # 更新统计
            self._update_stats()
            
            QMessageBox.information(
                self, "已添加",
                f"已将选中文本添加到第 {current_index + 1} 页幻灯片"
            )
    
    def _on_create_slide_from_source(self, text: str, start: int, end: int):
        """基于选中文本创建新幻灯片"""
        import uuid
        
        new_slide = {
            "id": str(uuid.uuid4())[:8],
            "type": "content",
            "layout": "text_only",
            "title": text[:30] + "..." if len(text) > 30 else text,
            "subtitle": "",
            "items": [{
                "id": f"item_0",
                "text": text,
                "level": 0,
                "content_type": "text",
                "source_range": {"start": start, "end": end}
            }]
        }
        
        # 插入到当前位置后面
        current_index = self.outline_panel.current_index
        insert_pos = current_index + 1 if current_index >= 0 else len(self.json_data)
        self.json_data.insert(insert_pos, new_slide)
        
        # 刷新大纲和预览
        self.outline_panel.set_slides_data(self.json_data)
        self.outline_panel.slide_list.setCurrentRow(insert_pos)
        self.preview_panel.set_slides_data(self.json_data)
        self._update_stats()
        
        QMessageBox.information(
            self, "已创建",
            f"已创建新幻灯片（第 {insert_pos + 1} 页）"
        )
    
    def _on_source_position_clicked(self, pos: int):
        """原文位置被点击"""
        # 双向联动：找到对应的幻灯片
        result = self.source_matcher.find_slide_for_position(pos)
        if result:
            slide_idx, item_idx = result
            self.outline_panel.slide_list.setCurrentRow(slide_idx)
            self.preview_panel.set_current_slide(slide_idx)
    
    def _on_slide_selected(self, index: int):
        """幻灯片被选中"""
        self.preview_panel.set_current_slide(index)
        self.ai_chat.set_slides_data(self.json_data, index)
        
        # 双向联动：高亮原文
        self.source_panel.highlight_slide_content(index)
    
    def _on_slide_changed(self, index: int, slide_data: dict):
        """幻灯片内容变化"""
        self.json_data[index] = slide_data
        self.preview_panel.set_slides_data(self.json_data)
        self._update_stats()
    
    def _on_slide_added(self, index: int, slide_data: dict):
        """新增幻灯片"""
        self.json_data.insert(index, slide_data)
        self.preview_panel.set_slides_data(self.json_data)
        self._update_stats()
    
    def _on_slide_deleted(self, index: int):
        """删除幻灯片"""
        if 0 <= index < len(self.json_data):
            self.json_data.pop(index)
            self.preview_panel.set_slides_data(self.json_data)
            self._update_stats()
    
    def _on_preview_slide_changed(self, index: int):
        """预览面板幻灯片变化"""
        self.outline_panel.slide_list.setCurrentRow(index)
    
    def _on_ai_slides_updated(self, new_slides: list):
        """AI 更新了幻灯片数据"""
        self.json_data = new_slides
        self.outline_panel.set_slides_data(self.json_data)
        self.preview_panel.set_slides_data(self.json_data)
        self._update_stats()
    
    def _on_fullscreen_preview(self):
        """全屏预览"""
        if not self.json_data:
            QMessageBox.warning(self, "提示", "没有幻灯片数据")
            return
        
        # 获取当前预览的幻灯片索引
        current_index = self.preview_panel.current_index
        
        dialog = FullscreenPreviewDialog(
            self.json_data, 
            current_index, 
            self
        )
        dialog.exec()
        
        # 全屏结束后同步位置
        new_index = dialog.get_current_index()
        if new_index != current_index:
            self.preview_panel.set_current_slide(new_index)
            self.outline_panel.slide_list.setCurrentRow(new_index)
    
    def _on_export(self):
        """导出 PPT"""
        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 PPT",
            os.path.expanduser("~/Desktop/generated_presentation.pptx"),
            "PowerPoint Files (*.pptx)"
        )
        
        if not save_path:
            return
        
        try:
            # 生成 PPT
            generate_ppt_from_json(self.json_data, save_path)
            
            self.output_path = save_path
            
            # 询问是否打开
            reply = QMessageBox.question(
                self, "导出成功",
                f"PPT 已成功导出至：\n{save_path}\n\n是否立即打开？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                subprocess.run(["open", save_path])
            
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self, "导出失败",
                f"生成 PPT 时发生错误：\n{str(e)}"
            )
    
    def _show_help(self):
        """显示帮助"""
        help_text = """🎨 PPT 人机共创工作台 使用指南

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 原文面板（左侧）
• 蓝色高亮：已被提炼到幻灯片的内容
• 橙色高亮：用户选中的内容
• 🎯 选中模式：开启后可拖选文本加入幻灯片

📋 编辑大纲面板（中间）
• 幻灯片导航：点击切换当前幻灯片
• 编辑表单：修改标题、副标题、版式
• 要点编辑：添加、删除、调整内容类型

👁️ PPT 预览面板（右侧）
• 实时预览：与最终导出完全一致
• 导航按钮：上一页/下一页
• 全屏预览：F5 快捷键

🤖 AI 助手（底部）
• 自然语言指令：输入修改需求
• 自动更新：AI 修改后自动刷新所有面板

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⌨️ 快捷键
• Ctrl+S: 导出 PPT
• F5: 全屏预览
• Escape: 取消

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 示例指令
• "把第2页的标题改为'核心优势'"
• "在第3页添加一个流程图"
• "把第1页改为图文混排"
• "在最后插入一页总结幻灯片"
"""
        QMessageBox.information(self, "使用指南", help_text)
    
    def get_output_path(self) -> str:
        """获取导出路径"""
        return self.output_path
    
    def get_final_slides(self) -> list:
        """获取最终幻灯片数据"""
        return self.json_data
