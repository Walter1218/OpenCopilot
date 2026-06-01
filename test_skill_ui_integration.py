#!/usr/bin/env python3
"""
技能UI集成功能测试脚本
测试技能面板、右键菜单、快捷指令等功能
"""

import sys
import os
import asyncio
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt, QTimer

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


class TestWindow(QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("技能UI集成测试")
        self.resize(800, 600)
        
        # 初始化Skill注册表
        self.registry = SkillRegistry()
        self._init_skills()
        
        # 设置UI
        self._setup_ui()
    
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
        title = QLabel("技能UI集成测试")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # 测试按钮
        test_panel_btn = QPushButton("测试技能面板")
        test_panel_btn.clicked.connect(self._test_skill_panel)
        layout.addWidget(test_panel_btn)
        
        test_search_btn = QPushButton("测试技能搜索对话框")
        test_search_btn.clicked.connect(self._test_skill_search)
        layout.addWidget(test_search_btn)
        
        test_context_btn = QPushButton("测试右键菜单")
        test_context_btn.clicked.connect(self._test_context_menu)
        layout.addWidget(test_context_btn)
        
        test_command_btn = QPushButton("测试命令解析器")
        test_command_btn.clicked.connect(self._test_command_parser)
        layout.addWidget(test_command_btn)
        
        # 结果显示
        self.result_label = QLabel("测试结果将显示在这里")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.result_label)
        
        layout.addStretch()
    
    def _test_skill_panel(self):
        """测试技能面板"""
        try:
            # 创建技能面板窗口
            panel_window = QMainWindow()
            panel_window.setWindowTitle("技能面板测试")
            panel_window.resize(1000, 600)
            
            # 创建技能面板
            panel = SkillPanel(self.registry)
            panel.skill_execute.connect(lambda name, params: self._on_skill_execute(name, params))
            
            panel_window.setCentralWidget(panel)
            panel_window.show()
            
            self.result_label.setText("✅ 技能面板测试窗口已打开")
            
        except Exception as e:
            self.result_label.setText(f"❌ 技能面板测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _test_skill_search(self):
        """测试技能搜索对话框"""
        try:
            # 创建搜索对话框
            dialog = SkillSearchDialog(self.registry)
            dialog.skill_execute.connect(lambda name, params: self._on_skill_execute(name, params))
            dialog.show_dialog()
            
            self.result_label.setText("✅ 技能搜索对话框已打开")
            
        except Exception as e:
            self.result_label.setText(f"❌ 技能搜索对话框测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _test_context_menu(self):
        """测试右键菜单"""
        try:
            # 创建右键菜单
            menu = SkillContextMenu(self.registry)
            menu.skill_execute.connect(lambda name, params: self._on_skill_execute(name, params))
            
            # 模拟显示菜单
            test_text = "这是一段测试文本"
            menu.show_for_text(test_text, self.mapToGlobal(self.rect().center()), {
                "source": "test"
            })
            
            self.result_label.setText("✅ 右键菜单测试已启动（请查看弹出菜单）")
            
        except Exception as e:
            self.result_label.setText(f"❌ 右键菜单测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _test_command_parser(self):
        """测试命令解析器"""
        try:
            # 创建命令解析器
            parser = SkillCommandParser(self.registry)
            
            # 测试命令解析
            test_commands = [
                "/coding",
                "/knowledge:query",
                "/ppt:generate param1=value1",
                "/evaluation",
                "/file",
                "/format",
                "/persona",
                "/unknown_skill"
            ]
            
            results = []
            for cmd in test_commands:
                result = parser.parse(cmd)
                if result:
                    results.append(f"✅ {cmd} -> {result['skill_name']}")
                else:
                    results.append(f"❌ {cmd} -> 解析失败")
            
            self.result_label.setText("命令解析测试结果:\n" + "\n".join(results))
            
        except Exception as e:
            self.result_label.setText(f"❌ 命令解析器测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_skill_execute(self, skill_name: str, params: dict):
        """技能执行回调"""
        self.result_label.setText(f"🎯 技能执行: {skill_name}\n参数: {params}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = TestWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()