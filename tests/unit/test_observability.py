"""
可观测性模块测试
"""
import pytest
import os



class TestObservabilityConfig:
    """可观测性配置"""

    def test_default(self):
        from opencopilot.observability import ObservabilityConfig
        c = ObservabilityConfig()
        assert c.enable_tracing is True
        assert c.enable_performance_monitoring is True

    def test_custom(self):
        from opencopilot.observability import ObservabilityConfig
        c = ObservabilityConfig(
            enable_tracing=False,
            health_check_interval=60.0,
        )
        assert c.enable_tracing is False
        assert c.health_check_interval == 60.0


class TestHealthChecker:
    """健康检查"""

    def test_init(self):
        from opencopilot.observability import HealthChecker
        checker = HealthChecker()
        assert checker is not None

    @pytest.mark.asyncio
    async def test_check_health(self):
        from opencopilot.observability import HealthChecker
        checker = HealthChecker()
        status = await checker.check_health(force=True)
        assert status is not None
        assert status.status in ("healthy", "degraded", "unhealthy")


class TestObservabilityModule:
    """可观测性模块"""

    @pytest.fixture
    def obs(self):
        from opencopilot.observability import ObservabilityModule
        return ObservabilityModule()

    def test_init(self, obs):
        assert obs is not None
        assert obs.config.enable_tracing is True

    @pytest.mark.asyncio
    async def test_log(self, obs):
        entry = await obs.info("Test message", module="test")
        assert entry is not None

    @pytest.mark.asyncio
    async def test_record_metric(self, obs):
        metric = await obs.record_metric("test_metric", 42.0, unit="ms")
        assert metric is not None
