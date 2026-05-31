"""
FormatSkill API 测试
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport


async def test_format_api():
    """测试 FormatSkill API"""
    print("\n" + "=" * 60)
    print("FormatSkill API 测试")
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
        
        # 2. 测试 Markdown 转 Word
        print("\n--- Markdown 转 Word 测试 ---")
        md_content = """# 测试文档

## 第一章

这是一个测试段落。

- 列表项1
- 列表项2
"""
        response = await client.post(
            "/api/format/md-to-docx",
            json={
                "content": md_content
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "docx"
        assert "paragraphs" in data
        print(f"✅ Markdown 转 Word 通过，段落数: {data.get('paragraphs', 'N/A')}")
        
        # 3. 测试 Markdown 转 PPT
        print("\n--- Markdown 转 PPT 测试 ---")
        response = await client.post(
            "/api/format/md-to-pptx",
            json={
                "content": md_content
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "pptx"
        assert "slides" in data
        print(f"✅ Markdown 转 PPT 通过，幻灯片数: {data.get('slides', 'N/A')}")
        
        # 4. 测试文本转表格 (Markdown格式)
        print("\n--- 文本转表格测试 (Markdown) ---")
        text_content = """姓名,年龄,城市
张三,25,北京
李四,30,上海
"""
        response = await client.post(
            "/api/format/text-to-table",
            json={
                "content": text_content,
                "format": "markdown"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"
        assert data["rows"] == 3
        assert data["columns"] == 3
        print(f"✅ 文本转表格通过，行数: {data['rows']}, 列数: {data['columns']}")
        
        # 5. 测试文本转表格 (HTML格式)
        print("\n--- 文本转表格测试 (HTML) ---")
        response = await client.post(
            "/api/format/text-to-table",
            json={
                "content": text_content,
                "format": "html"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "html"
        print(f"✅ 文本转HTML表格通过，行数: {data['rows']}")
        
        # 6. 测试文本转表格 (CSV格式)
        print("\n--- 文本转表格测试 (CSV) ---")
        response = await client.post(
            "/api/format/text-to-table",
            json={
                "content": text_content,
                "format": "csv"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "csv"
        print(f"✅ 文本转CSV表格通过，行数: {data['rows']}")
        
        # 7. 测试错误处理
        print("\n--- 错误处理测试 ---")
        response = await client.post(
            "/api/format/md-to-docx",
            json={
                "content": ""
            }
        )
        # 空内容会触发异常，返回500或400
        assert response.status_code in [400, 500]
        print(f"✅ 空内容错误处理通过，状态码: {response.status_code}")
    
    # 测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("✅ 所有 API 测试通过！")
    print("\nAPI 端点:")
    print("  1. POST /api/format/md-to-docx - Markdown转Word")
    print("  2. POST /api/format/md-to-pptx - Markdown转PPT")
    print("  3. POST /api/format/text-to-table - 文本转表格")


if __name__ == "__main__":
    asyncio.run(test_format_api())
