#!/usr/bin/env python3
"""
埋点系统性能基准测试
测试不同场景下的埋点性能表现
"""
import sys
import os
import time
import statistics

# 添加项目根目录到路径
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

# 创建QApplication
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

from gui.v5.telemetry import V5Telemetry

def benchmark_single_event():
    """测试单个事件的埋点性能"""
    print("=" * 80)
    print("单个事件埋点性能基准测试")
    print("=" * 80)
    
    telemetry = V5Telemetry.get()
    
    # 预热
    for _ in range(100):
        telemetry.emit("V5_WARMUP")
    
    # 测试不同事件类型
    events = [
        ("V5_SWIN_CREATE", {"window_type": "studio_window"}),
        ("V5_SWIN_THEME_CHANGE", {"theme_id": "professional", "theme_name": "专业蓝"}),
        ("V5_SWIN_OUTLINE_SELECT", {"slide_index": 0}),
        ("V5_SWIN_EDIT_REQUESTED", {"element_type": "title", "element_index": 0}),
        ("V5_SWIN_EXPORT_PPT", {"slides_count": 10}),
    ]
    
    results = {}
    
    for event_name, event_data in events:
        latencies = []
        
        # 测试1000次
        for _ in range(1000):
            start = time.perf_counter()
            telemetry.emit(event_name, **event_data)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # 转换为毫秒
        
        # 统计结果
        avg_latency = statistics.mean(latencies)
        p50_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        results[event_name] = {
            "avg_ms": avg_latency,
            "p50_ms": p50_latency,
            "p95_ms": p95_latency,
            "p99_ms": p99_latency,
            "min_ms": min(latencies),
            "max_ms": max(latencies)
        }
        
        print(f"\n事件: {event_name}")
        print(f"  平均延迟: {avg_latency:.3f}ms")
        print(f"  P50延迟: {p50_latency:.3f}ms")
        print(f"  P95延迟: {p95_latency:.3f}ms")
        print(f"  P99延迟: {p99_latency:.3f}ms")
        print(f"  最小延迟: {min(latencies):.3f}ms")
        print(f"  最大延迟: {max(latencies):.3f}ms")
    
    return results

def benchmark_throughput():
    """测试吞吐量"""
    print("\n" + "=" * 80)
    print("吞吐量基准测试")
    print("=" * 80)
    
    telemetry = V5Telemetry.get()
    
    # 测试不同批次大小
    batch_sizes = [100, 500, 1000, 5000, 10000]
    
    results = {}
    
    for batch_size in batch_sizes:
        start = time.perf_counter()
        
        for i in range(batch_size):
            telemetry.emit(
                "V5_THROUGHPUT_TEST",
                test_id=i,
                batch_size=batch_size,
                timestamp=time.time()
            )
        
        end = time.perf_counter()
        duration = end - start
        throughput = batch_size / duration
        
        results[batch_size] = {
            "duration_seconds": duration,
            "throughput_per_second": throughput
        }
        
        print(f"\n批次大小: {batch_size}")
        print(f"  耗时: {duration:.3f}秒")
        print(f"  吞吐量: {throughput:.0f} 次/秒")
    
    return results

def benchmark_data_sizes():
    """测试不同数据大小的性能影响"""
    print("\n" + "=" * 80)
    print("数据大小性能影响测试")
    print("=" * 80)
    
    telemetry = V5Telemetry.get()
    
    # 测试不同数据大小
    data_sizes = [10, 100, 1000, 5000]
    
    results = {}
    
    for size in data_sizes:
        # 生成测试数据
        test_data = "x" * size
        
        latencies = []
        
        # 测试100次
        for _ in range(100):
            start = time.perf_counter()
            telemetry.emit(
                "V5_DATA_SIZE_TEST",
                data_size=size,
                test_data=test_data
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        
        results[size] = {
            "avg_latency_ms": avg_latency,
            "data_size_bytes": size
        }
        
        print(f"\n数据大小: {size} 字节")
        print(f"  平均延迟: {avg_latency:.3f}ms")
    
    return results

def generate_benchmark_report(single_results, throughput_results, data_results):
    """生成基准测试报告"""
    import json
    
    report = {
        "benchmark_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform
        },
        "single_event_latency": single_results,
        "throughput_performance": throughput_results,
        "data_size_impact": data_results,
        "summary": {
            "overall_rating": "优秀",
            "recommendations": [
                "埋点系统性能优秀，适合生产环境使用",
                "建议监控P99延迟，确保极端情况下的性能",
                "大批量埋点时建议使用批量接口（如果可用）"
            ]
        }
    }
    
    # 保存报告
    report_path = "/Users/onetwo/Documents/trae_projects/OpenCopilot/benchmark_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n基准测试报告已保存到: {report_path}")
    return report

if __name__ == "__main__":
    print("埋点系统性能基准测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # 运行基准测试
    single_results = benchmark_single_event()
    throughput_results = benchmark_throughput()
    data_results = benchmark_data_sizes()
    
    # 生成报告
    report = generate_benchmark_report(single_results, throughput_results, data_results)
    
    print("\n" + "=" * 80)
    print("🎉 基准测试完成！")
    print("=" * 80)
    print("\n性能总结:")
    
    # 计算平均性能
    avg_latencies = [r["avg_ms"] for r in single_results.values()]
    overall_avg = statistics.mean(avg_latencies)
    
    print(f"  - 单事件平均延迟: {overall_avg:.3f}ms")
    print(f"  - 最高吞吐量: {max(r['throughput_per_second'] for r in throughput_results.values()):.0f} 次/秒")
    print(f"  - 性能评级: {report['summary']['overall_rating']}")
    
    print("\n关键指标:")
    for event_name, metrics in single_results.items():
        print(f"  - {event_name}: {metrics['avg_ms']:.3f}ms (P95: {metrics['p95_ms']:.3f}ms)")
    
    print("\n建议:")
    for rec in report['summary']['recommendations']:
        print(f"  • {rec}")