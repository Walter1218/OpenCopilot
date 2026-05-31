#!/usr/bin/env python3
"""
对话管理器单元测试
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppt_cocreation.conversation_manager import (
    ConversationManager,
    ConversationState,
    ConversationTurn,
    ChatResponse,
    create_conversation_manager
)


def test_create_session():
    """测试创建会话"""
    print("测试创建会话...")
    
    manager = ConversationManager()
    
    # 测试自动创建 ID
    session_id = manager.create_session()
    assert session_id is not None, "应该返回会话 ID"
    assert session_id in manager.sessions, "会话应该被保存"
    
    # 测试指定 ID
    custom_id = "test_session_001"
    session_id = manager.create_session(custom_id)
    assert session_id == custom_id, "应该返回指定的 ID"
    
    # 测试初始上下文
    context = {"title": "测试"}
    session_id = manager.create_session(context=context)
    session = manager.get_session(session_id)
    assert session.context == context, "上下文应该被保存"
    
    print("✅ 创建会话通过")


def test_get_session():
    """测试获取会话"""
    print("测试获取会话...")
    
    manager = ConversationManager()
    
    # 创建会话
    session_id = manager.create_session()
    
    # 获取会话
    session = manager.get_session(session_id)
    assert session is not None, "应该返回会话"
    assert session.session_id == session_id, "会话 ID 应该匹配"
    
    # 获取不存在的会话
    session = manager.get_session("non_existent")
    assert session is None, "不存在的会话应该返回 None"
    
    print("✅ 获取会话通过")


def test_delete_session():
    """测试删除会话"""
    print("测试删除会话...")
    
    manager = ConversationManager()
    
    # 创建会话
    session_id = manager.create_session()
    assert session_id in manager.sessions, "会话应该存在"
    
    # 删除会话
    result = manager.delete_session(session_id)
    assert result == True, "应该成功删除"
    assert session_id not in manager.sessions, "会话应该被删除"
    
    # 删除不存在的会话
    result = manager.delete_session("non_existent")
    assert result == False, "删除不存在的会话应该返回 False"
    
    print("✅ 删除会话通过")


def test_process_message_greeting():
    """测试处理问候消息"""
    print("测试处理问候消息...")
    
    manager = ConversationManager()
    session_id = manager.create_session()
    
    # 测试中文问候
    response = manager.process_message(session_id, "你好")
    assert "你好" in response.response, "应该回复问候"
    
    # 测试英文问候
    response = manager.process_message(session_id, "hi")
    assert "PPT 助手" in response.response, "应该介绍自己"
    
    print("✅ 问候消息通过")


def test_process_message_help():
    """测试处理帮助请求"""
    print("测试处理帮助请求...")
    
    manager = ConversationManager()
    session_id = manager.create_session()
    
    # 测试帮助请求
    response = manager.process_message(session_id, "帮助")
    assert "转换" in response.response, "应该介绍功能"
    assert "优化" in response.response, "应该介绍功能"
    
    print("✅ 帮助请求通过")


def test_process_message_convert():
    """测试处理转换请求"""
    print("测试处理转换请求...")
    
    manager = ConversationManager()
    
    # 创建带内容的会话
    context = {
        "current_slide": {
            "content": "产品A销量100万，产品B销量200万"
        }
    }
    session_id = manager.create_session(context=context)
    
    # 测试转换请求（没有明确目标）
    response = manager.process_message(session_id, "把这个转换一下")
    
    assert response.requires_confirmation == True, "应该需要确认"
    assert response.options is not None, "应该提供选项"
    assert len(response.options) > 0, "应该有选项"
    
    print("✅ 转换请求通过")


def test_process_message_visualization():
    """测试处理可视化请求"""
    print("测试处理可视化请求...")
    
    manager = ConversationManager()
    
    # 创建带内容的会话
    context = {
        "current_slide": {
            "content": "产品A销量100万，产品B销量200万"
        }
    }
    session_id = manager.create_session(context=context)
    
    # 测试图表请求
    response = manager.process_message(session_id, "用图表展示")
    
    assert response.requires_confirmation == True, "应该需要确认"
    assert response.options is not None, "应该提供选项"
    
    print("✅ 可视化请求通过")


def test_process_message_optimize():
    """测试处理优化请求"""
    print("测试处理优化请求...")
    
    manager = ConversationManager()
    
    # 创建带内容的会话
    context = {
        "current_slide": {
            "content": "这是一段需要优化的内容"
        }
    }
    session_id = manager.create_session(context=context)
    
    # 测试优化请求
    response = manager.process_message(session_id, "优化这段内容")
    
    assert response.requires_confirmation == True, "应该需要确认"
    assert response.options is not None, "应该提供选项"
    
    print("✅ 优化请求通过")


def test_process_message_simplify():
    """测试处理精简请求"""
    print("测试处理精简请求...")
    
    manager = ConversationManager()
    
    # 创建带内容的会话
    context = {
        "current_slide": {
            "content": """
            优点：
            - 优点1
            - 优点2
            - 优点3
            - 优点4
            - 优点5
            - 优点6
            - 优点7
            - 优点8
            """
        }
    }
    session_id = manager.create_session(context=context)
    
    # 测试精简请求
    response = manager.process_message(session_id, "精简这些要点")
    
    assert response.requires_confirmation == True, "应该需要确认"
    assert response.options is not None, "应该提供选项"
    
    print("✅ 精简请求通过")


def test_process_message_general():
    """测试处理通用消息"""
    print("测试处理通用消息...")
    
    manager = ConversationManager()
    session_id = manager.create_session()
    
    # 测试通用消息
    response = manager.process_message(session_id, "我想做一个PPT")
    
    assert response.response is not None, "应该有响应"
    assert response.requires_confirmation == False, "不应该需要确认"
    
    print("✅ 通用消息通过")


def test_confirmation_flow():
    """测试确认流程"""
    print("测试确认流程...")
    
    manager = ConversationManager()
    
    # 创建带内容的会话
    context = {
        "current_slide": {
            "content": "产品A销量100万，产品B销量200万"
        }
    }
    session_id = manager.create_session(context=context)
    
    # 发送转换请求（没有明确目标）
    response = manager.process_message(session_id, "把这个转换一下")
    assert response.requires_confirmation == True, "应该需要确认"
    
    # 确认选择
    response = manager.process_message(session_id, "1")
    
    # 检查是否执行了动作
    session = manager.get_session(session_id)
    assert session.last_action is not None, "应该记录动作"
    
    print("✅ 确认流程通过")


def test_conversation_history():
    """测试对话历史"""
    print("测试对话历史...")
    
    manager = ConversationManager()
    session_id = manager.create_session()
    
    # 发送几条消息
    manager.process_message(session_id, "你好")
    manager.process_message(session_id, "帮助")
    
    # 获取历史
    history = manager.get_history(session_id)
    
    assert len(history) == 4, f"应该有4条记录（2条用户消息+2条助手响应），实际 {len(history)}"
    assert history[0]["role"] == "user", "第一条应该是用户消息"
    assert history[1]["role"] == "assistant", "第二条应该是助手响应"
    
    print("✅ 对话历史通过")


def test_clear_history():
    """测试清除历史"""
    print("测试清除历史...")
    
    manager = ConversationManager()
    session_id = manager.create_session()
    
    # 发送消息
    manager.process_message(session_id, "你好")
    
    # 清除历史
    result = manager.clear_history(session_id)
    assert result == True, "应该成功清除"
    
    # 检查历史是否被清除
    session = manager.get_session(session_id)
    assert len(session.history) == 0, "历史应该被清除"
    assert session.turn_count == 0, "轮次应该被重置"
    
    print("✅ 清除历史通过")


def test_chat_response_to_dict():
    """测试聊天响应转字典"""
    print("测试聊天响应转字典...")
    
    response = ChatResponse(
        session_id="test",
        response="测试响应",
        options=[{"id": "opt1", "text": "选项1"}],
        context_update={"key": "value"},
        requires_confirmation=True
    )
    
    result = response.to_dict()
    
    assert result["session_id"] == "test", "会话 ID 应该正确"
    assert result["response"] == "测试响应", "响应应该正确"
    assert result["options"] == [{"id": "opt1", "text": "选项1"}], "选项应该正确"
    assert result["context_update"] == {"key": "value"}, "上下文更新应该正确"
    assert result["requires_confirmation"] == True, "需要确认应该正确"
    
    print("✅ 聊天响应转字典通过")


def test_conversation_state_to_dict():
    """测试对话状态转字典"""
    print("测试对话状态转字典...")
    
    state = ConversationState(
        session_id="test",
        turn_count=5,
        last_action="convert_to_chart",
        context={"key": "value"}
    )
    
    result = state.to_dict()
    
    assert result["session_id"] == "test", "会话 ID 应该正确"
    assert result["turn_count"] == 5, "轮次应该正确"
    assert result["last_action"] == "convert_to_chart", "最后动作应该正确"
    assert result["context"] == {"key": "value"}, "上下文应该正确"
    
    print("✅ 对话状态转字典通过")


def test_convenience_function():
    """测试便捷函数"""
    print("测试便捷函数...")
    
    manager = create_conversation_manager()
    
    assert isinstance(manager, ConversationManager), "应该返回 ConversationManager 实例"
    
    print("✅ 便捷函数通过")


def main():
    """主测试函数"""
    print("=" * 60)
    print("对话管理器单元测试")
    print("=" * 60)
    
    tests = [
        test_create_session,
        test_get_session,
        test_delete_session,
        test_process_message_greeting,
        test_process_message_help,
        test_process_message_convert,
        test_process_message_visualization,
        test_process_message_optimize,
        test_process_message_simplify,
        test_process_message_general,
        test_confirmation_flow,
        test_conversation_history,
        test_clear_history,
        test_chat_response_to_dict,
        test_conversation_state_to_dict,
        test_convenience_function,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_func.__name__} 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 错误: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"{'='*60}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())