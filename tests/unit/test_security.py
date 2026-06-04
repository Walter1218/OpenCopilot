"""
安全模块测试
"""
import pytest
import os



class TestSecurityConfig:
    """安全配置"""

    def test_default(self):
        from opencopilot.safety.security import SecurityConfig
        c = SecurityConfig()
        assert c.enable_rate_limiting is True
        assert c.enable_audit_logging is True

    def test_custom(self):
        from opencopilot.safety.security import SecurityConfig
        c = SecurityConfig(enable_rate_limiting=False, enable_audit_logging=False)
        assert c.enable_rate_limiting is False


class TestRateLimiter:
    """速率限制器"""

    def test_init(self):
        from opencopilot.safety.security import RateLimiter
        limiter = RateLimiter()
        assert limiter is not None

    def test_add_and_check_rule(self):
        from opencopilot.safety.security import RateLimiter
        from opencopilot.safety.security.models import RateLimitRule
        limiter = RateLimiter()
        rule = RateLimitRule(
            rule_id="rule-1", resource="api", action="chat",
            max_requests=100, time_window=60.0,
        )
        limiter.add_rule(rule)
        result = limiter.check_rate_limit("test_user", "api", "chat")
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)


class TestSecurityModule:
    """安全模块"""

    @pytest.fixture
    def security(self):
        from opencopilot.safety.security import SecurityModule
        return SecurityModule()

    def test_init(self, security):
        assert security is not None
        assert security.config.enable_rate_limiting is True

    @pytest.mark.asyncio
    async def test_check_permission(self, security):
        result = await security.check_permission(
            user_id="test_user", resource="file", action="read",
        )
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_validate_input(self, security):
        result = await security.validate_input(
            input_data={"name": "test"},
            schema={"required": ["name"], "properties": {"name": {"type": "string"}}}
        )
        assert result.valid is True
