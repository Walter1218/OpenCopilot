"""
v5 Agent Pipeline 消融实验 & 多维评测脚本

测试矩阵:
  - 6 action types: explain, fix, polish, translate, code_review, chat
  - 2 backends: self_agent (mimo), hermes (vnext_provider)
  - 每 case 运行 2 次 → 稳定性评估

评测维度:
  1. 输出质量 (quality): 相关性、完整性、正确性
  2. 稳定性 (stability): 多次运行的一致性
  3. 正确性 (correctness): 关键词命中、格式验证
  4. 时效性 (timeliness): 延迟、chunk 速率

运行:
  python tests/e2e/test_v5_ablation_benchmark.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import signal
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── 项目根目录注入 ──
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# 1. 评测用例定义
# =============================================================================

@dataclass
class TestCase:
    action_type: str
    label: str
    prompt: str
    context_source: str
    context_meta: dict
    # 评测规则
    min_length: int = 20
    keywords: list = field(default_factory=list)
    format_check: str = ""  # "json_slides" | "chinese" | "code" | ""
    description: str = ""


TEST_CASES: List[TestCase] = [
    TestCase(
        action_type="explain",
        label="Explain 代码解释",
        prompt="请解释以下代码/文本:\n\ndef fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)\n\nprint([fib(i) for i in range(10)])",
        context_source="selection",
        context_meta={"source_text": "def fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)"},
        min_length=50,
        keywords=["递归", "斐波那契", "函数", "fib", "调用", "返回"],
        format_check="chinese",
        description="解释斐波那契递归函数",
    ),
    TestCase(
        action_type="fix",
        label="Fix 代码修复",
        prompt="请修复以下代码中的问题:\n\ndef divide(a, b):\n    return a / b\n\nresult = divide(10, 0)\nprint(result)",
        context_source="selection",
        context_meta={"source_text": "def divide(a, b):\n    return a / b\n\nresult = divide(10, 0)"},
        min_length=30,
        keywords=["除零", "ZeroDivision", "异常", "错误", "检查", "0"],
        format_check="chinese",
        description="修复除零错误",
    ),
    TestCase(
        action_type="polish",
        label="Polish 文本润色",
        prompt="请润色优化以下文本:\n\n这个产品很好，用起来不错，功能也很多，推荐大家试试。",
        context_source="selection",
        context_meta={"source_text": "这个产品很好，用起来不错，功能也很多，推荐大家试试。"},
        min_length=15,
        keywords=["产品", "体验", "功能", "推荐"],
        format_check="chinese",
        description="润色一段产品评价",
    ),
    TestCase(
        action_type="translate",
        label="Translate 翻译",
        prompt="请将以下文本从中文翻译为英文:\n\n人工智能正在改变我们的生活方式，从医疗健康到交通出行，AI 技术无处不在。",
        context_source="selection",
        context_meta={"source_text": "人工智能正在改变我们的生活方式", "source_lang": "zh", "target_lang": "en"},
        min_length=30,
        keywords=["artificial intelligence", "AI", "changing", "life", "health", "transportation"],
        format_check="",
        description="中译英",
    ),
    TestCase(
        action_type="code_review",
        label="Code Review 代码审查",
        prompt="请对以下代码进行审查:\n\ndef process_users(users):\n    for user in users:\n        name = user['name']\n        email = user['email']\n        print(f'User: {name}, Email: {email}')\n    return True",
        context_source="selection",
        context_meta={"source_text": "def process_users(users):\n    for user in users:\n        name = user['name']\n        email = user['email']"},
        min_length=40,
        keywords=["检查", "错误", "key", "异常", "安全", "输入", "验证", "类型"],
        format_check="chinese",
        description="审查用户处理函数",
    ),
    TestCase(
        action_type="chat",
        label="Chat 自由对话",
        prompt="你好，请用一句话介绍一下你自己。",
        context_source="chat",
        context_meta={},
        min_length=10,
        keywords=["助手", "帮助", "AI", "智能", "copilot", "你好", "您好", "助理"],
        format_check="chinese",
        description="简单自我介绍",
    ),
]


# =============================================================================
# 2. 后端执行器
# =============================================================================

@dataclass
class ExecutionResult:
    backend: str
    action_type: str
    label: str
    success: bool
    full_text: str
    chunk_count: int
    latency_ms: float
    error_msg: str = ""
    output_len: int = 0
    chars_per_sec: float = 0.0

    def __post_init__(self):
        self.output_len = len(self.full_text)
        if self.latency_ms > 0 and self.output_len > 0:
            self.chars_per_sec = round(self.output_len / (self.latency_ms / 1000.0), 1)


def run_self_agent(tc: TestCase, timeout_sec: int = 180) -> ExecutionResult:
    """通过 self_agent 后端执行（直接调用 call_agent_pipeline_sync）"""
    from opencopilot.agent.caller import call_agent_pipeline_sync

    full_text = ""
    chunk_count = 0
    cancel_event = threading.Event()
    start_ts = time.time()

    try:
        # signal.alarm 硬超时
        def _alarm_handler(signum, frame):
            cancel_event.set()
            raise TimeoutError(f"self_agent 超时 (>{timeout_sec}s)")

        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(timeout_sec)

        for chunk in call_agent_pipeline_sync(
            text=tc.prompt,
            action_type=tc.action_type,
            session_id=f"bench-self-{uuid.uuid4().hex[:8]}",
            context_source=tc.context_source,
            context_meta=tc.context_meta,
            is_new_task=True,
            cancel_event=cancel_event,
            timeout=timeout_sec,
        ):
            full_text += chunk
            chunk_count += 1
            if cancel_event.is_set():
                break

        signal.alarm(0)
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)
        latency = (time.time() - start_ts) * 1000
        return ExecutionResult("self_agent", tc.action_type, tc.label, True,
                               full_text, chunk_count, latency)
    except Exception as e:
        signal.alarm(0)
        latency = (time.time() - start_ts) * 1000
        return ExecutionResult("self_agent", tc.action_type, tc.label, False,
                               "", 0, latency, error_msg=str(e))


def run_hermes_agent(tc: TestCase, timeout_sec: int = 180) -> ExecutionResult:
    """通过 Hermes (vnext_provider) 后端执行"""
    from gui_next.smart_copilot.runtime import SmartCopilotApiRuntime
    import httpx

    api_runtime = SmartCopilotApiRuntime(preferred_base_url="http://127.0.0.1:8000")
    start_ts = time.time()
    full_text = ""
    chunk_count = 0

    try:
        base_url = api_runtime.ensure_ready()
        client = httpx.Client(base_url=base_url, timeout=httpx.Timeout(10.0, read=timeout_sec))

        # 1. Create context snapshot
        snap_resp = client.post("/vnext/context/snapshots", json={
            "trigger": "benchmark",
            "source_app": f"bench_{tc.context_source}",
            "selection_text": tc.context_meta.get("source_text", tc.prompt),
            "metadata": {"context_source": tc.context_source, "context_meta": tc.context_meta},
        })
        snap_resp.raise_for_status()
        snapshot_id = snap_resp.json()["context_snapshot_id"]

        # 2. Create task
        task_resp = client.post("/vnext/tasks", json={
            "action": tc.action_type,
            "user_input": tc.prompt,
            "context_snapshot_id": snapshot_id,
        })
        task_resp.raise_for_status()
        task_id = task_resp.json()["task_id"]

        # 3. Poll events
        last_seq = 0
        terminal = False
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            ev_resp = client.get(f"/vnext/tasks/{task_id}/events")
            ev_resp.raise_for_status()
            events = ev_resp.json().get("events", [])
            for ev in events:
                seq = ev.get("sequence", 0)
                if seq <= last_seq:
                    continue
                last_seq = seq
                etype = ev.get("type", "")
                payload = ev.get("payload", {})
                if etype == "task.delta":
                    full_text += payload.get("delta", "")
                    chunk_count += 1
                elif etype == "task.completed":
                    summary = payload.get("summary", "")
                    if summary:
                        full_text = summary
                    terminal = True
                elif etype == "task.failed":
                    raise RuntimeError(payload.get("error", "Hermes task failed"))
            if terminal:
                break
            time.sleep(0.3)

        client.close()
        # 不要 shutdown 共享的 API 进程
        latency = (time.time() - start_ts) * 1000
        return ExecutionResult("hermes", tc.action_type, tc.label, True,
                               full_text, chunk_count, latency)
    except Exception as e:
        try:
            client.close()
        except Exception:
            pass
        latency = (time.time() - start_ts) * 1000
        return ExecutionResult("hermes", tc.action_type, tc.label, False,
                               "", 0, latency, error_msg=str(e))


# =============================================================================
# 3. 评测器
# =============================================================================

def _filter_think(text: str) -> str:
    display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in display:
        display = display.split("<think>")[0]
    return display


def _has_chinese(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def evaluate_quality(result: ExecutionResult, tc: TestCase) -> Dict[str, Any]:
    """评测输出质量"""
    text = _filter_think(result.full_text).strip()
    scores = {}

    # 1. 非空检查
    scores["not_empty"] = 1.0 if text else 0.0

    # 2. 长度达标
    scores["length_ok"] = 1.0 if len(text) >= tc.min_length else min(len(text) / tc.min_length, 0.9)

    # 3. 关键词命中
    text_lower = text.lower()
    matched = [kw for kw in tc.keywords if kw.lower() in text_lower]
    scores["keyword_hit_rate"] = len(matched) / max(len(tc.keywords), 1)

    # 4. 格式检查
    scores["format_ok"] = 1.0
    if tc.format_check == "chinese":
        scores["format_ok"] = 1.0 if _has_chinese(text) else 0.3
    elif tc.format_check == "json_slides":
        try:
            data = json.loads(text)
            scores["format_ok"] = 1.0 if "slides" in data else 0.5
        except json.JSONDecodeError:
            scores["format_ok"] = 0.3

    # 5. 无 think 标签泄漏
    scores["no_think_leak"] = 0.0 if "<think>" in text else 1.0

    # 综合质量分 (0-100)
    weights = {"not_empty": 0.1, "length_ok": 0.2, "keyword_hit_rate": 0.3,
               "format_ok": 0.2, "no_think_leak": 0.2}
    quality_score = sum(scores[k] * weights[k] for k in weights) * 100
    scores["overall"] = round(quality_score, 1)

    return scores


def evaluate_stability(results: List[ExecutionResult], tc: TestCase) -> Dict[str, Any]:
    """评测多次运行的稳定性"""
    if len(results) < 2:
        return {"consistency": "N/A (only 1 run)"}

    r1, r2 = results[0], results[1]
    # 长度一致性
    len_diff = abs(r1.output_len - r2.output_len) / max(r1.output_len, r2.output_len, 1)
    # 延迟一致性
    lat_diff = abs(r1.latency_ms - r2.latency_ms) / max(r1.latency_ms, r2.latency_ms, 1)
    # 成功率
    success_rate = sum(1 for r in results if r.success) / len(results)

    # 关键词命中一致性
    text1_lower = _filter_think(r1.full_text).lower()
    text2_lower = _filter_think(r2.full_text).lower()
    kw1 = set(kw for kw in tc.keywords if kw.lower() in text1_lower)
    kw2 = set(kw for kw in tc.keywords if kw.lower() in text2_lower)
    kw_overlap = len(kw1 & kw2) / max(len(kw1 | kw2), 1)

    return {
        "success_rate": round(success_rate * 100, 0),
        "length_consistency": round((1 - len_diff) * 100, 1),
        "latency_consistency": round((1 - lat_diff) * 100, 1),
        "keyword_overlap": round(kw_overlap * 100, 1),
    }


# =============================================================================
# 4. 报告生成
# =============================================================================

def generate_report(all_results: Dict[str, Dict[str, List[ExecutionResult]]],
                    run_count: int = 2) -> str:
    """生成 Markdown 评测报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# v5 Agent Pipeline 消融实验评测报告",
        f"",
        f"**生成时间**: {timestamp}  ",
        f"**运行次数**: 每 case {run_count} 次  ",
        f"**后端对比**: self_agent (mimo) vs hermes (vnext_provider)  ",
        f"",
        f"---",
        f"",
        f"## 1. 测试矩阵总览",
        f"",
        f"| # | Action | 描述 | self_agent | hermes |",
        f"|---|--------|------|------------|--------|",
    ]

    for tc in TEST_CASES:
        sa_results = all_results.get("self_agent", {}).get(tc.action_type, [])
        he_results = all_results.get("hermes", {}).get(tc.action_type, [])
        sa_status = "✅" if sa_results and sa_results[0].success else "❌"
        he_status = "✅" if he_results and he_results[0].success else "❌"
        desc = tc.description
        lines.append(f"| {tc.action_type} | {tc.label} | {desc} | {sa_status} | {he_status} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 2. 输出质量评分 (0-100)",
        f"",
    ])

    quality_summary = {"self_agent": [], "hermes": []}
    for backend in ["self_agent", "hermes"]:
        lines.append(f"### {backend}")
        lines.append(f"| Action | 非空 | 长度 | 关键词命中 | 格式 | 无泄漏 | **综合** |")
        lines.append(f"|--------|------|------|-----------|------|--------|---------|")
        for tc in TEST_CASES:
            results = all_results.get(backend, {}).get(tc.action_type, [])
            if results and results[0].success:
                scores = evaluate_quality(results[0], tc)
                lines.append(
                    f"| {tc.action_type} "
                    f"| {scores['not_empty']*100:.0f}% "
                    f"| {scores['length_ok']*100:.0f}% "
                    f"| {scores['keyword_hit_rate']*100:.0f}% "
                    f"| {scores['format_ok']*100:.0f}% "
                    f"| {scores['no_think_leak']*100:.0f}% "
                    f"| **{scores['overall']}** |"
                )
                quality_summary[backend].append(scores["overall"])
            else:
                lines.append(f"| {tc.action_type} | ❌ 失败 | - | - | - | - | **0** |")
                quality_summary[backend].append(0)
        lines.append("")

    lines.extend([
        f"---",
        f"",
        f"## 3. 时效性对比",
        f"",
        f"| Action | self_agent 延迟(ms) | hermes 延迟(ms) | self_agent 速率(c/s) | hermes 速率(c/s) |",
        f"|--------|-------------------|----------------|---------------------|-----------------|",
    ])

    latency_data = {"self_agent": [], "hermes": []}
    for tc in TEST_CASES:
        sa = all_results.get("self_agent", {}).get(tc.action_type, [])
        he = all_results.get("hermes", {}).get(tc.action_type, [])
        sa_lat = f"{sa[0].latency_ms:.0f}" if sa and sa[0].success else "FAIL"
        he_lat = f"{he[0].latency_ms:.0f}" if he and he[0].success else "FAIL"
        sa_cps = f"{sa[0].chars_per_sec:.1f}" if sa and sa[0].success else "-"
        he_cps = f"{he[0].chars_per_sec:.1f}" if he and he[0].success else "-"
        lines.append(f"| {tc.action_type} | {sa_lat} | {he_lat} | {sa_cps} | {he_cps} |")
        if sa and sa[0].success:
            latency_data["self_agent"].append(sa[0].latency_ms)
        if he and he[0].success:
            latency_data["hermes"].append(he[0].latency_ms)

    # 平均延迟
    sa_avg = sum(latency_data["self_agent"]) / max(len(latency_data["self_agent"]), 1)
    he_avg = sum(latency_data["hermes"]) / max(len(latency_data["hermes"]), 1)
    lines.append(f"| **平均** | **{sa_avg:.0f}** | **{he_avg:.0f}** | - | - |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 4. 稳定性评估 (2次运行)",
        f"",
    ])

    for backend in ["self_agent", "hermes"]:
        lines.append(f"### {backend}")
        lines.append(f"| Action | 成功率 | 长度一致% | 延迟一致% | 关键词重叠% |")
        lines.append(f"|--------|-------|----------|----------|------------|")
        for tc in TEST_CASES:
            results = all_results.get(backend, {}).get(tc.action_type, [])
            if len(results) >= 2:
                stab = evaluate_stability(results, tc)
                lines.append(
                    f"| {tc.action_type} "
                    f"| {stab.get('success_rate', 'N/A')}% "
                    f"| {stab.get('length_consistency', 'N/A')}% "
                    f"| {stab.get('latency_consistency', 'N/A')}% "
                    f"| {stab.get('keyword_overlap', 'N/A')}% |"
                )
            else:
                lines.append(f"| {tc.action_type} | N/A | N/A | N/A | N/A |")
        lines.append("")

    lines.extend([
        f"---",
        f"",
        f"## 5. 输出样本 (首次运行)",
        f"",
    ])

    for tc in TEST_CASES:
        for backend in ["self_agent", "hermes"]:
            results = all_results.get(backend, {}).get(tc.action_type, [])
            if results and results[0].success:
                text = _filter_think(results[0].full_text).strip()
                preview = text[:300] + ("..." if len(text) > 300 else "")
                lines.append(f"### [{backend}] {tc.label}")
                lines.append(f"- **长度**: {results[0].output_len} 字符 / {results[0].chunk_count} chunks")
                lines.append(f"- **延迟**: {results[0].latency_ms:.0f}ms")
                lines.append(f"- **输出预览**:")
                lines.append(f"```")
                lines.append(preview)
                lines.append(f"```")
                lines.append("")
            elif results:
                lines.append(f"### [{backend}] {tc.label}")
                lines.append(f"- ❌ 失败: {results[0].error_msg}")
                lines.append("")

    lines.extend([
        f"---",
        f"",
        f"## 6. 综合结论",
        f"",
    ])

    sa_quality_avg = sum(quality_summary["self_agent"]) / max(len(quality_summary["self_agent"]), 1)
    he_quality_avg = sum(quality_summary["hermes"]) / max(len(quality_summary["hermes"]), 1)
    sa_success = sum(1 for tc in TEST_CASES
                     for r in all_results.get("self_agent", {}).get(tc.action_type, [])[:1]
                     if r.success)
    he_success = sum(1 for tc in TEST_CASES
                     for r in all_results.get("hermes", {}).get(tc.action_type, [])[:1]
                     if r.success)

    lines.append(f"| 维度 | self_agent | hermes |")
    lines.append(f"|------|-----------|--------|")
    lines.append(f"| 平均质量分 | {sa_quality_avg:.1f} | {he_quality_avg:.1f} |")
    lines.append(f"| 成功用例 | {sa_success}/{len(TEST_CASES)} | {he_success}/{len(TEST_CASES)} |")
    lines.append(f"| 平均延迟 | {sa_avg:.0f}ms | {he_avg:.0f}ms |")

    winner = "self_agent" if sa_quality_avg > he_quality_avg else "hermes" if he_quality_avg > sa_quality_avg else "平手"
    lines.append(f"")
    lines.append(f"**综合优胜**: {winner}")
    lines.append(f"")
    lines.append(f"> 报告由 test_v5_ablation_benchmark.py 自动生成")

    return "\n".join(lines)


# =============================================================================
# 5. 主入口
# =============================================================================

def main():
    print("=" * 70)
    print("  v5 Agent Pipeline 消融实验 & 多维评测")
    print("=" * 70)
    print()

    RUNS_PER_CASE = 2
    all_results: Dict[str, Dict[str, List[ExecutionResult]]] = {
        "self_agent": {},
        "hermes": {},
    }

    total_cases = len(TEST_CASES) * 2 * RUNS_PER_CASE  # actions × backends × runs
    current = 0

    for tc in TEST_CASES:
        print(f"━━━ {tc.label} ({tc.description}) ━━━")

        for backend_name, runner in [("self_agent", run_self_agent), ("hermes", run_hermes_agent)]:
            results_for_case: List[ExecutionResult] = []

            for run_idx in range(RUNS_PER_CASE):
                current += 1
                tag = f"[{current}/{total_cases}]"
                print(f"  {tag} {backend_name} run#{run_idx+1} ...", end=" ", flush=True)

                result = runner(tc)
                results_for_case.append(result)

                status = "✅" if result.success else "❌"
                lat = f"{result.latency_ms:.0f}ms"
                out_info = f"{result.output_len}c/{result.chunk_count}chunks" if result.success else result.error_msg[:60]
                print(f"{status} {lat} → {out_info}")

            all_results[backend_name][tc.action_type] = results_for_case

        print()

    # 生成报告
    print("━━━ 生成评测报告 ━━━")
    report = generate_report(all_results, run_count=RUNS_PER_CASE)
    report_path = project_root / "tests" / "e2e" / "ablation_benchmark_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"报告已保存: {report_path}")
    print()

    # 输出关键摘要
    sa_quality = []
    he_quality = []
    for tc in TEST_CASES:
        sa_r = all_results["self_agent"].get(tc.action_type, [])
        he_r = all_results["hermes"].get(tc.action_type, [])
        if sa_r and sa_r[0].success:
            sa_quality.append(evaluate_quality(sa_r[0], tc)["overall"])
        if he_r and he_r[0].success:
            he_quality.append(evaluate_quality(he_r[0], tc)["overall"])

    sa_avg = sum(sa_quality) / max(len(sa_quality), 1)
    he_avg = sum(he_quality) / max(len(he_quality), 1)

    print(f"━━━ 摘要 ━━━")
    print(f"  self_agent 平均质量: {sa_avg:.1f}/100  (成功 {len(sa_quality)}/{len(TEST_CASES)})")
    print(f"  hermes     平均质量: {he_avg:.1f}/100  (成功 {len(he_quality)}/{len(TEST_CASES)})")
    winner = "self_agent 🏆" if sa_avg > he_avg else "hermes 🏆" if he_avg > sa_avg else "平手 🤝"
    print(f"  综合优胜: {winner}")
    print()
    print("完成！")


if __name__ == "__main__":
    main()
