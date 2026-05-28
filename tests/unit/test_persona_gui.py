import sys
import os
import shutil
import tempfile
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from persona_gui import PersonaManagerDialog
from persona_manager import PersonaManager

def test_persona_gui():
    print("==============================================")
    print("  模块测试: PersonaManager GUI (无 Mock)  ")
    print("==============================================\n")
    
    # 必须要有 QApplication 实例才能测试 PyQt 界面
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    temp_dir = tempfile.mkdtemp(prefix="open_copilot_test_gui_")
    print(f"[1] 创建 GUI 测试沙盒: {temp_dir}")
    
    try:
        # 预填充一些数据
        manager = PersonaManager(base_dir=temp_dir)
        manager.save_persona("initial_test", "I am initial.")
        
        # 实例化 Dialog
        dialog = PersonaManagerDialog(base_dir=temp_dir)
        
        # 1. 验证初始化列表
        print("[2] 验证列表初始化...")
        assert dialog.list_widget.count() == 1
        assert dialog.list_widget.item(0).text() == "initial_test"
        
        # 2. 模拟点击左侧 item，验证右侧内容回显
        print("[3] 验证选中回显...")
        # 当前应该默认选中第一个
        assert dialog.input_name.text() == "initial_test"
        assert dialog.text_editor.toPlainText() == "I am initial."
        # 编辑模式下输入框只读
        assert dialog.input_name.isReadOnly() is True
        
        # 3. 模拟新建点击
        print("[4] 模拟新建操作...")
        QTest.mouseClick(dialog.btn_new, Qt.MouseButton.LeftButton)
        assert dialog.input_name.text() == ""
        assert dialog.input_name.isReadOnly() is False
        assert "你是一个有用的AI助手" in dialog.text_editor.toPlainText()
        
        # 4. 模拟输入并保存
        print("[5] 模拟键盘输入并保存...")
        # 模拟键盘输入太容易因为焦点问题闪退，这里直接 setText
        dialog.input_name.setText("gui_test_persona")
        dialog.text_editor.setPlainText("Generated from UI test.")
        
        # 模拟点击保存按钮
        QTest.mouseClick(dialog.btn_save, Qt.MouseButton.LeftButton)
        
        # 验证底层文件是否真实创建
        content = manager.get_persona("gui_test_persona")
        assert content == "Generated from UI test."
        
        # 验证 UI 列表是否刷新
        assert dialog.list_widget.count() == 2
        # 应该选中刚才新建的项
        assert dialog.list_widget.currentItem().text() == "gui_test_persona"
        assert dialog.input_name.isReadOnly() is True
        
        print("\n[✓] PersonaManager GUI 测试通过！(真实 UI 事件，无 Mock)")
        
    finally:
        print(f"[6] 清理沙盒...")
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_persona_gui()