import sys
import os
import shutil
import tempfile
import time
from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from smart_copilot import AICardWindow, AIWorker
from persona_manager import PersonaManager

def test_smart_copilot_ui_methods():
    print("==============================================")
    print("  集成测试: SmartCopilot UI 按钮点击逻辑验证  ")
    print("==============================================\n")
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    temp_dir = tempfile.mkdtemp(prefix="open_copilot_test_ui_methods_")
    print(f"[1] 创建沙盒: {temp_dir}")
    
    try:
        # 初始化主窗口
        from llm_provider import ProviderFactory
        provider = ProviderFactory.create_provider()
        window = AICardWindow(provider)
        
        # 验证按钮存在
        print("[2] 验证角色工坊按钮存在...")
        assert hasattr(window, 'btn_persona')
        assert isinstance(window.btn_persona, QPushButton)
        
        print("[3] 验证设置按钮存在...")
        assert hasattr(window, 'btn_settings')
        assert isinstance(window.btn_settings, QPushButton)
        
        # 验证方法存在
        print("[4] 验证方法挂载...")
        assert hasattr(window, 'open_persona_workshop')
        assert hasattr(window, 'open_settings')
        
        print("[5] 验证 AIWorker 参数兼容性...")
        worker = AIWorker(
            provider, "test prompt", "custom", "test_session",
            context_source="vision", context_meta={}, context_envelope={},
            image_base64="dummy_base64_data"
        )
        assert worker.image_base64 == "dummy_base64_data"
        
        print("\n[✓] SmartCopilot UI 方法验证通过！没有属性缺失。")
        
    finally:
        print(f"[6] 清理沙盒...")
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_smart_copilot_ui_methods()