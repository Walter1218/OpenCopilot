import os
import shutil
import tempfile
from persona_manager import PersonaManager

def test_persona_manager():
    print("==============================================")
    print("  单元测试: PersonaManager 数据层 (无 Mock)  ")
    print("==============================================\n")
    
    # 1. 创建真实的临时目录
    temp_dir = tempfile.mkdtemp(prefix="open_copilot_test_personas_")
    print(f"[1] 创建测试目录: {temp_dir}")
    
    try:
        manager = PersonaManager(base_dir=temp_dir)
        
        # 2. 初始状态应该为空
        print("[2] 检查初始列表...")
        assert len(manager.list_personas()) == 0, "初始目录应该为空"
        
        # 3. 创建 Persona
        print("[3] 新建自定义 Persona...")
        success = manager.save_persona("test_persona", "You are a test persona.")
        assert success is True
        
        # 4. 创建嵌套 Persona
        print("[4] 新建嵌套 Persona...")
        manager.save_persona("custom/deep_test", "Nested content.")
        
        # 5. 读取并验证列表
        print("[5] 验证读取与列表...")
        personas = manager.list_personas()
        assert len(personas) == 2
        assert "test_persona" in personas
        assert "custom/deep_test" in personas
        
        content1 = manager.get_persona("test_persona")
        assert content1 == "You are a test persona."
        
        content2 = manager.get_persona("custom/deep_test")
        assert content2 == "Nested content."
        
        # 6. 删除测试
        print("[6] 验证删除...")
        success, msg = manager.delete_persona("test_persona")
        assert success is True
        assert len(manager.list_personas()) == 1
        
        # 7. 内置拦截测试
        print("[7] 验证内置角色保护...")
        success, msg = manager.delete_persona("default")
        assert success is False
        assert "内置角色无法删除" in msg
        
        print("\n[✓] PersonaManager 数据层单元测试通过！")
        
    finally:
        # 8. 清理临时目录
        print(f"[8] 清理测试目录...")
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_persona_manager()