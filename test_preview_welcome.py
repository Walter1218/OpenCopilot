"""
测试PPT预览区默认欢迎幻灯片显示
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from opencopilot.capabilities.ppt.preview_panel import SlideRenderer


def test_welcome_slide():
    """测试默认欢迎幻灯片显示"""
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = QMainWindow()
    window.setWindowTitle("PPT预览区欢迎幻灯片测试")
    window.setGeometry(100, 100, 800, 600)
    
    # 创建中央部件
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # 创建SlideRenderer实例
    renderer = SlideRenderer()
    layout.addWidget(renderer)
    
    # 不设置任何幻灯片数据，测试默认欢迎幻灯片
    # renderer.set_slide() 不调用，保持current_slide为None
    
    window.setCentralWidget(central_widget)
    window.show()
    
    print("测试窗口已显示，请检查PPT预览区是否显示欢迎幻灯片")
    print("欢迎幻灯片应该显示：")
    print("1. 标题：OpenCopilot PPT 共创工作台")
    print("2. 副标题：欢迎使用 — 请上传文档或输入主题开始创建")
    print("3. 提示信息：点击左侧 AI 助手开始对话，或使用右侧工具栏")
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    test_welcome_slide()