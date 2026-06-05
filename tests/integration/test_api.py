"""
API 集成测试
"""
import pytest
import os
import tempfile


from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from smart_copilot_api import app
    return TestClient(app)


class TestHealthEndpoints:
    """健康检查"""

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_system_status(self, client):
        r = client.get("/api/system/status")
        assert r.status_code in (200, 503)


class TestConfigEndpoints:
    """配置"""

    def test_get_config(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200
        assert "provider_type" in r.json()


class TestAgentEndpoints:
    """Agent"""

    def test_sessions(self, client):
        r = client.get("/v1/agent/sessions")
        assert r.status_code == 200
        assert "sessions" in r.json()


class TestFileEndpoints:
    """文件操作"""

    def test_read_file(self, client):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello API test")
            path = f.name
        try:
            r = client.post("/api/file/read", json={"file_path": path, "format": "text"})
            assert r.status_code == 200
        finally:
            os.unlink(path)


class TestKnowledgeEndpoints:
    """知识图谱"""

    def test_statistics(self, client):
        r = client.get("/api/knowledge/statistics")
        assert r.status_code in (200, 503)
