"""
技能搜索对话框组件
支持在对话中搜索和调用技能，参考 WorkBuddy 设计
"""

import asyncio
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFrame, QListWidget, QListWidgetItem, QTabWidget,
    QWidget, QTextEdit, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QKeySequence, QIcon, QShortcut

# 导入 Skill 架构
import sys
import os
from opencopilot.capabilities.skill import SkillRegistry, SkillContext, IntentRouter


class SkillSearchWorker(QObject):
    """技能搜索工作线程"""
    
    results_ready = pyqtSignal(list)  # 搜索结果
    
    def __init__(self, registry: SkillRegistry):
        super().__init__()
        self.registry = registry
        self.router = IntentRouter(registry)
    
    def search(self, query: str, context_type: str = "text"):
        """搜索技能"""
        try:
            results = []
            
            all_metadata = self.registry.get_all_metadata()
            
            for skill_name, metadata in all_metadata.items():
                score = self._calculate_score(query, metadata, context_type)
                if score > 0:
                    results.append((skill_name, metadata, score))
            
            # 按分数排序
            results.sort(key=lambda x: x[2], reverse=True)
            
            self.results_ready.emit(results[:20])  # 最多返回20个结果
            
        except Exception as e:
            print(f"搜索失败: {e}")
            self.results_ready.emit([])
    
    def _calculate_score(self, query: str, metadata, context_type: str) -> int:
        """计算匹配分数"""
        score = 0
        query_lower = query.lower()
        
        # 名称匹配
        if query_lower in metadata.display_name.lower():
            score += 20
        
        # 类别匹配
        if query_lower in metadata.category.lower():
            score += 10
        
        # 标签匹配
        for tag in metadata.tags:
            if query_lower in tag.lower():
                score += 5
        
        # 意图匹配
        for intent in metadata.intents:
            if query_lower in intent.lower():
                score += 3
        
        # 描述匹配
        if query_lower in metadata.description.lower():
            score += 2
        
        # 上下文相关性加分
        if context_type == "code" and metadata.category == "coding":
            score += 5
        elif context_type == "file" and metadata.category == "file":
            score += 5
        elif context_type == "text" and metadata.category in ["knowledge", "evaluation"]:
            score += 3
        
        return score


class SkillSearchDialog(QDialog):
    """技能搜索对话框
    
    特性：
    1. 快速搜索技能
    2. 支持键盘快捷键
    3. 实时搜索结果
    4. 技能详情预览
    5. 历史记录
    """
    
    # 信号定义
    skill_execute = pyqtSignal(str, dict)  # 技能名称，参数
    skill_select = pyqtSignal(str)  # 技能名称
    
    def __init__(self, registry: SkillRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.search_history: List[str] = []
        self.current_results: List[tuple] = []
        
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_search_worker()
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("技能搜索")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        title_label = QLabel("🎯 技能搜索")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 快捷键提示
        shortcut_hint = QLabel("Ctrl+K 搜索 | Esc 关闭")
        shortcut_hint.setFont(QFont("Microsoft YaHei", 9))
        shortcut_hint.setStyleSheet("color: #95a5a6;")
        title_layout.addWidget(shortcut_hint)
        
        layout.addLayout(title_layout)
        
        # 搜索框
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 输入技能名称、类别或关键词...")
        self.search_input.setFont(QFont("Microsoft YaHei", 12))
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 8px;
                padding: 10px 16px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._on_execute_skill)
        search_layout.addWidget(self.search_input)
        
        # 搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.setFont(QFont("Microsoft YaHei", 11))
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        
        # 主内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：搜索结果列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 分类标签页
        self.category_tabs = QTabWidget()
        self.category_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                border: none;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #bdc3c7;
            }
        """)
        
        # 全部结果标签页
        self.all_results_widget = QWidget()
        all_results_layout = QVBoxLayout(self.all_results_widget)
        
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #ebf5fb;
                border-left: 4px solid #3498db;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        self.results_list.currentItemChanged.connect(self._on_result_selected)
        self.results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        all_results_layout.addWidget(self.results_list)
        
        self.category_tabs.addTab(self.all_results_widget, "全部")
        
        # 各类别标签页
        self.category_lists: Dict[str, QListWidget] = {}
        
        left_layout.addWidget(self.category_tabs)
        
        # 结果统计
        self.stats_label = QLabel("输入关键词开始搜索")
        self.stats_label.setFont(QFont("Microsoft YaHei", 10))
        self.stats_label.setStyleSheet("color: #7f8c8d;")
        left_layout.addWidget(self.stats_label)
        
        content_splitter.addWidget(left_widget)
        
        # 右侧：技能详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        
        # 技能名称
        self.detail_name = QLabel("选择一个技能查看详情")
        self.detail_name.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.detail_name.setStyleSheet("color: #2c3e50;")
        self.detail_name.setWordWrap(True)
        right_layout.addWidget(self.detail_name)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #dcdde1;")
        right_layout.addWidget(line)
        
        # 描述
        self.detail_desc = QLabel("")
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setFont(QFont("Microsoft YaHei", 11))
        self.detail_desc.setStyleSheet("color: #34495e;")
        right_layout.addWidget(self.detail_desc)
        
        # 元信息
        meta_frame = QFrame()
        meta_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        meta_layout = QVBoxLayout(meta_frame)
        
        self.meta_category = QLabel("")
        self.meta_version = QLabel("")
        self.meta_author = QLabel("")
        self.meta_shortcut = QLabel("")
        
        for label in [self.meta_category, self.meta_version, self.meta_author, self.meta_shortcut]:
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setStyleSheet("color: #34495e;")
            meta_layout.addWidget(label)
        
        right_layout.addWidget(meta_frame)
        
        # 意图列表
        intents_label = QLabel("支持的操作:")
        intents_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        intents_label.setStyleSheet("color: #2c3e50;")
        right_layout.addWidget(intents_label)
        
        self.intents_list = QListWidget()
        self.intents_list.setMaximumHeight(120)
        self.intents_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        right_layout.addWidget(self.intents_list)
        
        # 执行按钮
        btn_layout = QHBoxLayout()
        
        self.execute_btn = QPushButton("执行技能")
        self.execute_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._on_execute_skill)
        btn_layout.addWidget(self.execute_btn)
        
        right_layout.addLayout(btn_layout)
        right_layout.addStretch()
        
        content_splitter.addWidget(right_widget)
        content_splitter.setSizes([350, 250])
        
        layout.addWidget(content_splitter)
        
        # 底部状态栏
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet("color: #95a5a6;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 历史记录按钮
        history_btn = QPushButton("📋 历史记录")
        history_btn.setFont(QFont("Microsoft YaHei", 9))
        history_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #3498db;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        history_btn.clicked.connect(self._show_history)
        status_layout.addWidget(history_btn)
        
        layout.addLayout(status_layout)
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+K 聚焦搜索框
        search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        search_shortcut.activated.connect(self.search_input.setFocus)
        
        # Esc 关闭对话框
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.close)
        
        # Enter 执行技能
        enter_shortcut = QShortcut(QKeySequence("Return"), self)
        enter_shortcut.activated.connect(self._on_execute_skill)
    
    def _setup_search_worker(self):
        """设置搜索工作线程"""
        self.search_thread = QThread()
        self.search_worker = SkillSearchWorker(self.registry)
        self.search_worker.moveToThread(self.search_thread)
        
        # 连接信号
        self.search_worker.results_ready.connect(self._on_search_results)
        self.search_thread.start()
    
    def _on_search_text_changed(self, text: str):
        """搜索文本变化"""
        # 使用定时器延迟搜索，避免频繁搜索
        if not hasattr(self, '_search_timer'):
            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._perform_search)
        
        self._search_timer.start(300)  # 300ms 延迟
    
    def _perform_search(self):
        """执行搜索"""
        query = self.search_input.text().strip()
        if not query:
            self.results_list.clear()
            self.stats_label.setText("输入关键词开始搜索")
            return
        
        # 在工作线程中执行搜索
        self.status_label.setText("搜索中...")
        self.search_worker.search(query)
    
    def _on_search_results(self, results: List[tuple]):
        """搜索结果回调"""
        self.current_results = results
        self._update_results_list(results)
        self._update_category_tabs(results)
        self.stats_label.setText(f"找到 {len(results)} 个匹配的技能")
        self.status_label.setText("就绪")
    
    def _update_results_list(self, results: List[tuple]):
        """更新结果列表"""
        self.results_list.clear()
        
        for skill_name, metadata, score in results:
            # 创建列表项
            icon = self._get_skill_icon(metadata.category)
            item_text = f"{icon} {metadata.display_name}\n{metadata.description[:60]}..."
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, skill_name)
            item.setSizeHint(QSize(0, 60))
            
            self.results_list.addItem(item)
        
        # 选中第一项
        if results:
            self.results_list.setCurrentRow(0)
    
    def _update_category_tabs(self, results: List[tuple]):
        """更新分类标签页"""
        # 清空现有标签页
        for widget in self.category_lists.values():
            widget.clear()
        
        # 按类别分组
        categories: Dict[str, List[tuple]] = {}
        for skill_name, metadata, score in results:
            category = metadata.category
            if category not in categories:
                categories[category] = []
            categories[category].append((skill_name, metadata, score))
        
        # 更新或创建标签页
        for category, items in categories.items():
            if category not in self.category_lists:
                # 创建新标签页
                list_widget = QListWidget()
                list_widget.setStyleSheet(self.results_list.styleSheet())
                list_widget.currentItemChanged.connect(self._on_category_result_selected)
                list_widget.itemDoubleClicked.connect(self._on_result_double_clicked)
                
                tab_name = self._get_category_name(category)
                self.category_tabs.addTab(list_widget, tab_name)
                self.category_lists[category] = list_widget
            
            # 更新列表
            list_widget = self.category_lists[category]
            list_widget.clear()
            
            for skill_name, metadata, score in items:
                icon = self._get_skill_icon(metadata.category)
                item_text = f"{icon} {metadata.display_name}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, skill_name)
                list_widget.addItem(item)
    
    def _on_result_selected(self, current, previous):
        """结果选中回调"""
        if current:
            skill_name = current.data(Qt.ItemDataRole.UserRole)
            self._show_skill_detail(skill_name)
    
    def _on_category_result_selected(self, current, previous):
        """分类结果选中回调"""
        if current:
            skill_name = current.data(Qt.ItemDataRole.UserRole)
            self._show_skill_detail(skill_name)
    
    def _on_result_double_clicked(self, item):
        """结果双击回调"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name:
            self.skill_execute.emit(skill_name, {})
            self.close()
    
    def _show_skill_detail(self, skill_name: str):
        """显示技能详情"""
        metadata = self.registry.get_metadata(skill_name)
        if metadata:
            # 更新详情
            self.detail_name.setText(metadata.display_name)
            self.detail_desc.setText(metadata.description)
            
            # 更新元信息
            self.meta_category.setText(f"类别: {metadata.category}")
            self.meta_version.setText(f"版本: {metadata.version}")
            self.meta_author.setText(f"作者: {metadata.author}")
            self.meta_shortcut.setText(f"快捷键: {metadata.shortcut or '无'}")
            
            # 更新意图列表
            self.intents_list.clear()
            for intent in metadata.intents:
                self.intents_list.addItem(intent)
            
            # 启用执行按钮
            self.execute_btn.setEnabled(True)
            
            # 发送选择信号
            self.skill_select.emit(skill_name)
    
    def _on_execute_skill(self):
        """执行技能"""
        current_item = self.results_list.currentItem()
        if current_item:
            skill_name = current_item.data(Qt.ItemDataRole.UserRole)
            
            # 获取选中的意图
            selected_intent_items = self.intents_list.selectedItems()
            intent = selected_intent_items[0].text() if selected_intent_items else ""
            
            # 构建参数
            params = {
                "intent": intent,
                "input_data": {}
            }
            
            # 添加到历史记录
            query = self.search_input.text().strip()
            if query and query not in self.search_history:
                self.search_history.append(query)
            
            # 发送执行信号
            self.skill_execute.emit(skill_name, params)
            self.close()
    
    def _show_history(self):
        """显示历史记录"""
        if not self.search_history:
            self.status_label.setText("暂无历史记录")
            return
        
        # 显示历史记录
        history_text = "搜索历史:\n" + "\n".join(self.search_history[-10:])
        self.status_label.setText(history_text)
    
    def _get_skill_icon(self, category: str) -> str:
        """获取技能图标"""
        icons = {
            "coding": "💻",
            "knowledge": "📚",
            "ppt": "📊",
            "evaluation": "📝",
            "file": "📁",
            "format": "🔄",
            "persona": "🎭",
            "default": "⚡"
        }
        return icons.get(category, icons["default"])
    
    def _get_category_name(self, category: str) -> str:
        """获取分类名称"""
        names = {
            "coding": "💻 编程",
            "knowledge": "📚 知识",
            "ppt": "📊 演示",
            "evaluation": "📝 评估",
            "file": "📁 文件",
            "format": "🔄 格式",
            "persona": "🎭 角色"
        }
        return names.get(category, category)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止搜索线程
        self.search_thread.quit()
        self.search_thread.wait()
        super().closeEvent(event)
    
    def show_dialog(self):
        """显示对话框"""
        self.show()
        self.search_input.setFocus()
        self.search_input.clear()
        self.results_list.clear()
        self.stats_label.setText("输入关键词开始搜索")
        self.status_label.setText("就绪")


class SkillQuickAccessWidget(QWidget):
    """技能快速访问组件
    
    用于在对话框中快速访问技能
    支持 / 命令触发
    """
    
    # 信号定义
    skill_execute = pyqtSignal(str, dict)  # 技能名称，参数
    command_triggered = pyqtSignal(str)  # 命令触发
    
    def __init__(self, registry: SkillRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.is_visible = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入 / 技能名称或关键词...")
        self.search_input.setFont(QFont("Microsoft YaHei", 11))
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_execute)
        layout.addWidget(self.search_input)
        
        # 结果列表
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(200)
        self.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #ebf5fb;
            }
        """)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.results_list.hide()
        layout.addWidget(self.results_list)
        
        # 提示标签
        self.hint_label = QLabel("输入 / 开始搜索技能")
        self.hint_label.setFont(QFont("Microsoft YaHei", 9))
        self.hint_label.setStyleSheet("color: #95a5a6;")
        layout.addWidget(self.hint_label)
        
        # 隐藏组件
        self.hide()
    
    def _on_text_changed(self, text: str):
        """文本变化回调"""
        if not text.startswith('/'):
            self.results_list.hide()
            self.hint_label.setText("输入 / 开始搜索技能")
            return
        
        # 获取建议
        query = text[1:].strip()
        if not query:
            self.results_list.hide()
            self.hint_label.setText("输入技能名称或关键词")
            return
        
        # 搜索技能
        self.results_list.clear()
        
        all_metadata = self.registry.get_all_metadata()
        matches = []
        
        for skill_name, metadata in all_metadata.items():
            score = 0
            
            # 名称匹配
            if query in metadata.display_name.lower():
                score += 10
            
            # 类别匹配
            if query in metadata.category.lower():
                score += 5
            
            # 标签匹配
            for tag in metadata.tags:
                if query in tag.lower():
                    score += 3
            
            if score > 0:
                matches.append((skill_name, metadata, score))
        
        # 按匹配度排序
        matches.sort(key=lambda x: x[2], reverse=True)
        
        # 添加到结果列表
        for skill_name, metadata, score in matches[:5]:  # 最多显示5个
            icon = self._get_skill_icon(metadata.category)
            item_text = f"{icon} {metadata.display_name}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, skill_name)
            self.results_list.addItem(item)
        
        # 显示结果列表
        if matches:
            self.results_list.show()
            self.hint_label.setText(f"找到 {len(matches)} 个匹配的技能")
        else:
            self.results_list.hide()
            self.hint_label.setText("未找到匹配的技能")
    
    def _on_item_clicked(self, item):
        """点击结果项"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name:
            self.search_input.setText(f"/{skill_name}")
    
    def _on_item_double_clicked(self, item):
        """双击结果项"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name:
            self.skill_execute.emit(skill_name, {})
            self.hide_quick_access()
    
    def _on_execute(self):
        """执行命令"""
        command = self.search_input.text().strip()
        
        if not command:
            return
        
        if command.startswith('/'):
            skill_name = command[1:].strip()
            
            # 验证技能是否存在
            skill = self.registry.get_skill(skill_name)
            if skill:
                self.skill_execute.emit(skill_name, {})
                self.hide_quick_access()
            else:
                # 尝试模糊匹配
                self._fuzzy_execute(skill_name)
        else:
            # 普通命令
            self.command_triggered.emit(command)
            self.hide_quick_access()
    
    def _fuzzy_execute(self, query: str):
        """模糊匹配执行"""
        best_match = None
        best_score = 0
        
        all_metadata = self.registry.get_all_metadata()
        for skill_name, metadata in all_metadata.items():
            score = 0
            
            if query in metadata.display_name.lower():
                score += 10
            
            for tag in metadata.tags:
                if query in tag.lower():
                    score += 3
            
            if score > best_score:
                best_score = score
                best_match = skill_name
        
        if best_match and best_score > 3:
            self.skill_execute.emit(best_match, {})
            self.hide_quick_access()
        else:
            self.hint_label.setText(f"未找到匹配的技能: {query}")
    
    def _get_skill_icon(self, category: str) -> str:
        """获取技能图标"""
        icons = {
            "coding": "💻",
            "knowledge": "📚",
            "ppt": "📊",
            "evaluation": "📝",
            "file": "📁",
            "format": "🔄",
            "persona": "🎭",
            "default": "⚡"
        }
        return icons.get(category, icons["default"])
    
    def show_quick_access(self):
        """显示快速访问"""
        self.show()
        self.search_input.setFocus()
        self.search_input.clear()
        self.results_list.hide()
        self.is_visible = True
    
    def hide_quick_access(self):
        """隐藏快速访问"""
        self.hide()
        self.search_input.clear()
        self.results_list.hide()
        self.is_visible = False
    
    def toggle_quick_access(self):
        """切换快速访问显示状态"""
        if self.is_visible:
            self.hide_quick_access()
        else:
            self.show_quick_access()


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试用的注册表
    registry = SkillRegistry()
    
    # 创建测试技能
    from opencopilot.capabilities.skill.coding_skill import CodingSkill
    from opencopilot.capabilities.skill.knowledge_skill import KnowledgeSkill
    
    coding_skill = CodingSkill()
    knowledge_skill = KnowledgeSkill()
    
    registry.register(coding_skill)
    registry.register(knowledge_skill)
    
    # 创建搜索对话框
    dialog = SkillSearchDialog(registry)
    dialog.skill_execute.connect(lambda name, params: print(f"执行技能: {name}, 参数: {params}"))
    dialog.show_dialog()
    
    sys.exit(app.exec())