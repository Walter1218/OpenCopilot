"""
ConfigManager 配置管理器测试
"""
import pytest
import os



class TestConfigManager:
    """配置管理"""

    @pytest.fixture
    def cfg(self):
        from config_manager import ConfigManager
        return ConfigManager.get_instance()

    def test_singleton(self, cfg):
        from config_manager import ConfigManager
        assert ConfigManager.get_instance() is cfg

    def test_get_agent(self, cfg):
        agent = cfg.get_agent()
        assert "max_turns" in agent
        assert isinstance(agent["max_turns"], int)

    def test_get_llm(self, cfg):
        llm = cfg.get_llm()
        assert "temperature" in llm

    def test_get_concurrency(self, cfg):
        conc = cfg.get_concurrency()
        assert "chat" in conc

    def test_get_web_search(self, cfg):
        ws = cfg.get_web_search()
        assert "enabled" in ws
        assert "limit" in ws

    def test_get_agent_runtime_defaults(self, cfg):
        runtime = cfg.get_agent_runtime()
        assert runtime["default_backend"] == "self_agent"
        assert runtime["default_provider"] == "self_agent"
        assert runtime["default_model"] == "default"
        assert isinstance(runtime["capability_routes"], dict)
        assert runtime["fallback_policy"]["enabled"] is False

    def test_get_agent_runtime_override(self, cfg):
        original = cfg.get_raw()
        cfg._config["agent_runtime"] = {
            "default_backend": "self_agent",
            "default_provider": "self_agent",
            "capability_routes": {
                "ppt": {
                    "backend": "vnext_provider",
                    "provider": "hermes_local",
                }
            },
            "fallback_policy": {
                "enabled": True,
                "on_timeout": "self_agent",
                "on_protocol_error": "",
            }
        }
        runtime = cfg.get_agent_runtime()
        assert runtime["default_backend"] == "self_agent"
        assert runtime["default_provider"] == "self_agent"
        assert runtime["capability_routes"]["ppt"]["backend"] == "vnext_provider"
        assert runtime["fallback_policy"]["enabled"] is True
        assert runtime["fallback_policy"]["on_timeout"] == "self_agent"
        assert runtime["fallback_policy"]["on_protocol_error"] == ""
        cfg._config = original

    def test_default_agent_values(self, cfg):
        agent = cfg.get_agent()
        assert agent["max_turns"] >= 1

    def test_reload(self, cfg):
        original = cfg.get_agent()
        cfg.reload()
        assert cfg.get_agent()["max_turns"] == original["max_turns"]
