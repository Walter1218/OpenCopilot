"""
技能增强版右键菜单组件
集成 Skill 功能，支持上下文动态显示
"""

from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import QMenu, QWidget, QApplication
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtCore import pyqtSignal, Qt

# 导入 Skill 架构
import sys
import os
from opencopilot.capabilities.skill import SkillRegistry, SkillContext, IntentRouter


class SkillContextMenu(QMenu):
    """技能增强版右键菜单
    
    特性：
    1. 根据上下文动态显示相关 Skill
    2. 支持快捷指令（/skill_name）
    3. 智能推荐相关操作
    4. 支持多级菜单
    """
    
    # 信号定义
    skill_execute = pyqtSignal(str, dict)  # 技能名称，参数
    action_triggered = pyqtSignal(str, object)  # 动作触发信号
    
    def __init__(self, registry: SkillRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.router = IntentRouter(registry)
        
        self.context_type = "text"
        self.context_data = {}
        self.selected_text = ""
        self.file_path = ""
        self.code_language = ""
        
        # 动态菜单项列表
        self.dynamic_actions: List[QAction] = []
        self.skill_menus: Dict[str, QMenu] = {}
        
        # 设置菜单样式
        self._apply_style()
    
    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px 8px 12px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
            QMenu::item:disabled {
                color: #95a5a6;
            }
            QMenu::separator {
                height: 1px;
                background-color: #ecf0f1;
                margin: 4px 8px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
                margin-left: 8px;
            }
        """)
    
    def show_for_text(self, text: str, position, context_data: Dict[str, Any] = None):
        """为文本显示菜单
        
        Args:
            text: 选中的文本
            position: 显示位置
            context_data: 上下文数据
        """
        self.context_type = "text"
        self.selected_text = text
        self.context_data = context_data or {}
        
        # 清空并重建菜单
        self.clear()
        self._build_text_menu()
        
        # 显示菜单
        self.exec(position)
    
    def show_for_code(self, code: str, language: str, position, context_data: Dict[str, Any] = None):
        """为代码显示菜单
        
        Args:
            code: 代码文本
            language: 编程语言
            position: 显示位置
            context_data: 上下文数据
        """
        self.context_type = "code"
        self.selected_text = code
        self.code_language = language
        self.context_data = context_data or {}
        
        # 清空并重建菜单
        self.clear()
        self._build_code_menu()
        
        # 显示菜单
        self.exec(position)
    
    def show_for_file(self, file_path: str, position, context_data: Dict[str, Any] = None):
        """为文件显示菜单
        
        Args:
            file_path: 文件路径
            position: 显示位置
            context_data: 上下文数据
        """
        self.context_type = "file"
        self.file_path = file_path
        self.context_data = context_data or {}
        
        # 清空并重建菜单
        self.clear()
        self._build_file_menu()
        
        # 显示菜单
        self.exec(position)
    
    def _build_text_menu(self):
        """构建文本菜单"""
        # 基础操作
        self._add_basic_actions()
        self.addSeparator()
        
        # AI 操作
        self._add_ai_actions()
        self.addSeparator()
        
        # Skill 操作（根据上下文动态显示）
        self._add_skill_actions("text")
        self.addSeparator()
        
        # 快捷指令入口
        self._add_command_entry()
    
    def _build_code_menu(self):
        """构建代码菜单"""
        # 基础操作
        self._add_basic_actions()
        self.addSeparator()
        
        # 代码专用操作
        self._add_code_actions()
        self.addSeparator()
        
        # Skill 操作（根据上下文动态显示）
        self._add_skill_actions("code")
        self.addSeparator()
        
        # 快捷指令入口
        self._add_command_entry()
    
    def _build_file_menu(self):
        """构建文件菜单"""
        # 文件操作
        self._add_file_actions()
        self.addSeparator()
        
        # Skill 操作（根据上下文动态显示）
        self._add_skill_actions("file")
        self.addSeparator()
        
        # 快捷指令入口
        self._add_command_entry()
    
    def _add_basic_actions(self):
        """添加基础操作"""
        self._add_action("📋 复制", "copy", "Ctrl+C")
        self._add_action("📌 粘贴", "paste", "Ctrl+V")
        self._add_action("✂️ 剪切", "cut", "Ctrl+X")
    
    def _add_ai_actions(self):
        """添加 AI 操作"""
        self._add_action("🌐 翻译", "translate", "Ctrl+T")
        self._add_action("✨ 润色", "polish", "Ctrl+P")
        self._add_action("📝 修订", "revise", "Ctrl+R")
        self._add_action("💡 解释", "explain", "Ctrl+E")
        self._add_action("📊 总结", "summarize", "Ctrl+M")
    
    def _add_code_actions(self):
        """添加代码操作"""
        self._add_action("🔍 解释代码", "explain_code", "Ctrl+Shift+E")
        self._add_action("⚡ 优化代码", "optimize_code", "Ctrl+Shift+O")
        self._add_action("🐛 查找 Bug", "find_bugs", "Ctrl+Shift+B")
        self._add_action("📝 添加注释", "add_comment", "Ctrl+Shift+M")
        self._add_action("🔄 重构代码", "refactor_code", "Ctrl+Shift+R")
    
    def _add_file_actions(self):
        """添加文件操作"""
        self._add_action("📂 打开文件", "open_file")
        self._add_action("👁️ 预览文件", "preview_file")
        self._add_action("📝 重命名", "rename_file")
        self._add_action("📋 复制路径", "copy_path")
    
    def _add_skill_actions(self, context_type: str):
        """添加 Skill 操作（根据上下文动态显示）"""
        # 获取推荐的技能
        recommended_skills = self._get_recommended_skills(context_type)
        
        if not recommended_skills:
            return
        
        # 创建 Skill 子菜单
        skill_menu = QMenu("🎯 技能推荐", self)
        skill_menu.setStyleSheet(self.styleSheet())
        
        for skill_name, score in recommended_skills[:5]:  # 最多显示5个推荐
            metadata = self.registry.get_metadata(skill_name)
            if metadata:
                # 创建菜单项
                icon = self._get_skill_icon(metadata.category)
                action = skill_menu.addAction(f"{icon} {metadata.display_name}")
                action.setToolTip(metadata.description)
                action.setData(skill_name)
                action.triggered.connect(lambda checked, name=skill_name: self._on_skill_triggered(name))
        
        # 添加分隔线和更多技能入口
        skill_menu.addSeparator()
        more_action = skill_menu.addAction("📋 查看所有技能...")
        more_action.triggered.connect(self._on_show_all_skills)
        
        self.addMenu(skill_menu)
    
    def _add_command_entry(self):
        """添加快捷指令入口"""
        cmd_action = self._add_action("⌨️ 输入命令...", "open_command", "/")
        cmd_action.setToolTip("输入 /技能名称 执行技能")
    
    def _add_action(self, text: str, action_id: str, shortcut: str = None) -> QAction:
        """添加菜单项"""
        action = QAction(text, self)
        action.setData(action_id)
        
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        
        action.triggered.connect(lambda checked, aid=action_id: self._on_action_triggered(aid))
        self.addAction(action)
        
        return action
    
    def _get_recommended_skills(self, context_type: str) -> List[tuple]:
        """获取推荐的技能
        
        Args:
            context_type: 上下文类型（text/code/file）
        
        Returns:
            List[tuple]: (技能名称, 置信度) 列表
        """
        # 创建上下文
        intent = self._detect_intent(context_type)
        context = SkillContext(
            intent=intent,
            input_data={
                "text": self.selected_text,
                "file_path": self.file_path,
                "language": self.code_language,
                "context_type": context_type,
                **self.context_data
            }
        )
        
        # 使用路由器获取推荐
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            recommendations = loop.run_until_complete(
                self.router.route_multiple(context, max_skills=5)
            )
            loop.close()
            return recommendations
        except Exception as e:
            print(f"获取推荐技能失败: {e}")
            return []
    
    def _detect_intent(self, context_type: str) -> str:
        """检测意图
        
        Args:
            context_type: 上下文类型
        
        Returns:
            str: 意图
        """
        # 基于上下文类型检测意图
        if context_type == "code":
            # 分析代码内容
            if "bug" in self.selected_text.lower() or "error" in self.selected_text.lower():
                return "bug_fix"
            elif "def " in self.selected_text or "class " in self.selected_text:
                return "explain"
            else:
                return "code_review"
        
        elif context_type == "file":
            # 分析文件类型
            if self.file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp')):
                return "code_review"
            elif self.file_path.endswith(('.md', '.txt', '.docx')):
                return "document_analysis"
            elif self.file_path.endswith(('.pptx', '.ppt')):
                return "ppt_edit"
            else:
                return "file_process"
        
        else:  # text
            # 分析文本内容
            text_lower = self.selected_text.lower()
            if any(word in text_lower for word in ['翻译', 'translate', '英文', '中文']):
                return "translate"
            elif any(word in text_lower for word in ['总结', '概括', '摘要']):
                return "summarize"
            elif any(word in text_lower for word in ['优化', '改进', '提升']):
                return "polish"
            else:
                return "explain"
    
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
    
    def _on_action_triggered(self, action_id: str):
        """动作触发回调"""
        self.action_triggered.emit(action_id, None)
    
    def _on_skill_triggered(self, skill_name: str):
        """技能触发回调"""
        # 构建执行参数
        params = {
            "context_type": self.context_type,
            "selected_text": self.selected_text,
            "file_path": self.file_path,
            "language": self.code_language,
            **self.context_data
        }
        
        # 根据上下文类型设置默认意图
        if self.context_type == "code":
            params["intent"] = "explain"
        elif self.context_type == "file":
            params["intent"] = "file_process"
        else:
            params["intent"] = "explain"
        
        self.skill_execute.emit(skill_name, params)
    
    def _on_show_all_skills(self):
        """显示所有技能"""
        self.action_triggered.emit("show_all_skills", None)


class SkillCommandWidget(QWidget):
    """技能命令输入组件
    
    支持：
    - /skill_name 执行技能
    - /skill_name:intent 执行特定意图
    - 自动补全
    - 历史记录
    """
    
    # 信号定义
    command_execute = pyqtSignal(str, dict)  # 技能名称，参数
    command_cancel = pyqtSignal()  # 取消命令
    
    def __init__(self, registry: SkillRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.command_history: List[str] = []
        self.history_index = -1
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QLabel
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题
        title_layout = QHBoxLayout()
        title_label = QLabel("⌨️ 技能命令")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: #95a5a6;
            }
            QPushButton:hover {
                color: #e74c3c;
            }
        """)
        close_btn.clicked.connect(self.command_cancel.emit)
        title_layout.addWidget(close_btn)
        
        layout.addLayout(title_layout)
        
        # 命令输入框
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("输入 /技能名称 执行技能...")
        self.command_input.setFont(QFont("Consolas", 12))
        self.command_input.setStyleSheet("""
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
        self.command_input.textChanged.connect(self._on_text_changed)
        self.command_input.returnPressed.connect(self._on_execute)
        self.command_input.installEventFilter(self)
        layout.addWidget(self.command_input)
        
        # 建议列表
        self.suggestions_list = QListWidget()
        self.suggestions_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
                max-height: 150px;
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
        self.suggestions_list.itemClicked.connect(self._on_suggestion_clicked)
        self.suggestions_list.itemDoubleClicked.connect(self._on_suggestion_double_clicked)
        self.suggestions_list.hide()
        layout.addWidget(self.suggestions_list)
        
        # 提示标签
        self.hint_label = QLabel("输入 / 开始搜索技能，按 Enter 执行")
        self.hint_label.setFont(QFont("Microsoft YaHei", 9))
        self.hint_label.setStyleSheet("color: #95a5a6;")
        layout.addWidget(self.hint_label)
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        if obj == self.command_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.command_cancel.emit()
                return True
            elif event.key() == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True
            elif event.key() == Qt.Key.Key_Tab:
                self._autocomplete()
                return True
        
        return super().eventFilter(obj, event)
    
    def _on_text_changed(self, text: str):
        """文本变化回调"""
        if not text.startswith('/'):
            self.suggestions_list.hide()
            self.hint_label.setText("输入 / 开始搜索技能")
            return
        
        # 获取建议
        query = text[1:].strip()
        if not query:
            self.suggestions_list.hide()
            self.hint_label.setText("输入技能名称或关键词")
            return
        
        # 搜索技能
        self.suggestions_list.clear()
        
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
            
            # 意图匹配
            for intent in metadata.intents:
                if query in intent.lower():
                    score += 2
            
            if score > 0:
                matches.append((skill_name, metadata, score))
        
        # 按匹配度排序
        matches.sort(key=lambda x: x[2], reverse=True)
        
        # 添加到建议列表
        for skill_name, metadata, score in matches[:8]:
            icon = self._get_skill_icon(metadata.category)
            item_text = f"{icon} {metadata.display_name} - {metadata.description[:40]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, skill_name)
            self.suggestions_list.addItem(item)
        
        # 显示建议列表
        if matches:
            self.suggestions_list.show()
            self.hint_label.setText(f"找到 {len(matches)} 个匹配的技能，按 Tab 补全")
        else:
            self.suggestions_list.hide()
            self.hint_label.setText("未找到匹配的技能")
    
    def _on_execute(self):
        """执行命令"""
        command = self.command_input.text().strip()
        
        if not command:
            return
        
        # 添加到历史记录
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # 解析命令
        if command.startswith('/'):
            skill_name = command[1:].strip()
            
            # 验证技能是否存在
            skill = self.registry.get_skill(skill_name)
            if skill:
                # 执行技能
                self.command_execute.emit(skill_name, {})
                self.command_input.clear()
                self.suggestions_list.hide()
            else:
                # 尝试模糊匹配
                self._fuzzy_execute(skill_name)
        else:
            # 普通命令
            self.command_execute.emit("chat", {"message": command})
            self.command_input.clear()
            self.suggestions_list.hide()
    
    def _on_suggestion_clicked(self, item):
        """点击建议项"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name:
            self.command_input.setText(f"/{skill_name}")
    
    def _on_suggestion_double_clicked(self, item):
        """双击建议项"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name:
            self.command_execute.emit(skill_name, {})
            self.command_input.clear()
            self.suggestions_list.hide()
    
    def _navigate_history(self, direction: int):
        """导航历史记录"""
        if not self.command_history:
            return
        
        self.history_index += direction
        self.history_index = max(0, min(self.history_index, len(self.command_history) - 1))
        
        self.command_input.setText(self.command_history[self.history_index])
    
    def _autocomplete(self):
        """自动补全"""
        current_item = self.suggestions_list.currentItem()
        if current_item:
            skill_name = current_item.data(Qt.ItemDataRole.UserRole)
            if skill_name:
                self.command_input.setText(f"/{skill_name}")
    
    def _fuzzy_execute(self, query: str):
        """模糊匹配执行"""
        # 查找最匹配的技能
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
            self.command_execute.emit(best_match, {})
            self.command_input.clear()
            self.suggestions_list.hide()
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
    
    def show_command(self):
        """显示命令输入框"""
        self.show()
        self.command_input.setFocus()
        self.command_input.clear()
        self.suggestions_list.hide()
    
    def hide_command(self):
        """隐藏命令输入框"""
        self.hide()
        self.command_input.clear()
        self.suggestions_list.hide()


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
    
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
    
    # 创建主窗口
    window = QMainWindow()
    window.setWindowTitle("技能右键菜单测试")
    window.resize(400, 300)
    
    # 创建测试按钮
    button = QPushButton("右键点击测试")
    button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
    def show_context_menu(pos):
        menu = SkillContextMenu(registry)
        menu.show_for_text("测试文本", button.mapToGlobal(pos))
    
    button.customContextMenuRequested.connect(show_context_menu)
    window.setCentralWidget(button)
    
    window.show()
    sys.exit(app.exec())