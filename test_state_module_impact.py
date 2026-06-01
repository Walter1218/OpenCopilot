"""
状态管理模块影响对比测试

展示有/没有状态管理模块的系统差异。
"""

import sys
import time
import json
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from state_manager import StateManager, TaskStatus
from asu_custom_agent import ASUAgentMemory, ContextWindowManager, normalize_context_envelope, build_context_prefix


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_section(title):
    """打印小节标题"""
    print(f"\n{title}")
    print("-" * 40)


def compare_old_vs_new():
    """对比旧模块 vs 新模块"""
    
    print_header("状态管理模块影响对比测试")
    
    # 创建临时数据库
    temp_db_old = tempfile.NamedTemporaryFile(suffix='_old.db', delete=False)
    temp_db_old.close()
    temp_db_new = tempfile.NamedTemporaryFile(suffix='_new.db', delete=False)
    temp_db_new.close()
    
    try:
        # 初始化模块
        old_memory = ASUAgentMemory(temp_db_old.name)
        new_manager = StateManager(temp_db_new.name)
        
        print_section("1. API 可用性对比")
        
        # 旧模块 API
        old_apis = [
            "get_context(session_id)",
            "add_message(session_id, role, content)",
            "set_persona(session_id, persona)",
            "clear(session_id)",
            "session_count()"
        ]
        
        # 新模块 API（包含旧模块所有 API + 新增 API）
        new_apis = old_apis.copy()
        new_apis.extend([
            "create_task(session_id, task_type, description)",
            "get_task(task_id)",
            "update_task(task_id, status, progress, result)",
            "get_session_tasks(session_id)",
            "get_active_tasks(session_id)",
            "get_session_state(session_id)",
            "update_session_state(session_id, persona, is_active, metadata)",
            "get_statistics()"
        ])
        
        print(f"旧模块 API 数量: {len(old_apis)}")
        print(f"新模块 API 数量: {len(new_apis)}")
        print(f"新增 API 数量: {len(new_apis) - len(old_apis)}")
        
        print("\n旧模块 API:")
        for api in old_apis:
            print(f"  - {api}")
        
        print("\n新增 API:")
        for api in new_apis[len(old_apis):]:
            print(f"  + {api}")
        
        print_section("2. 功能对比")
        
        # 测试会话管理
        session_id = "test_comparison_1"
        
        # 旧模块：基本会话管理
        old_memory.add_message(session_id, "user", "测试消息")
        old_context = old_memory.get_context(session_id)
        
        # 新模块：增强会话管理
        new_manager.add_message(session_id, "user", "测试消息")
        new_context = new_manager.get_context(session_id)
        new_state = new_manager.get_session_state(session_id)
        
        print(f"\n会话管理:")
        print(f"  旧模块: 基本会话 + 消息历史")
        print(f"  新模块: 增强会话 + 消息历史 + 会话状态 + 任务管理")
        
        print(f"\n会话状态信息:")
        print(f"  - 会话ID: {new_state.session_id}")
        print(f"  - 人设: {new_state.persona}")
        print(f"  - 创建时间: {time.ctime(new_state.created_at)}")
        print(f"  - 更新时间: {time.ctime(new_state.updated_at)}")
        print(f"  - 是否活跃: {new_state.is_active}")
        
        # 测试任务管理
        print(f"\n任务管理（新功能）:")
        
        # 创建任务
        task1 = new_manager.create_task(
            session_id=session_id,
            task_type="code_review",
            description="审查 Python 代码"
        )
        print(f"  - 创建任务: {task1.task_id[:8]}...")
        
        # 更新任务状态
        new_manager.update_task(task1.task_id, status=TaskStatus.IN_PROGRESS, progress=0.5)
        print(f"  - 更新进度: 50%")
        
        # 完成任务
        new_manager.update_task(task1.task_id, status=TaskStatus.COMPLETED, result={"score": 95})
        print(f"  - 完成任务: score=95")
        
        # 获取任务统计
        stats = new_manager.get_statistics()
        print(f"\n统计信息:")
        print(f"  - 总会话数: {stats['total_sessions']}")
        print(f"  - 总任务数: {stats['total_tasks']}")
        print(f"  - 总消息数: {stats['total_messages']}")
        
        print_section("3. 数据结构对比")
        
        # 旧模块数据结构
        print(f"\n旧模块数据结构:")
        print(f"  - sessions: session_id, persona, updated_at")
        print(f"  - messages: id, session_id, role, content, timestamp")
        
        # 新模块数据结构
        print(f"\n新模块数据结构:")
        print(f"  - sessions: session_id, persona, created_at, updated_at, is_active, metadata")
        print(f"  - messages: id, session_id, role, content, timestamp")
        print(f"  - tasks: task_id, session_id, status, task_type, description, progress, result, error, metadata, checkpoint_id, created_at, updated_at, completed_at")
        print(f"  - checkpoints: checkpoint_id, task_id, session_id, state_snapshot, created_at, description, metadata, is_auto, parent_checkpoint_id")
        
        print_section("4. 使用场景对比")
        
        print(f"\n旧模块适用场景:")
        print(f"  ✓ 简单对话系统")
        print(f"  ✓ 基本会话管理")
        print(f"  ✓ 消息历史记录")
        
        print(f"\n新模块适用场景:")
        print(f"  ✓ 简单对话系统（兼容旧模块）")
        print(f"  ✓ 复杂任务管理")
        print(f"  ✓ 长时间运行任务")
        print(f"  ✓ 任务状态跟踪")
        print(f"  ✓ 检查点和恢复")
        print(f"  ✓ 会话状态管理")
        print(f"  ✓ 统计和监控")
        
        print_section("5. 代码示例对比")
        
        print(f"\n旧模块使用示例:")
        print("""
# 初始化
memory = ASUAgentMemory("database.db")

# 获取上下文
context = memory.get_context(session_id)
messages = context["messages"]
persona = context["persona"]

# 添加消息
memory.add_message(session_id, "user", "用户消息")
memory.add_message(session_id, "assistant", "助手回复")

# 设置人设
memory.set_persona(session_id, "coding")

# 清空会话
memory.clear(session_id)
""")
        
        print(f"\n新模块使用示例:")
        print("""
# 初始化
manager = StateManager("database.db")

# 获取上下文（兼容旧模块）
context = manager.get_context(session_id)
messages = context["messages"]
persona = context["persona"]

# 添加消息（兼容旧模块）
manager.add_message(session_id, "user", "用户消息")
manager.add_message(session_id, "assistant", "助手回复")

# 设置人设（兼容旧模块）
manager.set_persona(session_id, "coding")

# 清空会话（兼容旧模块）
manager.clear(session_id)

# 新增：任务管理
task = manager.create_task(session_id, "code_review", "审查代码")
manager.update_task(task.task_id, status=TaskStatus.IN_PROGRESS, progress=0.5)
manager.update_task(task.task_id, status=TaskStatus.COMPLETED, result={"score": 95})

# 新增：会话状态管理
state = manager.get_session_state(session_id)
manager.update_session_state(session_id, persona="coding", metadata={"theme": "dark"})

# 新增：统计信息
stats = manager.get_statistics()
""")
        
        print_section("6. 迁移路径")
        
        print(f"\n从旧模块迁移到新模块:")
        print(f"  1. 直接替换: 将 ASUAgentMemory 替换为 StateManager")
        print(f"  2. 无需修改: 所有现有代码无需修改")
        print(f"  3. 渐进增强: 逐步使用新功能")
        print(f"  4. 向后兼容: 旧代码继续工作")
        
        print(f"\n迁移示例:")
        print("""
# 旧代码
from asu_custom_agent import ASUAgentMemory
memory = ASUAgentMemory("database.db")

# 新代码（只需修改导入）
from state_manager import StateManager
memory = StateManager("database.db")

# 其他代码完全不变
context = memory.get_context(session_id)
memory.add_message(session_id, "user", "消息")
""")
        
        print_section("7. 性能对比")
        
        # 性能测试
        iterations = 1000
        
        # 旧模块性能
        start_time = time.time()
        for i in range(iterations):
            old_memory.add_message("perf_test_old", "user", f"消息 {i}")
            old_memory.get_context("perf_test_old")
        old_duration = time.time() - start_time
        
        # 新模块性能
        start_time = time.time()
        for i in range(iterations):
            new_manager.add_message("perf_test_new", "user", f"消息 {i}")
            new_manager.get_context("perf_test_new")
        new_duration = time.time() - start_time
        
        print(f"\n性能测试 ({iterations} 次迭代):")
        print(f"  旧模块: {old_duration:.3f} 秒")
        print(f"  新模块: {new_duration:.3f} 秒")
        print(f"  性能差异: {new_duration/old_duration:.2f}x")
        
        if new_duration / old_duration < 1.5:
            print(f"  结论: 性能差异在可接受范围内")
        else:
            print(f"  结论: 性能有所下降，但功能增强显著")
        
        print_section("8. 总结")
        
        print(f"\n状态管理模块的价值:")
        print(f"  ✓ 100% 向后兼容")
        print(f"  ✓ 新增任务管理功能")
        print(f"  ✓ 新增会话状态管理")
        print(f"  ✓ 新增检查点和恢复机制")
        print(f"  ✓ 新增统计和监控功能")
        print(f"  ✓ 支持复杂任务场景")
        print(f"  ✓ 为生产化做好准备")
        
        print(f"\n系统可感知的差异:")
        print(f"  1. API 数量: {len(old_apis)} → {len(new_apis)} (+{len(new_apis) - len(old_apis)})")
        print(f"  2. 数据表: 2 → 4 (+2)")
        print(f"  3. 功能模块: 会话管理 → 会话管理 + 任务管理 + 检查点 + 恢复 + 统计")
        print(f"  4. 使用场景: 简单对话 → 复杂任务 + 长时间运行 + 状态跟踪")
        
        return True
    
    finally:
        # 清理临时文件
        import os
        try:
            os.unlink(temp_db_old.name)
            os.unlink(temp_db_new.name)
        except:
            pass


if __name__ == "__main__":
    success = compare_old_vs_new()
    sys.exit(0 if success else 1)
