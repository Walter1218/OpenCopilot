"""
PersonaSkill API 测试
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport


async def test_persona_api():
    """测试 PersonaSkill API"""
    print("\n" + "=" * 60)
    print("PersonaSkill API 测试")
    print("=" * 60)
    
    # 导入 FastAPI 应用
    from smart_copilot_api import app
    
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 测试健康检查
        print("\n--- 健康检查 ---")
        response = await client.get("/health")
        assert response.status_code == 200
        print("✅ 健康检查通过")
        
        # 2. 测试列出人设
        print("\n--- 列出人设测试 ---")
        response = await client.post("/api/persona/list")
        assert response.status_code == 200
        data = response.json()
        assert "personas" in data
        assert "built_in" in data
        assert "custom" in data
        print(f"✅ 列出人设通过，人设数量: {data.get('total', 0)}")
        print(f"   内置人设: {data.get('built_in', [])}")
        
        # 3. 测试获取人设
        print("\n--- 获取人设测试 ---")
        response = await client.post(
            "/api/persona/get",
            json={"name": "default"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "default"
        assert "content" in data
        print(f"✅ 获取人设通过，人设名称: {data['name']}, 内容长度: {data.get('length', 0)}")
        
        # 4. 测试保存人设
        print("\n--- 保存人设测试 ---")
        test_content = """# API测试人设

这是通过API创建的测试人设。

## 特点

- API测试用途
- 自动创建
"""
        response = await client.post(
            "/api/persona/save",
            json={
                "name": "api_test_persona",
                "content": test_content
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "api_test_persona"
        print(f"✅ 保存人设通过，人设名称: {data['name']}, 操作: {data.get('action', 'N/A')}")
        
        # 5. 测试获取保存的人设
        print("\n--- 获取保存的人设测试 ---")
        response = await client.post(
            "/api/persona/get",
            json={"name": "api_test_persona"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "api_test_persona"
        print(f"✅ 获取保存的人设通过，人设名称: {data['name']}")
        
        # 6. 测试删除人设
        print("\n--- 删除人设测试 ---")
        response = await client.post(
            "/api/persona/delete",
            json={"name": "api_test_persona"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "deleted"
        print(f"✅ 删除人设通过，人设名称: {data['name']}, 操作: {data.get('action', 'N/A')}")
        
        # 7. 测试删除内置人设（应该失败）
        print("\n--- 删除内置人设测试 ---")
        response = await client.post(
            "/api/persona/delete",
            json={"name": "default"}
        )
        # 内置人设删除会返回400或500
        assert response.status_code in [400, 500]
        print(f"✅ 删除内置人设保护通过，状态码: {response.status_code}")
        
        # 8. 测试获取不存在的人设
        print("\n--- 获取不存在人设测试 ---")
        response = await client.post(
            "/api/persona/get",
            json={"name": "nonexistent_persona"}
        )
        # 不存在的人设会返回400或500
        assert response.status_code in [400, 500]
        print(f"✅ 获取不存在人设错误处理通过，状态码: {response.status_code}")
    
    # 测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("✅ 所有 API 测试通过！")
    print("\nAPI 端点:")
    print("  1. POST /api/persona/list - 列出所有人设")
    print("  2. POST /api/persona/get - 获取指定人设")
    print("  3. POST /api/persona/save - 保存人设")
    print("  4. POST /api/persona/delete - 删除人设")


if __name__ == "__main__":
    asyncio.run(test_persona_api())
