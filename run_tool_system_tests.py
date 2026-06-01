#!/usr/bin/env python3
"""
工具系统测试运行脚本

运行所有工具系统相关的测试，并生成测试报告。
"""

import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("工具系统测试运行器")
    print("=" * 60)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 测试目录
    test_dir = Path(__file__).parent / "tests" / "tool_system"
    
    if not test_dir.exists():
        print(f"错误: 测试目录不存在: {test_dir}")
        return False
    
    # 测试文件列表
    test_files = [
        "test_tool_models.py",
        "test_tool_registry.py",
        "test_tool_executor.py",
        "test_skill_adapter.py"
    ]
    
    # 检查测试文件是否存在
    missing_files = []
    for test_file in test_files:
        if not (test_dir / test_file).exists():
            missing_files.append(test_file)
    
    if missing_files:
        print(f"警告: 以下测试文件不存在: {', '.join(missing_files)}")
        test_files = [f for f in test_files if f not in missing_files]
    
    if not test_files:
        print("错误: 没有找到测试文件")
        return False
    
    # 运行测试
    print(f"找到 {len(test_files)} 个测试文件:")
    for test_file in test_files:
        print(f"  - {test_file}")
    print()
    
    # 构建 pytest 命令
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",  # 详细输出
        "--tb=short",  # 简短的错误输出
        "--json-report",  # 生成 JSON 报告
        "--json-report-file=test_report.json",  # JSON 报告文件
        "--cov=tool_system",  # 代码覆盖率
        "--cov-report=term-missing",  # 终端显示覆盖率
        "--cov-report=json:coverage.json",  # JSON 覆盖率报告
    ]
    
    print("运行命令:", " ".join(cmd))
    print()
    print("-" * 60)
    
    # 执行测试
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        print("-" * 60)
        print()
        
        if result.returncode == 0:
            print("✓ 所有测试通过!")
        else:
            print("✗ 部分测试失败")
        
        # 生成测试报告摘要
        generate_summary()
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return False


def generate_summary():
    """生成测试报告摘要"""
    print()
    print("=" * 60)
    print("测试报告摘要")
    print("=" * 60)
    
    # 检查 JSON 报告是否存在
    report_file = Path("test_report.json")
    if report_file.exists():
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            summary = report.get("summary", {})
            print(f"总测试数: {summary.get('total', 0)}")
            print(f"通过: {summary.get('passed', 0)}")
            print(f"失败: {summary.get('failed', 0)}")
            print(f"错误: {summary.get('error', 0)}")
            print(f"跳过: {summary.get('skipped', 0)}")
            
            duration = report.get("duration", 0)
            print(f"总耗时: {duration:.2f} 秒")
            
        except Exception as e:
            print(f"读取测试报告时出错: {e}")
    else:
        print("未找到测试报告文件")
    
    # 检查覆盖率报告
    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        try:
            with open(coverage_file, 'r', encoding='utf-8') as f:
                coverage = json.load(f)
            
            total = coverage.get("totals", {})
            print()
            print("代码覆盖率:")
            print(f"  总行数: {total.get('num_statements', 0)}")
            print(f"  覆盖行数: {total.get('covered_lines', 0)}")
            print(f"  覆盖率: {total.get('percent_covered', 0):.1f}%")
            
        except Exception as e:
            print(f"读取覆盖率报告时出错: {e}")
    
    print()
    print("=" * 60)


def run_specific_test(test_name):
    """运行特定测试"""
    print(f"运行特定测试: {test_name}")
    
    test_dir = Path(__file__).parent / "tests" / "tool_system"
    test_file = test_dir / f"test_{test_name}.py"
    
    if not test_file.exists():
        print(f"错误: 测试文件不存在: {test_file}")
        return False
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 运行特定测试
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # 运行所有测试
        success = run_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
