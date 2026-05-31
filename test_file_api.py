#!/usr/bin/env python3
"""
FileSkill API 测试

测试 FileSkill 的 API 接口：
1. 文件读取接口
2. 文件写入接口
3. 文件格式转换接口
4. 目录列表接口
5. 文件删除接口
"""

import asyncio
import sys
import os
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx


def print_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if message:
        print(f"      {message}")


async def test_file_read_api():
    """测试文件读取API"""
    print_header("文件读取API测试")
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("测试内容")
            temp_file = f.name
        
        try:
            async with httpx.AsyncClient() as client:
                # 测试正常读取
                response = await client.post(
                    "http://localhost:8088/api/file/read",
                    json={
                        "file_path": temp_file,
                        "format": "text"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print_result("文件读取API测试", True, 
                                f"读取成功，内容: {data.get('content', '')[:20]}...")
                else:
                    print_result("文件读取API测试", False, 
                                f"状态码: {response.status_code}, 错误: {response.text}")
                
                return response.status_code == 200
        finally:
            # 清理临时文件
            os.unlink(temp_file)
    except Exception as e:
        print_result("文件读取API测试", False, str(e))
        return False


async def test_file_write_api():
    """测试文件写入API"""
    print_header("文件写入API测试")
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test.txt")
            
            async with httpx.AsyncClient() as client:
                # 测试正常写入
                response = await client.post(
                    "http://localhost:8088/api/file/write",
                    json={
                        "content": "API测试内容",
                        "file_path": temp_file,
                        "format": "text"
                    }
                )
                
                if response.status_code == 200:
                    # 验证文件是否写入成功
                    if os.path.exists(temp_file):
                        with open(temp_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if content == "API测试内容":
                            print_result("文件写入API测试", True, "写入成功，内容验证通过")
                        else:
                            print_result("文件写入API测试", False, "内容验证失败")
                    else:
                        print_result("文件写入API测试", False, "文件未创建")
                else:
                    print_result("文件写入API测试", False, 
                                f"状态码: {response.status_code}, 错误: {response.text}")
                
                return response.status_code == 200
    except Exception as e:
        print_result("文件写入API测试", False, str(e))
        return False


async def test_file_convert_api():
    """测试文件格式转换API"""
    print_header("文件格式转换API测试")
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("测试内容")
            temp_file = f.name
        
        try:
            output_file = temp_file.replace('.txt', '.md')
            
            async with httpx.AsyncClient() as client:
                # 测试正常转换
                response = await client.post(
                    "http://localhost:8088/api/file/convert",
                    json={
                        "input_path": temp_file,
                        "output_format": "md",
                        "output_path": output_file
                    }
                )
                
                if response.status_code == 200:
                    print_result("文件格式转换API测试", True, "转换成功")
                else:
                    print_result("文件格式转换API测试", False, 
                                f"状态码: {response.status_code}, 错误: {response.text}")
                
                return response.status_code == 200
        finally:
            # 清理临时文件
            os.unlink(temp_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    except Exception as e:
        print_result("文件格式转换API测试", False, str(e))
        return False


async def test_file_list_api():
    """测试目录列表API"""
    print_header("目录列表API测试")
    
    try:
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一些文件
            for i in range(3):
                with open(os.path.join(temp_dir, f"file{i}.txt"), 'w') as f:
                    f.write(f"内容{i}")
            
            async with httpx.AsyncClient() as client:
                # 测试正常目录列表
                response = await client.post(
                    "http://localhost:8088/api/file/list",
                    json={
                        "dir_path": temp_dir
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    print_result("目录列表API测试", True, 
                                f"列出 {len(items)} 个项目")
                else:
                    print_result("目录列表API测试", False, 
                                f"状态码: {response.status_code}, 错误: {response.text}")
                
                return response.status_code == 200
    except Exception as e:
        print_result("目录列表API测试", False, str(e))
        return False


async def test_file_delete_api():
    """测试文件删除API"""
    print_header("文件删除API测试")
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("测试内容")
            temp_file = f.name
        
        try:
            async with httpx.AsyncClient() as client:
                # 测试正常删除
                response = await client.post(
                    "http://localhost:8088/api/file/delete",
                    json={
                        "file_path": temp_file
                    }
                )
                
                if response.status_code == 200:
                    # 验证文件是否被删除
                    if not os.path.exists(temp_file):
                        print_result("文件删除API测试", True, "删除成功")
                    else:
                        print_result("文件删除API测试", False, "文件未删除")
                else:
                    print_result("文件删除API测试", False, 
                                f"状态码: {response.status_code}, 错误: {response.text}")
                
                return response.status_code == 200
        except Exception as e:
            # 如果测试失败，确保清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            raise
    except Exception as e:
        print_result("文件删除API测试", False, str(e))
        return False


async def main():
    """主测试函数"""
    print_header("FileSkill API 全面测试")
    
    # 运行所有测试
    tests = [
        test_file_read_api,
        test_file_write_api,
        test_file_convert_api,
        test_file_list_api,
        test_file_delete_api
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {test.__name__} - {str(e)}")
            results.append(False)
    
    # 打印总结
    print_header("测试总结")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())