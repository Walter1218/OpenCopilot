#!/usr/bin/env python3
"""
技能UI集成功能演示脚本
演示技能面板、右键菜单、快捷指令等功能
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入Skill架构
from skill_architecture import SkillRegistry, SkillContext
from skill_architecture.coding_skill import CodingSkill
from skill_architecture.knowledge_skill import KnowledgeSkill
from skill_architecture.ppt_skill import PPTSkill
from skill_architecture.evaluation_skill import EvaluationSkill
from skill_architecture.file_skill import FileSkill
from skill_architecture.format_skill import FormatSkill
from skill_architecture.persona_skill import PersonaSkill

# 导入UI组件
from widgets.skill_panel import SkillPanel, SkillSearchWidget, SkillCommandParser
from widgets.skill_context_menu import SkillContextMenu, SkillCommandWidget
from widgets.skill_search_dialog import SkillSearchDialog, SkillQuickAccessWidget


class DemoWindow(QMainWindow):
    """演示窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("技能UI集成演示")
        self.resize(1000, 700)
        
        # 初始化Skill注册表
        self.registry = SkillRegistry()
        self._init_skills()
        
        # 设置UI
        self._setup_ui()
        
        # 设置快捷键
        self._setup_shortcuts()
    
    def _init_skills(self):
        """初始化所有Skill"""
        try:
            skills = [
                CodingSkill(),
                KnowledgeSkill(),
                PPTSkill(),
                EvaluationSkill(),
                FileSkill(),
                FormatSkill(),
                PersonaSkill()
            ]
            
            for skill in skills:
                self.registry.register(skill)
                print(f"[注册] {skill.metadata.display_name}")
            
            print(f"[完成] 共注册 {len(skills)} 个技能")
            
        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title = QLabel("🎯 技能UI集成功能演示")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            margin: 20px;
            color: #2c3e50;
        """)
        layout.addWidget(title)
        
        # 说明
        desc = QLabel("""
        <b>功能演示：</b><br>
        • <b>技能面板</b>：点击"打开技能面板"按钮查看所有技能<br>
        • <b>技能搜索</b>：按 Ctrl+K 打开技能搜索对话框<br>
        • <b>快捷指令</b>：在文本框中输入 /coding 等命令<br>
        • <b>右键菜单</b>：在文本框中选中文本后右键点击<br>
        """)
        desc.setStyleSheet("""
            font-size: 14px;
            color: #34495e;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 10px;
        """)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 按钮区域
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        # 技能面板按钮
        panel_btn = QPushButton("📋 打开技能面板")
        panel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        panel_btn.clicked.connect(self._show_skill_panel)
        btn_layout.addWidget(panel_btn)
        
        # 技能搜索按钮
        search_btn = QPushButton("🔍 打开技能搜索 (Ctrl+K)")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        search_btn.clicked.connect(self._show_skill_search)
        btn_layout.addWidget(search_btn)
        
        # 命令演示按钮
        cmd_btn = QPushButton("⌨️ 演示命令输入 (Ctrl+/)")
        cmd_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        cmd_btn.clicked.connect(self._show_command_demo)
        btn_layout.addWidget(cmd_btn)
        
        layout.addLayout(btn_layout)
        
        # 文本编辑区域
        text_label = QLabel("📝 文本编辑区域（右键点击测试菜单）：")
        text_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(text_label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText("""这是一段示例文本，您可以：

1. 选中文本后右键点击，查看技能推荐菜单
2. 输入 /coding 命令执行编程技能
3. 输入 /knowledge:query 查询知识库
4. 输入 /ppt:generate 生成PPT

试试看吧！""")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #dcdde1;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.text_edit)
        
        # 状态栏
        self.status_label = QLabel("就绪 | 按 Ctrl+K 搜索技能，Ctrl+/ 输入命令")
        self.status_label.setStyleSheet("""
            font-size: 12px;
            color: #7f8c8d;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 4px;
        """)
        layout.addWidget(self.status_label)
        
        # 初始化技能搜索对话框
        self.skill_search_dialog = SkillSearchDialog(self.registry)
        self.skill_search_dialog.skill_execute.connect(self._on_skill_execute)
        
        # 初始化命令解析器
        self.command_parser = SkillCommandParser(self.registry)
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+K 打开技能搜索
        search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        search_shortcut.activated.connect(self._show_skill_search)
        
        # Ctrl+/ 打开命令输入
        command_shortcut = QShortcut(QKeySequence("Ctrl+/"), self)
        command_shortcut.activated.connect(self._show_command_demo)
    
    def _show_skill_panel(self):
        """显示技能面板"""
        try:
            # 创建技能面板窗口
            panel_window = QMainWindow()
            panel_window.setWindowTitle("技能面板")
            panel_window.resize(1000, 600)
            
            # 创建技能面板
            panel = SkillPanel(self.registry)
            panel.skill_execute.connect(self._on_skill_execute)
            
            panel_window.setCentralWidget(panel)
            panel_window.show()
            
            self.status_label.setText("✅ 技能面板已打开")
            
        except Exception as e:
            self.status_label.setText(f"❌ 打开技能面板失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_skill_search(self):
        """显示技能搜索"""
        try:
            self.skill_search_dialog.show_dialog()
            self.status_label.setText("✅ 技能搜索对话框已打开")
            
        except Exception as e:
            self.status_label.setText(f"❌ 打开技能搜索失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_command_demo(self):
        """显示命令演示"""
        try:
            # 切换到文本编辑框并清空
            self.text_edit.setFocus()
            self.text_edit.clear()
            self.text_edit.setPlainText("""请输入技能命令，例如：

/coding - 执行编程技能
/knowledge:query - 查询知识库
/ppt:generate - 生成PPT
/evaluation - 执行评估技能
/file - 执行文件技能
/format - 执行格式转换技能
/persona - 执行角色技能

输入命令后按 Enter 执行。""")
            
            self.status_label.setText("✅ 命令演示已启动，请在文本框中输入命令")
            
        except Exception as e:
            self.status_label.setText(f"❌ 命令演示失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        try:
            selected_text = self.text_edit.textCursor().selectedText()
            
            # 创建右键菜单
            menu = SkillContextMenu(self.registry, self)
            menu.skill_execute.connect(self._on_skill_execute)
            
            # 显示菜单
            menu.show_for_text(selected_text, self.text_edit.mapToGlobal(position), {
                "source": "demo_text_edit"
            })
            
            self.status_label.setText("✅ 右键菜单已显示")
            
        except Exception as e:
            self.status_label.setText(f"❌ 显示右键菜单失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_skill_execute(self, skill_name: str, params: dict):
        """技能执行回调"""
        self.status_label.setText(f"🎯 正在执行技能: {skill_name}")
        
        # 显示执行信息
        QMessageBox.information(
            self,
            "技能执行",
            f"正在执行技能: {skill_name}\n\n参数: {params}"
        )
        
        self.status_label.setText(f"✅ 技能 {skill_name} 执行完成")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建演示窗口
    window = DemoWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()