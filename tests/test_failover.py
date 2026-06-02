"""
Provider 故障转移功能测试

测试故障转移 Provider 的各项功能：
1. 初始化
2. 故障检测
3. 自动切换
4. 状态查询
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

# 导入被测试模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_provider import (
    BaseProvider,
    MiniMaxProvider,
    LocalProvider,
    ASUCustomAgentClient,
    FailoverProvider,
    ProviderFactoryWithFailover
)


class MockProvider(BaseProvider):
    """模拟 Provider"""
    
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0
    
    def stream_chat(self, prompt: str, system_prompt: str = ""):
        self.call_count += 1
        if self.should_fail:
            raise Exception(f"{self.name} 故障")
        yield f"[{self.name}] 响应: {prompt}"
    
    def stream_chat_with_history(self, messages: list):
        self.call_count += 1
        if self.should_fail:
            raise Exception(f"{self.name} 故障")
        last_msg = messages[-1]["content"] if messages else ""
        yield f"[{self.name}] 响应: {last_msg}"


class TestFailoverProvider:
    """故障转移 Provider 测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        providers = [
            ("provider1", MockProvider("provider1")),
            ("provider2", MockProvider("provider2"))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        assert len(failover.providers) == 2
        assert failover.current_index == 0
        assert failover.providers[0][0] == "provider1"
        assert failover.providers[1][0] == "provider2"
    
    def test_stream_chat_success(self):
        """测试成功调用"""
        providers = [
            ("provider1", MockProvider("provider1")),
            ("provider2", MockProvider("provider2"))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        # 测试流式调用
        chunks = list(failover.stream_chat("测试消息"))
        
        assert len(chunks) > 0
        assert "provider1" in chunks[0]
        assert failover.failure_counts[0] == 0
    
    def test_stream_chat_failure_and_failover(self):
        """测试故障和故障转移"""
        providers = [
            ("provider1", MockProvider("provider1", should_fail=True)),
            ("provider2", MockProvider("provider2", should_fail=False))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        # 测试流式调用（provider1 会失败）
        chunks = list(failover.stream_chat("测试消息"))
        
        # 应该包含故障转移消息
        has_failover_message = any("[Failover]" in chunk for chunk in chunks)
        assert has_failover_message
        
        # 应该切换到 provider2
        assert failover.current_index == 1
    
    def test_stream_chat_all_fail(self):
        """测试所有 Provider 都失败"""
        providers = [
            ("provider1", MockProvider("provider1", should_fail=True)),
            ("provider2", MockProvider("provider2", should_fail=True))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        # 测试流式调用（所有 Provider 都失败）
        chunks = list(failover.stream_chat("测试消息"))
        
        # 应该包含所有 Provider 都失败的消息
        has_all_fail_message = any("所有 Provider 都失败" in chunk for chunk in chunks)
        assert has_all_fail_message
    
    def test_stream_chat_with_history(self):
        """测试带历史的流式调用"""
        providers = [
            ("provider1", MockProvider("provider1")),
            ("provider2", MockProvider("provider2"))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
            {"role": "user", "content": "测试消息"}
        ]
        
        chunks = list(failover.stream_chat_with_history(messages))
        
        assert len(chunks) > 0
        assert "provider1" in chunks[0]
    
    def test_get_status(self):
        """测试获取状态"""
        providers = [
            ("provider1", MockProvider("provider1")),
            ("provider2", MockProvider("provider2"))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        status = failover.get_status()
        
        assert "current_provider" in status
        assert "providers" in status
        assert "total_providers" in status
        assert status["current_provider"] == "provider1"
        assert status["total_providers"] == 2
        assert len(status["providers"]) == 2
    
    def test_switch_to_next(self):
        """测试切换到下一个 Provider"""
        providers = [
            ("provider1", MockProvider("provider1")),
            ("provider2", MockProvider("provider2")),
            ("provider3", MockProvider("provider3"))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        # 初始状态
        assert failover.current_index == 0
        
        # 切换到下一个
        failover._switch_to_next()
        assert failover.current_index == 1
        
        # 再切换
        failover._switch_to_next()
        assert failover.current_index == 2
        
        # 循环回到第一个
        failover._switch_to_next()
        assert failover.current_index == 0
    
    def test_failure_count_reset(self):
        """测试失败计数重置"""
        providers = [
            ("provider1", MockProvider("provider1")),
            ("provider2", MockProvider("provider2"))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        # 模拟失败
        failover._record_failure()
        assert failover.failure_counts[0] == 1
        
        # 成功后重置
        failover._record_success()
        assert failover.failure_counts[0] == 0


class TestProviderFactoryWithFailover:
    """带故障转移的 Provider 工厂测试类"""
    
    def test_create_provider_with_failover(self):
        """测试创建带故障转移的 Provider"""
        with patch('llm_provider.load_config') as mock_config:
            mock_config.return_value = {
                "failover": {"enabled": True}
            }
            
            provider = ProviderFactoryWithFailover.create_provider(use_failover=True)
            
            assert isinstance(provider, FailoverProvider)
    
    def test_create_provider_without_failover(self):
        """测试创建不带故障转移的 Provider"""
        provider = ProviderFactoryWithFailover.create_provider(use_failover=False)
        
        assert isinstance(provider, ASUCustomAgentClient)
    
    def test_create_provider_failover_disabled(self):
        """测试故障转移禁用时创建 Provider"""
        with patch('llm_provider.load_config') as mock_config:
            mock_config.return_value = {
                "failover": {"enabled": False}
            }
            
            provider = ProviderFactoryWithFailover.create_provider(use_failover=True)
            
            assert isinstance(provider, ASUCustomAgentClient)


class TestFailoverIntegration:
    """故障转移集成测试类"""
    
    @pytest.mark.asyncio
    async def test_failover_with_real_providers(self):
        """测试故障转移与真实 Provider（模拟）"""
        # 创建模拟的 Provider
        provider1 = MockProvider("minimax", should_fail=True)
        provider2 = MockProvider("local", should_fail=False)
        
        providers = [
            ("minimax", provider1),
            ("local", provider2)
        ]
        
        failover = FailoverProvider(providers=providers)
        
        # 测试故障转移
        chunks = []
        for chunk in failover.stream_chat("测试消息"):
            chunks.append(chunk)
        
        # 应该成功获取到 provider2 的响应
        assert any("local" in chunk for chunk in chunks)
        
        # provider1 应该被调用过
        assert provider1.call_count == 1
        
        # provider2 应该被调用过
        assert provider2.call_count == 1
    
    def test_multiple_failovers(self):
        """测试多次故障转移"""
        providers = [
            ("provider1", MockProvider("provider1", should_fail=True)),
            ("provider2", MockProvider("provider2", should_fail=True)),
            ("provider3", MockProvider("provider3", should_fail=False))
        ]
        
        failover = FailoverProvider(providers=providers)
        
        # 测试流式调用
        chunks = list(failover.stream_chat("测试消息"))
        
        # 应该成功获取到 provider3 的响应
        assert any("provider3" in chunk for chunk in chunks)
        
        # 应该切换到了 provider3
        assert failover.current_index == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])