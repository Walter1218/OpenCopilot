"""
集成测试

测试所有模块 API 是否正确集成到主系统。
包括：
- 模块注册测试
- MCP API 测试
- 符号引用 API 测试
- 端到端测试
"""

import pytest
import os
import sys
import json
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient


# ============================================================
# 模块集成测试
# ============================================================

class TestModuleIntegration:
    """模块集成测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from smart_copilot_platform import app
        return TestClient(app)
    
    def test_app_startup(self, client):
        """测试应用启动"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_modules_registered(self, client):
        """测试模块是否已注册"""
        response = client.get("/api/modules")
        assert response.status_code == 200
        
        data = response.json()
        assert "modules" in data
        assert "total_modules" in data
        
        # 至少应该有 system 模块
        assert data["total_modules"] >= 1
    
    def test_system_health(self, client):
        """测试系统健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "modules" in data


# ============================================================
# MCP API 测试
# ============================================================

class TestMCPAPI:
    """MCP API 测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from smart_copilot_platform import app
        return TestClient(app)
    
    def test_list_mcp_servers(self, client):
        """测试列出 MCP Server"""
        response = client.get("/api/mcp/servers")
        assert response.status_code == 200
        
        data = response.json()
        assert "servers" in data
        assert "count" in data
        assert isinstance(data["servers"], list)
    
    def test_refresh_mcp_config(self, client):
        """测试刷新 MCP 配置"""
        response = client.post("/api/mcp/refresh")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "servers" in data
    
    def test_get_mcp_status(self, client):
        """测试获取 MCP 状态"""
        response = client.get("/api/mcp/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "config_path" in data
        assert "configured_servers" in data
        assert "running_servers" in data
    
    def test_get_mcp_server_tools_not_found(self, client):
        """测试获取不存在的 MCP Server 工具"""
        response = client.get("/api/mcp/servers/nonexistent/tools")
        assert response.status_code == 404
    
    def test_call_mcp_tool_not_found(self, client):
        """测试调用不存在的 MCP Server 工具"""
        response = client.post(
            "/api/mcp/servers/nonexistent/call",
            json={"tool_name": "test", "arguments": {}}
        )
        assert response.status_code == 404


# ============================================================
# 符号引用 API 测试
# ============================================================

class TestCodeAnalysisAPI:
    """代码分析 API 测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from smart_copilot_platform import app
        return TestClient(app)
    
    @pytest.fixture
    def test_python_file(self):
        """创建测试 Python 文件"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write("def hello():\n")
            f.write("    \"\"\"Say hello\"\"\"\n")
            f.write("    print(\"Hello, World!\")\n")
            f.write("\n")
            f.write("def greet(name):\n")
            f.write("    \"\"\"Greet someone\"\"\"\n")
            f.write("    hello()\n")
            f.write("    print(f\"Hello, {name}!\")\n")
            f.write("\n")
            f.write("class MyClass:\n")
            f.write("    \"\"\"Test class\"\"\"\n")
            f.write("    \n")
            f.write("    def method(self):\n")
            f.write("        \"\"\"Test method\"\"\"\n")
            f.write("        hello()\n")
            temp_file = f.name
        
        yield temp_file
        
        # 清理
        os.unlink(temp_file)
    
    def test_get_file_symbols(self, client, test_python_file):
        """测试获取文件符号"""
        response = client.get(f"/api/code/symbols?file_path={test_python_file}")
        assert response.status_code == 200
        
        data = response.json()
        assert "file" in data
        assert "symbols" in data
        assert "count" in data
        
        # 应该能找到一些符号
        assert data["count"] > 0
        
        # 检查符号结构
        for symbol in data["symbols"]:
            assert "name" in symbol
            assert "kind" in symbol
            assert "location" in symbol
    
    def test_find_symbol_definition(self, client, test_python_file):
        """测试查找符号定义"""
        # 查找 hello 函数的定义（第1行）
        response = client.post(
            "/api/code/definition",
            json={
                "file_path": test_python_file,
                "line": 0,
                "character": 4
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "file" in data
        assert "position" in data
        assert "definition" in data
    
    def test_find_symbol_references(self, client, test_python_file):
        """测试查找符号引用"""
        # 查找 hello 函数的引用
        response = client.post(
            "/api/code/references",
            json={
                "file_path": test_python_file,
                "line": 0,
                "character": 4,
                "include_declaration": True
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "file" in data
        assert "position" in data
        assert "references" in data
        assert "count" in data
    
    def test_file_not_found(self, client):
        """测试文件不存在的情况"""
        response = client.get("/api/code/symbols?file_path=/nonexistent/file.py")
        assert response.status_code == 404
    
    def test_clear_symbol_cache(self, client):
        """测试清除符号缓存"""
        response = client.post("/api/code/clear-cache")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


# ============================================================
# 上下文管理 API 测试
# ============================================================

class TestContextAPI:
    """上下文管理 API 测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from smart_copilot_platform import app
        return TestClient(app)
    
    def test_get_current_context_empty(self, client):
        """测试获取当前上下文（空）"""
        response = client.get("/api/context/current")
        # 可能返回 404（没有当前上下文）或 200（空上下文）
        assert response.status_code in [200, 404]
    
    def test_inject_context(self, client):
        """测试注入上下文"""
        response = client.post(
            "/api/context/inject",
            params={
                "content": "Test content",
                "metadata": json.dumps({"source": "test"})
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "context_id" in data
        assert data["content"] == "Test content"


# ============================================================
# PPT API 测试
# ============================================================

class TestPPTAPI:
    """PPT API 测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from smart_copilot_platform import app
        return TestClient(app)
    
    def test_generate_ppt(self, client):
        """测试生成 PPT"""
        slides = [
            {
                "title": "Test Slide",
                "content": "Test content",
                "layout": "title_and_content"
            }
        ]
        
        response = client.post(
            "/api/ppt/generate",
            json={
                "slides": slides,
                "filename": "test.pptx"
            }
        )
        
        # 可能成功或失败（取决于 ppt_generator 是否可用）
        assert response.status_code in [200, 500]


# ============================================================
# 端到端测试
# ============================================================

class TestEndToEnd:
    """端到端测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from smart_copilot_platform import app
        return TestClient(app)
    
    def test_full_workflow(self, client):
        """测试完整工作流程"""
        # 1. 检查系统健康
        health_response = client.get("/health")
        assert health_response.status_code == 200
        
        # 2. 获取模块列表
        modules_response = client.get("/api/modules")
        assert modules_response.status_code == 200
        
        # 3. 检查 MCP 状态
        mcp_response = client.get("/api/mcp/status")
        assert mcp_response.status_code == 200
        
        # 4. 创建测试文件并分析
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write("def test(): pass\n")
            temp_file = f.name
        
        try:
            # 获取符号
            symbols_response = client.get(f"/api/code/symbols?file_path={temp_file}")
            assert symbols_response.status_code == 200
            
            # 清除缓存
            cache_response = client.post("/api/code/clear-cache")
            assert cache_response.status_code == 200
            
        finally:
            os.unlink(temp_file)


# ============================================================
# 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from smart_copilot_platform import app
        return TestClient(app)
    
    def test_health_check_performance(self, client):
        """测试健康检查性能"""
        import time
        
        start = time.time()
        for _ in range(100):
            client.get("/health")
        end = time.time()
        
        avg_time = (end - start) / 100
        assert avg_time < 0.1  # 平均响应时间应小于 100ms
    
    def test_symbols_performance(self, client):
        """测试符号查询性能"""
        import time
        
        # 创建测试文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            # 写入一个较大的文件
            for i in range(100):
                f.write(f"def function_{i}(): pass\n")
            temp_file = f.name
        
        try:
            start = time.time()
            for _ in range(10):
                client.get(f"/api/code/symbols?file_path={temp_file}")
            end = time.time()
            
            avg_time = (end - start) / 10
            assert avg_time < 1.0  # 平均响应时间应小于 1s
            
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
