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

from ppt_generator import generate_ppt_from_json, extract_json_from_text


class CoCreationDialog(QDialog):
    """PPT 人机共创主对话框"""
    
    # 主题定义
    THEMES = {
        "dark": {
            "name": "深色",
            "dialog_bg": "#1e1e1e",
            "dialog_color": "#d4d4d4",
            "splitter_handle": "#3c3c3c",
            "toolbar_bg": "#2d2d2d",
            "button_bg": "#3c3c3c",
            "button_hover": "#4c4c4c",
            "button_pressed": "#5c5c5c",
            "accent_color": "#007bff",
            "border_color": "#555555"
        },
        "light": {
            "name": "浅色",
            "dialog_bg": "#f5f5f5",
            "dialog_color": "#333333",
            "splitter_handle": "#cccccc",
            "toolbar_bg": "#ffffff",
            "button_bg": "#e0e0e0",
            "button_hover": "#d0d0d0",
            "button_pressed": "#c0c0c0",
            "accent_color": "#0066cc",
            "border_color": "#cccccc"
        },
        "blue": {
            "name": "蓝色",
            "dialog_bg": "#0d1b2a",
            "dialog_color": "#e0e0e0",
            "splitter_handle": "#1b3a5c",
            "toolbar_bg": "#1b2838",
            "button_bg": "#2a4a6b",
            "button_hover": "#3a5a7b",
            "button_pressed": "#4a6a8b",
            "accent_color": "#4da6ff",
            "border_color": "#3a5a7b"
        },
        "green": {
            "name": "绿色",
            "dialog_bg": "#0a1f0a",
            "dialog_color": "#d4d4d4",
            "splitter_handle": "#1a3a1a",
            "toolbar_bg": "#1a2a1a",
            "button_bg": "#2a4a2a",
            "button_hover": "#3a5a3a",
            "button_pressed": "#4a6a4a",
            "accent_color": "#4dff4d",
            "border_color": "#3a5a3a"
        }
    }
    
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
        # agent_url 参数保留用于向后兼容，不再使用（统一走 Pipeline）
        self.output_path = None
        
        # 主题
        self.current_theme = "dark"
        
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
        
        # 设置样式（使用当前主题）
        self._apply_theme()
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # 顶部工具栏
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 三面板分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：原文面板（占30%）
        self.source_panel = SourcePanel()
        self.source_panel.setMinimumWidth(250)
        self.splitter.addWidget(self.source_panel)
        
        # 中间：编辑大纲面板（占30%）
        self.outline_panel = OutlinePanel()
        self.outline_panel.setMinimumWidth(300)
        self.splitter.addWidget(self.outline_panel)
        
        # 右侧：预览面板（占40%，优先显示）
        self.preview_panel = PreviewPanel()
        self.preview_panel.setMinimumWidth(400)
        self.splitter.addWidget(self.preview_panel)
        
        # 设置分割比例：原文30% : 大纲30% : 预览40%
        self.splitter.setSizes([300, 300, 400])
        
        main_layout.addWidget(self.splitter, 1)
        
        # 底部：AI 对话框
        self.ai_chat = AICopilotChatWidget()
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
        # === 文件操作 ===
        # Ctrl+S: 导出
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(self._on_export)
        
        # Ctrl+Shift+S: 导出并下载
        shortcut_save_as = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        shortcut_save_as.activated.connect(self._on_export_and_download)
        
        # Escape: 取消
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self.reject)
        
        # === 预览操作 ===
        # F5: 全屏预览
        shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        shortcut_f5.activated.connect(self._on_fullscreen_preview)
        
        # F11: 切换全屏（替代F5）
        shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        shortcut_f11.activated.connect(self._on_fullscreen_preview)
        
        # === 导航操作 ===
        # Ctrl+Left: 上一页
        shortcut_prev = QShortcut(QKeySequence("Ctrl+Left"), self)
        shortcut_prev.activated.connect(self._on_prev_slide)
        
        # Ctrl+Right: 下一页
        shortcut_next = QShortcut(QKeySequence("Ctrl+Right"), self)
        shortcut_next.activated.connect(self._on_next_slide)
        
        # Ctrl+Home: 第一页
        shortcut_home = QShortcut(QKeySequence("Ctrl+Home"), self)
        shortcut_home.activated.connect(self._on_first_slide)
        
        # Ctrl+End: 最后一页
        shortcut_end = QShortcut(QKeySequence("Ctrl+End"), self)
        shortcut_end.activated.connect(self._on_last_slide)
        
        # === 编辑操作 ===
        # Ctrl+Z: 撤销（大纲面板）
        shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        shortcut_undo.activated.connect(self._on_undo)
        
        # Ctrl+Shift+Z: 重做（大纲面板）
        shortcut_redo = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        shortcut_redo.activated.connect(self._on_redo)
        
        # Delete: 删除选中幻灯片
        shortcut_delete = QShortcut(QKeySequence("Delete"), self)
        shortcut_delete.activated.connect(self._on_delete_slide)
        
        # Ctrl+D: 复制当前幻灯片
        shortcut_duplicate = QShortcut(QKeySequence("Ctrl+D"), self)
        shortcut_duplicate.activated.connect(self._on_duplicate_slide)
        
        # Ctrl+Shift+N: 添加新幻灯片
        shortcut_add = QShortcut(QKeySequence("Ctrl+Shift+N"), self)
        shortcut_add.activated.connect(self._on_add_slide)
        
        # === AI 操作 ===
        # Ctrl+Enter: 发送AI消息
        shortcut_send = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_send.activated.connect(self._on_send_ai_message)
        
        # Ctrl+1: 快捷指令 - 换个标题
        shortcut_cmd1 = QShortcut(QKeySequence("Ctrl+1"), self)
        shortcut_cmd1.activated.connect(lambda: self._execute_shortcut("换个标题"))
        
        # Ctrl+2: 快捷指令 - 添加要点
        shortcut_cmd2 = QShortcut(QKeySequence("Ctrl+2"), self)
        shortcut_cmd2.activated.connect(lambda: self._execute_shortcut("添加要点"))
        
        # Ctrl+3: 快捷指令 - 换版式
        shortcut_cmd3 = QShortcut(QKeySequence("Ctrl+3"), self)
        shortcut_cmd3.activated.connect(lambda: self._execute_shortcut("换版式"))
        
        # Ctrl+4: 快捷指令 - 精简内容
        shortcut_cmd4 = QShortcut(QKeySequence("Ctrl+4"), self)
        shortcut_cmd4.activated.connect(lambda: self._execute_shortcut("精简内容"))
        
        # === 视图操作 ===
        # Ctrl++: 放大预览
        shortcut_zoom_in = QShortcut(QKeySequence("Ctrl++"), self)
        shortcut_zoom_in.activated.connect(self._on_zoom_in)
        
        # Ctrl+-: 缩小预览
        shortcut_zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        shortcut_zoom_out.activated.connect(self._on_zoom_out)
        
        # Ctrl+0: 重置缩放
        shortcut_zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        shortcut_zoom_reset.activated.connect(self._on_zoom_reset)
        
        # === 面板切换 ===
        # Ctrl+1: 切换到原文面板
        shortcut_panel1 = QShortcut(QKeySequence("Alt+1"), self)
        shortcut_panel1.activated.connect(lambda: self._focus_panel("source"))
        
        # Ctrl+2: 切换到大纲面板
        shortcut_panel2 = QShortcut(QKeySequence("Alt+2"), self)
        shortcut_panel2.activated.connect(lambda: self._focus_panel("outline"))
        
        # Ctrl+3: 切换到预览面板
        shortcut_panel3 = QShortcut(QKeySequence("Alt+3"), self)
        shortcut_panel3.activated.connect(lambda: self._focus_panel("preview"))
        
        # Ctrl+4: 切换到AI对话
        shortcut_panel4 = QShortcut(QKeySequence("Alt+4"), self)
        shortcut_panel4.activated.connect(lambda: self._focus_panel("ai"))
        
        # === 主题切换 ===
        # Ctrl+T: 切换主题
        shortcut_theme = QShortcut(QKeySequence("Ctrl+T"), self)
        shortcut_theme.activated.connect(self._on_toggle_theme)
        
        # === 帮助 ===
        # F1: 显示快捷键帮助
        shortcut_help = QShortcut(QKeySequence("F1"), self)
        shortcut_help.activated.connect(self._on_show_shortcuts_help)
    
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
            
            # 更新预览数据（set_slides_data 保留当前索引）
            self.preview_panel.set_slides_data(self.json_data)
            self.preview_panel.set_current_slide(current_index)
            
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
        
        # 刷新大纲和预览，跳转到新创建的幻灯片
        self.outline_panel.set_slides_data(self.json_data)
        self.outline_panel.slide_list.setCurrentRow(insert_pos)
        self.preview_panel.set_slides_data(self.json_data)
        self.preview_panel.set_current_slide(insert_pos)
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
        # 更新预览数据但保持当前页不跳转
        self.preview_panel.set_slides_data(self.json_data)
        self.preview_panel.set_current_slide(index)
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
            # 删除后导航到最近的合法页
            new_index = min(index, len(self.json_data) - 1)
            if new_index >= 0:
                self.preview_panel.set_current_slide(new_index)
                self.outline_panel.slide_list.setCurrentRow(new_index)
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

⌨️ 快捷键（按 F1 查看完整列表）

📁 文件：Ctrl+S 导出 | Ctrl+Shift+S 导出并下载
🔄 预览：F5/F11 全屏 | Escape 退出
📄 导航：Ctrl+← 上一页 | Ctrl+→ 下一页
✏️ 编辑：Ctrl+D 复制 | Delete 删除 | Ctrl+Shift+N 新建
🤖 AI：Ctrl+Enter 发送 | Ctrl+1~4 快捷指令
🔍 视图：Ctrl++ 放大 | Ctrl+- 缩小 | Ctrl+0 重置
📋 面板：Alt+1~4 切换面板
🎨 主题：Ctrl+T 切换主题

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
    
    # === 快捷键对应的方法 ===
    
    def _on_export_and_download(self):
        """导出并下载"""
        self._on_export()
    
    def _on_prev_slide(self):
        """上一页"""
        current = self.preview_panel.current_index
        if current > 0:
            self.preview_panel.set_current_slide(current - 1)
            self.outline_panel.slide_list.setCurrentRow(current - 1)
    
    def _on_next_slide(self):
        """下一页"""
        current = self.preview_panel.current_index
        if current < len(self.json_data) - 1:
            self.preview_panel.set_current_slide(current + 1)
            self.outline_panel.slide_list.setCurrentRow(current + 1)
    
    def _on_first_slide(self):
        """第一页"""
        if self.json_data:
            self.preview_panel.set_current_slide(0)
            self.outline_panel.slide_list.setCurrentRow(0)
    
    def _on_last_slide(self):
        """最后一页"""
        if self.json_data:
            last_index = len(self.json_data) - 1
            self.preview_panel.set_current_slide(last_index)
            self.outline_panel.slide_list.setCurrentRow(last_index)
    
    def _on_undo(self):
        """撤销"""
        # NOTE(NYI): 实现撤销功能 — 需深度集成 Qt UndoStack/QGraphicsView
        pass
    
    def _on_redo(self):
        """重做"""
        # NOTE(NYI): 实现重做功能 — 需深度集成 Qt UndoStack/QGraphicsView
        pass
    
    def _on_delete_slide(self):
        """删除选中幻灯片"""
        current = self.outline_panel.current_index
        if 0 <= current < len(self.json_data):
            self.outline_panel._on_delete_slide()
    
    def _on_duplicate_slide(self):
        """复制当前幻灯片"""
        current = self.outline_panel.current_index
        if 0 <= current < len(self.json_data):
            import copy
            new_slide = copy.deepcopy(self.json_data[current])
            new_slide['title'] = f"{new_slide.get('title', '')} (副本)"
            self.json_data.insert(current + 1, new_slide)
            self.outline_panel.set_slides_data(self.json_data)
            self.outline_panel.slide_list.setCurrentRow(current + 1)
            self.preview_panel.set_slides_data(self.json_data)
            self.preview_panel.set_current_slide(current + 1)
            self._update_stats()
    
    def _on_add_slide(self):
        """添加新幻灯片"""
        self.outline_panel._on_add_slide()
    
    def _on_send_ai_message(self):
        """发送AI消息"""
        self.ai_chat._on_send()
    
    def _execute_shortcut(self, command: str):
        """执行快捷指令"""
        self.ai_chat._execute_shortcut(command)
    
    def _on_zoom_in(self):
        """放大预览"""
        # NOTE(NYI): 实现缩放功能 — 需深度集成 Qt UndoStack/QGraphicsView
        pass
    
    def _on_zoom_out(self):
        """缩小预览"""
        # NOTE(NYI): 实现缩放功能 — 需深度集成 Qt UndoStack/QGraphicsView
        pass
    
    def _on_zoom_reset(self):
        """重置缩放"""
        # NOTE(NYI): 实现缩放功能 — 需深度集成 Qt UndoStack/QGraphicsView
        pass
    
    def _focus_panel(self, panel_name: str):
        """聚焦到指定面板"""
        if panel_name == "source":
            self.source_panel.setFocus()
        elif panel_name == "outline":
            self.outline_panel.setFocus()
        elif panel_name == "preview":
            self.preview_panel.setFocus()
        elif panel_name == "ai":
            self.ai_chat.input_edit.setFocus()
    
    def _on_toggle_theme(self):
        """切换主题"""
        themes = list(self.THEMES.keys())
        current_index = themes.index(self.current_theme)
        next_index = (current_index + 1) % len(themes)
        self.current_theme = themes[next_index]
        self._apply_theme()
        
        # 显示主题切换提示
        theme_name = self.THEMES[self.current_theme]["name"]
        QMessageBox.information(self, "主题切换", f"已切换到「{theme_name}」主题")
    
    def _apply_theme(self):
        """应用当前主题"""
        theme = self.THEMES[self.current_theme]
        
        # 主对话框样式
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['dialog_bg']};
                color: {theme['dialog_color']};
            }}
            QSplitter::handle {{
                background-color: {theme['splitter_handle']};
                width: 2px;
                height: 2px;
            }}
            QToolTip {{
                background-color: {theme['toolbar_bg']};
                color: {theme['dialog_color']};
                border: 1px solid {theme['border_color']};
                padding: 4px;
            }}
        """)
        
        # 更新子面板样式（如果支持主题）
        if hasattr(self, 'source_panel') and hasattr(self.source_panel, 'apply_theme'):
            self.source_panel.apply_theme(theme)
        if hasattr(self, 'outline_panel') and hasattr(self.outline_panel, 'apply_theme'):
            self.outline_panel.apply_theme(theme)
        if hasattr(self, 'preview_panel') and hasattr(self.preview_panel, 'apply_theme'):
            self.preview_panel.apply_theme(theme)
        if hasattr(self, 'ai_chat') and hasattr(self.ai_chat, 'apply_theme'):
            self.ai_chat.apply_theme(theme)
    
    def _on_show_shortcuts_help(self):
        """显示快捷键帮助"""
        help_text = """⌨️ 快捷键列表

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 文件操作
• Ctrl+S: 导出 PPT
• Ctrl+Shift+S: 导出并下载

🔄 预览操作
• F5 / F11: 全屏预览
• Escape: 退出全屏/取消

📄 导航操作
• Ctrl+←: 上一页
• Ctrl+→: 下一页
• Ctrl+Home: 第一页
• Ctrl+End: 最后一页

✏️ 编辑操作
• Ctrl+Z: 撤销
• Ctrl+Shift+Z: 重做
• Delete: 删除选中幻灯片
• Ctrl+D: 复制当前幻灯片
• Ctrl+Shift+N: 添加新幻灯片

🤖 AI 操作
• Ctrl+Enter: 发送AI消息
• Ctrl+1: 换个标题
• Ctrl+2: 添加要点
• Ctrl+3: 换版式
• Ctrl+4: 精简内容

🔍 视图操作
• Ctrl++: 放大预览
• Ctrl+-: 缩小预览
• Ctrl+0: 重置缩放

📋 面板切换
• Alt+1: 原文面板
• Alt+2: 大纲面板
• Alt+3: 预览面板
• Alt+4: AI对话

🎨 主题
• Ctrl+T: 切换主题

❓ 帮助
• F1: 显示此帮助

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        QMessageBox.information(self, "快捷键帮助", help_text)
