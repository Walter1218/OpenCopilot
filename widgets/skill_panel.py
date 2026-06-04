from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
"""
技能面板组件
提供技能搜索、浏览、执行的统一界面
参考 WorkBuddy 等工具的设计理念
"""

import asyncio
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFrame, QListWidget, QListWidgetItem, QScrollArea,
    QGridLayout, QGroupBox, QTabWidget, QTextEdit, QSplitter,
    QSizePolicy, QToolTip, QMenu, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QAction, QKeySequence

# 导入 Skill 架构
import sys
import os
from opencopilot.capabilities.skill import SkillRegistry, SkillContext, SkillMetadata


class SkillCard(QFrame):
    """技能卡片组件"""
    
    # 信号
    skill_clicked = pyqtSignal(str)  # 技能名称
    skill_execute = pyqtSignal(str, dict)  # 技能名称，参数
    
    def __init__(self, skill_name: str, metadata: SkillMetadata, parent=None):
        super().__init__(parent)
        self.skill_name = skill_name
        self.metadata = metadata
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 技能图标和名称
        header_layout = QHBoxLayout()
        
        # 图标（根据类别选择）
        icon_label = QLabel(self._get_icon())
        icon_label.setFont(QFont("Segoe UI Emoji", 24))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)
        
        # 名称和类别
        name_layout = QVBoxLayout()
        
        name_label = QLabel(self.metadata.display_name)
        name_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #2c3e50;")
        name_layout.addWidget(name_label)
        
        category_label = QLabel(self.metadata.category)
        category_label.setFont(QFont("Microsoft YaHei", 9))
        category_label.setStyleSheet("color: #7f8c8d;")
        name_layout.addWidget(category_label)
        
        header_layout.addLayout(name_layout)
        header_layout.addStretch()
        
        # 快捷键（如果有）
        if self.metadata.shortcut:
            shortcut_label = QLabel(self.metadata.shortcut)
            shortcut_label.setFont(QFont("Consolas", 10))
            shortcut_label.setStyleSheet("""
                QLabel {
                    background-color: #ecf0f1;
                    border-radius: 4px;
                    padding: 2px 6px;
                    color: #2c3e50;
                }
            """)
            header_layout.addWidget(shortcut_label)
        
        layout.addLayout(header_layout)
        
        # 描述
        desc_label = QLabel(self.metadata.description)
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont("Microsoft YaHei", 10))
        desc_label.setStyleSheet("color: #34495e;")
        layout.addWidget(desc_label)
        
        # 标签
        if self.metadata.tags:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(4)
            
            for tag in self.metadata.tags[:5]:  # 最多显示5个标签
                tag_label = QLabel(f"#{tag}")
                tag_label.setFont(QFont("Microsoft YaHei", 8))
                tag_label.setStyleSheet("""
                    QLabel {
                        background-color: #3498db;
                        color: white;
                        border-radius: 8px;
                        padding: 2px 8px;
                    }
                """)
                tags_layout.addWidget(tag_label)
            
            tags_layout.addStretch()
            layout.addLayout(tags_layout)
        
        # 执行按钮
        btn_layout = QHBoxLayout()
        
        execute_btn = QPushButton("执行")
        execute_btn.setFont(QFont("Microsoft YaHei", 10))
        execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        execute_btn.clicked.connect(lambda: self.skill_execute.emit(self.skill_name, {}))
        btn_layout.addWidget(execute_btn)
        
        detail_btn = QPushButton("详情")
        detail_btn.setFont(QFont("Microsoft YaHei", 10))
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        detail_btn.clicked.connect(lambda: self.skill_clicked.emit(self.skill_name))
        btn_layout.addWidget(detail_btn)
        
        layout.addLayout(btn_layout)
    
    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet("""
            SkillCard {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 10px;
                margin: 4px;
            }
            SkillCard:hover {
                border: 2px solid #3498db;
                background-color: #f8f9fa;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(180)
    
    def _get_icon(self) -> str:
        """根据类别获取图标"""
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
        return icons.get(self.metadata.category, icons["default"])


class SkillDetailPanel(QWidget):
    """技能详情面板"""
    
    # 信号
    execute_requested = pyqtSignal(str, dict)  # 技能名称，参数
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_skill = None
        self.registry = None
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题区域
        self.title_label = QLabel("选择一个技能查看详情")
        self.title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(self.title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #dcdde1;")
        layout.addWidget(line)
        
        # 描述
        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setFont(QFont("Microsoft YaHei", 11))
        self.desc_label.setStyleSheet("color: #34495e;")
        layout.addWidget(self.desc_label)
        
        # 元信息
        self.meta_group = QGroupBox("技能信息")
        self.meta_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        meta_layout = QGridLayout(self.meta_group)
        
        self.category_value = QLabel("")
        self.version_value = QLabel("")
        self.author_value = QLabel("")
        self.shortcut_value = QLabel("")
        
        meta_layout.addWidget(QLabel("类别:"), 0, 0)
        meta_layout.addWidget(self.category_value, 0, 1)
        meta_layout.addWidget(QLabel("版本:"), 1, 0)
        meta_layout.addWidget(self.version_value, 1, 1)
        meta_layout.addWidget(QLabel("作者:"), 2, 0)
        meta_layout.addWidget(self.author_value, 2, 1)
        meta_layout.addWidget(QLabel("快捷键:"), 3, 0)
        meta_layout.addWidget(self.shortcut_value, 3, 1)
        
        layout.addWidget(self.meta_group)
        
        # 意图列表
        self.intents_group = QGroupBox("支持的操作")
        self.intents_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        intents_layout = QVBoxLayout(self.intents_group)
        
        self.intents_list = QListWidget()
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
            QListWidget::item:hover {
                background-color: #ebf5fb;
            }
        """)
        intents_layout.addWidget(self.intents_list)
        
        layout.addWidget(self.intents_group)
        
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
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._on_execute)
        btn_layout.addWidget(self.execute_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
    
    def set_skill(self, skill_name: str, registry: SkillRegistry):
        """设置当前技能"""
        self.current_skill = skill_name
        self.registry = registry
        
        skill = registry.get_skill(skill_name)
        if skill:
            metadata = skill.metadata
            
            # 更新标题
            self.title_label.setText(f"{metadata.display_name}")
            
            # 更新描述
            self.desc_label.setText(metadata.description)
            
            # 更新元信息
            self.category_value.setText(metadata.category)
            self.version_value.setText(metadata.version)
            self.author_value.setText(metadata.author)
            self.shortcut_value.setText(metadata.shortcut or "无")
            
            # 更新意图列表
            self.intents_list.clear()
            for intent in metadata.intents:
                self.intents_list.addItem(intent)
            
            # 启用执行按钮
            self.execute_btn.setEnabled(True)
        else:
            self.title_label.setText("技能未找到")
            self.desc_label.setText(f"无法加载技能: {skill_name}")
            self.execute_btn.setEnabled(False)
    
    def _on_execute(self):
        """执行技能"""
        if self.current_skill:
            # 获取选中的意图
            selected_items = self.intents_list.selectedItems()
            intent = selected_items[0].text() if selected_items else ""
            
            # 发送执行信号
            self.execute_requested.emit(self.current_skill, {
                "intent": intent,
                "input_data": {}
            })


class SkillPanel(QWidget):
    """技能面板主组件"""
    
    # 信号
    skill_execute = pyqtSignal(str, dict)  # 技能名称，参数
    skill_search = pyqtSignal(str)  # 搜索关键词
    
    def __init__(self, registry: SkillRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.skill_cards: Dict[str, SkillCard] = {}
        self._setup_ui()
        self._load_skills()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：技能列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)
        
        # 搜索框
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索技能...")
        self.search_input.setFont(QFont("Microsoft YaHei", 11))
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #dcdde1;
            }
        """)
        refresh_btn.clicked.connect(self._load_skills)
        search_layout.addWidget(refresh_btn)
        
        left_layout.addLayout(search_layout)
        
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
        
        # 全部技能标签页
        self.all_skills_widget = QWidget()
        self.all_skills_layout = QGridLayout(self.all_skills_widget)
        self.all_skills_layout.setSpacing(8)
        self.category_tabs.addTab(self.all_skills_widget, "全部")
        
        # 各类别标签页
        self.category_widgets: Dict[str, QWidget] = {}
        
        left_layout.addWidget(self.category_tabs)
        
        # 统计信息
        self.stats_label = QLabel("共 0 个技能")
        self.stats_label.setFont(QFont("Microsoft YaHei", 10))
        self.stats_label.setStyleSheet("color: #7f8c8d;")
        left_layout.addWidget(self.stats_label)
        
        splitter.addWidget(left_widget)
        
        # 右侧：技能详情
        self.detail_panel = SkillDetailPanel()
        self.detail_panel.execute_requested.connect(self._on_execute_skill)
        splitter.addWidget(self.detail_panel)
        
        # 设置分割比例
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
    
    def _load_skills(self):
        """加载所有技能"""
        # 清空现有卡片
        self._clear_cards()
        
        # 获取所有技能元数据
        all_metadata = self.registry.get_all_metadata()
        
        # 按类别分组
        categories: Dict[str, List[str]] = {}
        
        for skill_name, metadata in all_metadata.items():
            category = metadata.category
            if category not in categories:
                categories[category] = []
            categories[category].append(skill_name)
        
        # 创建技能卡片
        row, col = 0, 0
        max_cols = 2  # 每行2个卡片
        
        for skill_name, metadata in all_metadata.items():
            # 创建卡片
            card = SkillCard(skill_name, metadata)
            card.skill_clicked.connect(self._on_skill_clicked)
            card.skill_execute.connect(self._on_execute_skill)
            
            # 添加到网格
            self.all_skills_layout.addWidget(card, row, col)
            self.skill_cards[skill_name] = card
            
            # 更新位置
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # 更新类别标签页
        self._update_category_tabs(categories)
        
        # 更新统计
        self.stats_label.setText(f"共 {len(all_metadata)} 个技能")
    
    def _clear_cards(self):
        """清空所有卡片"""
        # 清空全部技能布局
        while self.all_skills_layout.count():
            item = self.all_skills_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 清空类别标签页
        for widget in self.category_widgets.values():
            widget.deleteLater()
        self.category_widgets.clear()
        
        # 重置标签页
        while self.category_tabs.count() > 1:
            self.category_tabs.removeTab(1)
        
        self.skill_cards.clear()
    
    def _update_category_tabs(self, categories: Dict[str, List[str]]):
        """更新类别标签页"""
        category_icons = {
            "coding": "💻 编程",
            "knowledge": "📚 知识",
            "ppt": "📊 演示",
            "evaluation": "📝 评估",
            "file": "📁 文件",
            "format": "🔄 格式",
            "persona": "🎭 角色"
        }
        
        for category, skills in categories.items():
            if category not in self.category_widgets:
                # 创建新标签页
                widget = QWidget()
                layout = QGridLayout(widget)
                layout.setSpacing(8)
                
                # 添加技能卡片
                row, col = 0, 0
                max_cols = 2
                
                for skill_name in skills:
                    if skill_name in self.skill_cards:
                        card = self.skill_cards[skill_name]
                        # 创建副本（因为一个widget只能有一个父）
                        new_card = SkillCard(skill_name, self.registry.get_skill(skill_name).metadata)
                        new_card.skill_clicked.connect(self._on_skill_clicked)
                        new_card.skill_execute.connect(self._on_execute_skill)
                        
                        layout.addWidget(new_card, row, col)
                        
                        col += 1
                        if col >= max_cols:
                            col = 0
                            row += 1
                
                # 添加标签页
                tab_name = category_icons.get(category, category)
                self.category_tabs.addTab(widget, tab_name)
                self.category_widgets[category] = widget
    
    def _on_search(self, text: str):
        """搜索技能"""
        search_text = text.lower().strip()
        
        for skill_name, card in self.skill_cards.items():
            metadata = self.registry.get_metadata(skill_name)
            if metadata:
                # 检查是否匹配
                match = (
                    search_text in metadata.display_name.lower() or
                    search_text in metadata.description.lower() or
                    search_text in metadata.category.lower() or
                    any(search_text in tag for tag in metadata.tags) or
                    any(search_text in intent for intent in metadata.intents)
                )
                
                card.setVisible(match or not search_text)
        
        # 发送搜索信号
        self.skill_search.emit(text)
    
    def _on_skill_clicked(self, skill_name: str):
        """技能卡片点击"""
        self.detail_panel.set_skill(skill_name, self.registry)
    
    def _on_execute_skill(self, skill_name: str, params: Dict[str, Any]):
        """执行技能"""
        self.skill_execute.emit(skill_name, params)
    
    def refresh(self):
        """刷新技能列表"""
        self._load_skills()


class SkillSearchWidget(QWidget):
    """技能搜索组件（用于对话框中）"""
    
    # 信号
    skill_selected = pyqtSignal(str, str)  # 技能名称，意图
    skill_execute = pyqtSignal(str, dict)  # 技能名称，参数
    
    def __init__(self, registry: SkillRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
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
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.returnPressed.connect(self._on_execute)
        layout.addWidget(self.search_input)
        
        # 结果列表
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
                max-height: 200px;
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
        layout.addWidget(self.results_list)
        
        # 提示标签
        self.hint_label = QLabel("输入 / 开始搜索技能")
        self.hint_label.setFont(QFont("Microsoft YaHei", 9))
        self.hint_label.setStyleSheet("color: #95a5a6;")
        layout.addWidget(self.hint_label)
        
        # 隐藏结果列表
        self.results_list.hide()
    
    def _on_search(self, text: str):
        """搜索技能"""
        if not text.startswith('/'):
            self.results_list.hide()
            self.hint_label.setText("输入 / 开始搜索技能")
            return
        
        # 移除 / 前缀
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
            # 计算匹配度
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
            
            # 意图匹配
            for intent in metadata.intents:
                if query in intent.lower():
                    score += 2
            
            # 描述匹配
            if query in metadata.description.lower():
                score += 1
            
            if score > 0:
                matches.append((skill_name, metadata, score))
        
        # 按匹配度排序
        matches.sort(key=lambda x: x[2], reverse=True)
        
        # 添加到结果列表
        for skill_name, metadata, score in matches[:10]:  # 最多显示10个
            item = QListWidgetItem(f"{metadata.display_name} - {metadata.description[:50]}...")
            item.setData(Qt.ItemDataRole.UserRole, skill_name)
            self.results_list.addItem(item)
        
        # 显示结果列表
        if matches:
            self.results_list.show()
            self.hint_label.setText(f"找到 {len(matches)} 个匹配的技能")
        else:
            self.results_list.hide()
            self.hint_label.setText("未找到匹配的技能")
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """点击结果项"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name:
            self.skill_selected.emit(skill_name, "")
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击结果项"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name:
            self.skill_execute.emit(skill_name, {})
            self.search_input.clear()
            self.results_list.hide()
    
    def _on_execute(self):
        """执行当前选中的技能"""
        current_item = self.results_list.currentItem()
        if current_item:
            skill_name = current_item.data(Qt.ItemDataRole.UserRole)
            if skill_name:
                self.skill_execute.emit(skill_name, {})
                self.search_input.clear()
                self.results_list.hide()


class SkillCommandParser:
    """技能命令解析器
    
    支持格式：
    - /skill_name 执行技能
    - /skill_name:intent 执行特定意图
    - /skill_name param1=value1 param2=value2 带参数执行
    """
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
    
    def parse(self, command: str) -> Optional[Dict[str, Any]]:
        """
        解析命令
        
        Args:
            command: 命令字符串
        
        Returns:
            Dict: 解析结果，包含 skill_name, intent, params
        """
        if not command.startswith('/'):
            return None
        
        # 移除 / 前缀
        content = command[1:].strip()
        
        if not content:
            return None
        
        # 分割命令和参数
        parts = content.split()
        command_part = parts[0]
        params_part = parts[1:] if len(parts) > 1 else []
        
        # 解析技能名称和意图
        if ':' in command_part:
            skill_name, intent = command_part.split(':', 1)
        else:
            skill_name = command_part
            intent = ""
        
        # 验证技能是否存在
        skill = self.registry.get_skill(skill_name)
        if not skill:
            # 尝试模糊匹配
            skill_name = self._fuzzy_match(skill_name)
            if not skill_name:
                return None
            skill = self.registry.get_skill(skill_name)
        
        # 解析参数
        params = {}
        for param in params_part:
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        
        return {
            "skill_name": skill_name,
            "intent": intent,
            "params": params,
            "metadata": skill.metadata
        }
    
    def _fuzzy_match(self, query: str) -> Optional[str]:
        """模糊匹配技能名称"""
        query = query.lower()
        
        best_match = None
        best_score = 0
        
        for skill_name in self.registry.list_skills():
            metadata = self.registry.get_metadata(skill_name)
            if metadata:
                # 计算匹配度
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
                
                if score > best_score:
                    best_score = score
                    best_match = skill_name
        
        return best_match if best_score > 0 else None
    
    def get_suggestions(self, partial: str) -> List[Dict[str, str]]:
        """获取命令建议"""
        suggestions = []
        
        if not partial.startswith('/'):
            return suggestions
        
        query = partial[1:].lower().strip()
        
        for skill_name in self.registry.list_skills():
            metadata = self.registry.get_metadata(skill_name)
            if metadata:
                # 检查是否匹配
                if (query in metadata.display_name.lower() or 
                    query in metadata.category.lower() or
                    any(query in tag for tag in metadata.tags)):
                    
                    suggestions.append({
                        "command": f"/{skill_name}",
                        "name": metadata.display_name,
                        "description": metadata.description
                    })
        
        return suggestions[:10]  # 最多返回10个建议


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
    
    # 创建技能面板
    panel = SkillPanel(registry)
    panel.setWindowTitle("技能面板测试")
    panel.resize(1000, 600)
    panel.show()
    
    sys.exit(app.exec())