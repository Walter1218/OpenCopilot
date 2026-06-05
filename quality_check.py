#!/usr/bin/env python3
"""
OpenCopilot 质量评估体系

一键运行所有质量检查并输出综合报告。

使用: python quality_check.py
"""

import sys
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent

SUITES = {
    "单元测试": {
        "path": "tests/unit/ tests/integration/",
        "weight": 0.20,
        "desc": "核心模块功能正确性"
    },
    "E2E链路测试": {
        "path": "tests/e2e/test_real_business.py -k 'not TestAPIGatewayRealHTTP'",
        "weight": 0.20,
        "desc": "完整业务链路走通"
    },
    "结果评估": {
        "path": "tests/e2e/test_result_evaluation.py",
        "weight": 0.20,
        "desc": "输出正确性benchmark对比"
    },
    "Phase1消融": {
        "path": "tests/e2e/test_ablation_study.py",
        "weight": 0.15,
        "desc": "假功能修复效果验证"
    },
    "P1消融(PPT)": {
        "path": "tests/e2e/test_ablation_ppt.py",
        "weight": 0.15,
        "desc": "PPT富文本渲染验证"
    },
    "P2消融(安全)": {
        "path": "tests/e2e/test_ablation_p2.py",
        "weight": 0.10,
        "desc": "安全加固效果验证"
    },
}

def run_suite(name, info):
    """运行单个测试套件"""
    path = info["path"]
    print(f"\n{'='*60}")
    print(f"  {name} — {info['desc']}")
    print(f"{'='*60}")
    
    t0 = time.time()
    # 使用 shlex 正确解析参数（处理 -k '...' 等）
    import shlex
    cmd = [sys.executable, "-m", "pytest"] + shlex.split(path) + ["-q", "--tb=line"]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.time() - t0
    
    # 解析结果
    stdout = result.stdout
    passed = 0
    failed = 0
    import re
    
    # 找 "X passed" 行（兼容多种格式）
    for line in stdout.split('\n'):
        line = line.strip()
        # 匹配 "X passed" 或 "X passed, Y warnings"
        m = re.search(r'(\d+)\s+passed', line)
        if m and 'failed' not in line:
            passed = int(m.group(1))
        m_fail = re.search(r'(\d+)\s+failed', line)
        if m_fail and 'passed' not in line:
            failed = int(m_fail.group(1))
        # 匹配 "X failed, Y passed" 格式
        m_combined = re.match(r'(\d+)\s+passed,\s+(\d+)\s+failed', line)
        if m_combined:
            passed = int(m_combined.group(1))
            failed = int(m_combined.group(2))
        # 匹配 "X failed" (only failed)
        m_only_fail = re.match(r'(\d+)\s+failed$', line)
        if m_only_fail and passed == 0:
            failed = int(m_only_fail.group(1))
    
    total = passed + failed
    score = passed / total * 100 if total > 0 else 0
    
    return {
        "name": name,
        "passed": passed,
        "failed": failed,
        "total": total,
        "score": score,
        "elapsed": elapsed,
        "stderr": result.stderr[-200:] if result.stderr else ""
    }


def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║       OpenCopilot 质量评估体系 v1.0                   ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    all_results = []
    overall_start = time.time()
    
    for name, info in SUITES.items():
        try:
            r = run_suite(name, info)
            all_results.append(r)
        except subprocess.TimeoutExpired:
            all_results.append({
                "name": name, "passed": 0, "failed": 1, "total": 1,
                "score": 0, "elapsed": 120, "stderr": "TIMEOUT"
            })
        except Exception as e:
            all_results.append({
                "name": name, "passed": 0, "failed": 1, "total": 1,
                "score": 0, "elapsed": 0, "stderr": str(e)
            })
    
    overall_elapsed = time.time() - overall_start
    
    # ========== 综合报告 ==========
    print(f"\n{'='*60}")
    print(f"  综合质量报告")
    print(f"{'='*60}")
    print(f"{'套件':<16} {'通过':>5} {'失败':>5} {'得分':>6} {'权重':>6} 加权")
    print(f"{'-'*50}")
    
    total_weighted = 0
    total_passed = 0
    total_cases = 0
    
    for r in all_results:
        weighted = r["score"] * SUITES[r["name"]]["weight"]
        total_weighted += weighted
        total_passed += r["passed"]
        total_cases += r["total"]
        
        status = "✅" if r["failed"] == 0 else "❌"
        print(f"{status} {r['name']:<14} {r['passed']:>5} {r['failed']:>5} {r['score']:>5.0f}% {SUITES[r['name']]['weight']:>5.0%}  {weighted:>5.1f}")
    
    overall = total_weighted  # 加权后已是百分制
    
    print(f"{'-'*50}")
    print(f"{'总计':<16} {total_passed:>5} {total_cases - total_passed:>5} {'':>6} {'':>6}  {total_weighted:>5.1f}")
    print(f"\n  综合质量分: {overall:.1f}/100")
    print(f"  总耗时: {overall_elapsed:.1f}s")
    
    # 等级评定
    if overall >= 95:
        grade = "🟢 A 优秀"
    elif overall >= 85:
        grade = "🟡 B 良好"
    elif overall >= 70:
        grade = "🟠 C 合格"
    else:
        grade = "🔴 D 需改进"
    
    print(f"  质量等级: {grade}")
    
    # 失败详情
    failures = [r for r in all_results if r["failed"] > 0]
    if failures:
        print(f"\n  失败详情:")
        for r in failures:
            print(f"    {r['name']}: {r['failed']} failed")
            if r["stderr"]:
                # 只显示前 200 字符
                err = r["stderr"].strip()[:200]
                print(f"      {err}")
    
    print(f"\n{'='*60}")
    
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
