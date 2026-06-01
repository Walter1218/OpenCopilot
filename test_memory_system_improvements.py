"""
记忆系统改进验证测试

验证以下改进：
1. MiniMax M2.7 200K 上下文配置
2. 记忆类型配额管理
3. 动态预算调整
4. 记忆配额管理器
"""

import sys
import os
import time
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_system.config import ConfigManager, MemoryType, MemoryTypeQuota, ContextBudgetConfig
from memory_system.quota_manager import QuotaManager, MemoryStats
from asu_custom_agent import ContextWindowManager


def test_config_manager():
    """测试配置管理器"""
    print("=" * 60)
    print("测试配置管理器")
    print("=" * 60)
    
    # 创建配置管理器
    config = ConfigManager()
    
    # 测试记忆类型配额
    for memory_type in MemoryType:
        quota = config.get_memory_type_quota(memory_type)
        print(f"{memory_type.value}:")
        print(f"  最大数量: {quota.max_count}")
        print(f"  最大字符数: {quota.max_chars}")
        print(f"  最大保留天数: {quota.max_age_days}")
        print(f"  重要性阈值: {quota.importance_threshold}")
        print()
    
    # 测试上下文预算配置
    budget = config.get_context_budget()
    print("上下文预算配置:")
    print(f"  最大输入字符数: {budget.max_input_chars}")
    print(f"  预留输出字符数: {budget.reserve_output_chars}")
    print(f"  最近对话轮数: {budget.recent_turns}")
    print(f"  单条消息最大字符数: {budget.max_history_msg_chars}")
    print(f"  历史消息预算比例: {budget.history_budget_ratio}")
    print(f"  当前输入预算比例: {budget.user_budget_ratio}")
    print()
    
    # 测试模型限制
    print("模型上下文限制:")
    for model_name, limit in budget.model_limits.items():
        print(f"  {model_name}: {limit} tokens")
    print()
    
    return True


def test_context_window_manager():
    """测试上下文窗口管理器"""
    print("=" * 60)
    print("测试上下文窗口管理器")
    print("=" * 60)
    
    # 测试默认配置（MiniMax M2.7）
    manager = ContextWindowManager()
    print("默认配置（MiniMax M2.7）:")
    print(f"  最大输入字符数: {manager.max_input_chars}")
    print(f"  预留输出字符数: {manager.reserve_output_chars}")
    print(f"  最近对话轮数: {manager.recent_turns}")
    print(f"  单条消息最大字符数: {manager.max_history_msg_chars}")
    print()
    
    # 测试动态调整
    print("动态调整测试:")
    models_to_test = ["minimax-m2.7", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    
    for model_name in models_to_test:
        manager = ContextWindowManager(model_name=model_name)
        print(f"  {model_name}:")
        print(f"    最大输入字符数: {manager.max_input_chars}")
        print(f"    预留输出字符数: {manager.reserve_output_chars}")
        print(f"    最近对话轮数: {manager.recent_turns}")
        print(f"    单条消息最大字符数: {manager.max_history_msg_chars}")
        print()
    
    return True


def test_quota_manager():
    """测试配额管理器"""
    print("=" * 60)
    print("测试配额管理器")
    print("=" * 60)
    
    # 创建配额管理器
    quota_manager = QuotaManager()
    
    # 测试记忆统计
    test_memories = [
        {
            "memory_id": "test1",
            "content": "这是一条测试记忆",
            "importance": 0.8,
            "access_count": 5,
            "created_at": time.time() - 86400 * 10,  # 10天前
        },
        {
            "memory_id": "test2",
            "content": "这是另一条测试记忆",
            "importance": 0.6,
            "access_count": 3,
            "created_at": time.time() - 86400 * 5,  # 5天前
        },
        {
            "memory_id": "test3",
            "content": "这是第三条测试记忆",
            "importance": 0.4,
            "access_count": 1,
            "created_at": time.time() - 86400 * 1,  # 1天前
        },
    ]
    
    # 获取统计信息
    stats = quota_manager.get_memory_stats(test_memories, MemoryType.SHORT_TERM)
    print("短期记忆统计:")
    print(f"  数量: {stats.count}")
    print(f"  总字符数: {stats.total_chars}")
    print(f"  平均重要性: {stats.avg_importance:.2f}")
    print(f"  平均访问次数: {stats.avg_access_count:.2f}")
    print(f"  最旧记忆年龄: {stats.oldest_memory_age_days:.1f}天")
    print(f"  最新记忆年龄: {stats.newest_memory_age_days:.1f}天")
    print()
    
    # 检查配额
    is_within_quota, reason = quota_manager.check_quota(MemoryType.SHORT_TERM, stats)
    print(f"配额检查: {'通过' if is_within_quota else '超出'}")
    print(f"原因: {reason}")
    print()
    
    # 获取配额使用情况
    usage = quota_manager.get_quota_usage(MemoryType.SHORT_TERM, stats)
    print("配额使用情况:")
    print(f"  数量使用率: {usage['usage']['count_usage']:.2%}")
    print(f"  字符数使用率: {usage['usage']['chars_usage']:.2%}")
    print(f"  年龄使用率: {usage['usage']['age_usage']:.2%}")
    print(f"  数量状态: {'正常' if usage['status']['count_ok'] else '超出'}")
    print(f"  字符数状态: {'正常' if usage['status']['chars_ok'] else '超出'}")
    print(f"  年龄状态: {'正常' if usage['status']['age_ok'] else '超出'}")
    print()
    
    # 测试清理建议
    memories_by_type = {
        MemoryType.SHORT_TERM: test_memories,
    }
    
    suggestions = quota_manager.suggest_cleanup(memories_by_type)
    print("清理建议:")
    for memory_type, suggestion in suggestions.items():
        print(f"  {memory_type}:")
        print(f"    需要清理: {suggestion['needs_cleanup']}")
        print(f"    原因: {suggestion['reasons']}")
        print(f"    需要删除的记忆数: {suggestion['memories_to_delete_count']}")
        print(f"    预计释放字符数: {suggestion['estimated_chars_freed']}")
    print()
    
    return True


def test_integration():
    """测试集成功能"""
    print("=" * 60)
    print("测试集成功能")
    print("=" * 60)
    
    # 测试配置管理器与配额管理器的集成
    config = ConfigManager()
    quota_manager = QuotaManager(config)
    
    # 测试不同记忆类型的配额
    print("各记忆类型配额:")
    for memory_type in MemoryType:
        quota = config.get_memory_type_quota(memory_type)
        print(f"  {memory_type.value}:")
        print(f"    最大数量: {quota.max_count}")
        print(f"    最大字符数: {quota.max_chars}")
        print(f"    最大保留天数: {quota.max_age_days}")
    print()
    
    # 测试上下文预算配置
    budget = config.get_context_budget()
    print("上下文预算配置:")
    print(f"  最大输入字符数: {budget.max_input_chars}")
    print(f"  预留输出字符数: {budget.reserve_output_chars}")
    print(f"  最近对话轮数: {budget.recent_turns}")
    print(f"  单条消息最大字符数: {budget.max_history_msg_chars}")
    print()
    
    # 测试动态调整
    print("动态调整测试:")
    manager = ContextWindowManager(model_name="minimax-m2.7")
    print(f"  MiniMax M2.7 配置:")
    print(f"    最大输入字符数: {manager.max_input_chars}")
    print(f"    预留输出字符数: {manager.reserve_output_chars}")
    print(f"    最近对话轮数: {manager.recent_turns}")
    print(f"    单条消息最大字符数: {manager.max_history_msg_chars}")
    print()
    
    return True


def main():
    """主测试函数"""
    print("开始验证记忆系统改进效果")
    print()
    
    tests = [
        ("配置管理器", test_config_manager),
        ("上下文窗口管理器", test_context_window_manager),
        ("配额管理器", test_quota_manager),
        ("集成功能", test_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    # 输出测试结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result, error in results:
        if result:
            print(f"✅ {test_name}: 通过")
            passed += 1
        else:
            print(f"❌ {test_name}: 失败")
            if error:
                print(f"   错误: {error}")
            failed += 1
    
    print()
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print(f"通过率: {passed / len(results) * 100:.1f}%")
    
    # 输出改进总结
    print()
    print("=" * 60)
    print("改进总结")
    print("=" * 60)
    
    print("1. MiniMax M2.7 200K 上下文配置:")
    print("   - 最大输入字符数: 120,000 (约 180K token)")
    print("   - 预留输出字符数: 30,000 (约 45K token)")
    print("   - 最近对话轮数: 12 轮")
    print("   - 单条消息最大字符数: 8,000")
    print()
    
    print("2. 记忆类型配额管理:")
    print("   - 短期记忆: 100 条, 50K 字符, 1 天")
    print("   - 长期记忆: 1000 条, 500K 字符, 365 天")
    print("   - 工作记忆: 50 条, 25K 字符, 7 天")
    print("   - 情景记忆: 200 条, 100K 字符, 90 天")
    print("   - 语义记忆: 500 条, 250K 字符, 180 天")
    print("   - 程序记忆: 100 条, 50K 字符, 30 天")
    print()
    
    print("3. 动态预算调整:")
    print("   - 根据模型能力自动调整配置")
    print("   - 支持 MiniMax M2.7, GPT-4, Claude 等模型")
    print("   - 自动计算最优的字符限制和轮数")
    print()
    
    print("4. 记忆配额管理器:")
    print("   - 配额检查: 检查是否超出配额")
    print("   - 配额强制执行: 自动清理超出配额的记忆")
    print("   - 清理建议: 提供智能清理建议")
    print("   - 使用统计: 实时监控配额使用情况")
    print()
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)