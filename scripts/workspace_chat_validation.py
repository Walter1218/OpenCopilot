#!/usr/bin/env python3
"""
Workspace Chat 全链路生产环境验证

覆盖范围：
1. 意图检测准确性（离线，不调 LLM）
2. 所有 action_type 通过 Workspace Chat 等效参数调用 Pipeline（真实 LLM）
3. Research 联网搜索能力验证（enable_web_search=True）
4. V5AgentWorker 等效路径验证

运行方式：
    cd /Users/onetwo/Documents/trae_projects/OpenCopilot
    python scripts/workspace_chat_validation.py

注意：消耗真实 LLM token，预计 3-5 分钟。
"""

import os
import sys
import uuid
import time
import signal
import threading
import traceback
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

TIMEOUT_PER_CALL = 80
BANNER_WIDTH = 60


# ═══ 输出工具 ═══

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def banner(title: str):
    print(f"\n{Colors.CYAN}{'═' * BANNER_WIDTH}")
    print(f"  {title}")
    print(f"{'═' * BANNER_WIDTH}{Colors.RESET}")

def ok(msg: str, detail: str = ""):
    icon = f"{Colors.GREEN}✅{Colors.RESET}"
    line = f"  {icon} {msg}"
    if detail: line += f"  — {detail}"
    print(line)

def fail(msg: str, detail: str = ""):
    icon = f"{Colors.RED}❌{Colors.RESET}"
    line = f"  {icon} {msg}"
    if detail: line += f"  — {detail}"
    print(line)

def info(msg: str):
    print(f"  {Colors.YELLOW}ℹ{Colors.RESET} {msg}")


# ═══ 结果收集 ═══

class ResultCollector:
    def __init__(self):
        self.results = []

    def add(self, module: str, test: str, passed: bool,
            score: float = -1, detail: str = "", latency: float = -1):
        self.results.append({
            "module": module, "test": test, "passed": passed,
            "score": score, "detail": detail, "latency": latency,
        })

    @property
    def total(self):
        return len(self.results)

    @property
    def passed_count(self):
        return sum(1 for r in self.results if r["passed"])

    @property
    def failed_count(self):
        return self.total - self.passed_count

collector = ResultCollector()


# ═══ Pipeline 调用（与 V5AgentWorker 等效） ═══

def check_llm_available() -> Tuple[bool, str]:
    try:
        from opencopilot.agent.caller import call_agent_pipeline_sync
        cancel = threading.Event()
        chunks = []
        for chunk in call_agent_pipeline_sync(
            text="hi", action_type="chat",
            session_id=f"ws-val-{uuid.uuid4().hex[:6]}",
            context_source="chat", context_meta={},
            is_new_task=True, cancel_event=cancel, timeout=20,
        ):
            chunks.append(chunk)
            if len(chunks) >= 3:
                break
        return (True, f"Pipeline OK ({len(chunks)} chunks)") if chunks else (False, "Pipeline 返回空")
    except Exception as e:
        return False, str(e)


def call_workspace_pipeline(
    prompt: str,
    action_type: str,
    enable_web_search: bool = False,
    context_meta: dict = None,
    timeout: int = TIMEOUT_PER_CALL,
) -> Tuple[str, int, float]:
    """模拟 V5AgentWorker 的 pipeline 调用路径，返回 (full_text, chunk_count, latency_s)"""
    from opencopilot.agent.caller import call_agent_pipeline_sync

    full_text = ""
    chunk_count = 0
    cancel_event = threading.Event()
    t0 = time.time()

    def _alarm_handler(signum, frame):
        cancel_event.set()
        raise TimeoutError(f"LLM 调用超时（>{timeout}s）")

    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(timeout)
        for chunk in call_agent_pipeline_sync(
            text=prompt,
            action_type=action_type,
            session_id=f"ws-val-{uuid.uuid4().hex[:8]}",
            context_source="chat",             # Workspace Chat 固定 context_source
            context_meta=context_meta or {},
            is_new_task=(action_type != "chat"),  # 与 workspace.py 一致
            enable_web_search=enable_web_search,
            cancel_event=cancel_event,
            timeout=timeout,
        ):
            full_text += chunk
            chunk_count += 1
            if cancel_event.is_set():
                break
        signal.alarm(0)
    except TimeoutError:
        raise RuntimeError(f"LLM 调用超时（>{timeout}s）")
    finally:
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

    latency = time.time() - t0
    return full_text, chunk_count, latency


# ═══ 质量评分 ═══

def score_output(text: str, criteria: Dict[str, Any]) -> Tuple[float, list]:
    """通用质量评分 (0-5)"""
    score = 0.0
    notes = []

    # 1. 长度 (0-1)
    min_len = criteria.get("min_length", 30)
    actual_len = len(text.strip())
    if actual_len >= min_len:
        score += 1.0
        notes.append(f"长度达标: {actual_len} >= {min_len}")
    else:
        notes.append(f"长度不足: {actual_len} < {min_len}")

    # 2. 关键词覆盖 (0-2)
    keywords = criteria.get("keywords", [])
    if keywords:
        text_lower = text.lower()
        hits = [k for k in keywords if k.lower() in text_lower]
        ratio = len(hits) / len(keywords)
        score += ratio * 2.0
        notes.append(f"关键词命中: {len(hits)}/{len(keywords)} ({ratio:.0%})")

    # 3. 内容密度 (0-1): 非重复字符占比
    if actual_len > 50:
        unique_ratio = len(set(text)) / min(actual_len, 500)
        if unique_ratio > 0.15:
            score += 1.0
            notes.append(f"内容密度: {unique_ratio:.2f}")
        else:
            notes.append(f"内容密度低: {unique_ratio:.2f}")

    # 4. 结构完整性 (0-1): 有多段/列表/标题
    has_paragraphs = text.count("\n\n") >= 1
    has_list = bool(set("-•*") & set(text)) or text.count("\n-") >= 2
    has_heading = "#" in text or text[:5].isupper()
    structure_score = sum([has_paragraphs, has_list, has_heading]) / 3
    score += structure_score
    notes.append(f"结构: 段落={has_paragraphs} 列表={has_list} 标题={has_heading}")

    return min(score, 5.0), notes


# ═══════════════════════════════════════════════════
# Part 1: 意图检测准确性（离线，不消耗 LLM token）
# ═══════════════════════════════════════════════════

def test_intent_detection():
    banner("Part 1: 意图检测准确性（离线验证）")
    from gui.v5.workspace import _detect_action_type

    test_cases = [
        # (输入文本, 预期 action_type, 场景说明)
        ("帮我做个产品介绍PPT", "ppt", "PPT生成"),
        ("把这段翻译成英文", "translate", "翻译"),
        ("解释一下这段代码的意思", "explain", "代码解释"),
        ("这段代码有bug，帮我修复", "fix", "代码修复"),
        ("帮我润色一下这段文字", "polish", "文本润色"),
        ("帮我做一下代码审查", "code_review", "代码审查"),
        ("你好，介绍一下你自己", "chat", "普通对话"),
        ("帮我调研下agent memory 最新技术并以一个md 文件形式输出", "research", "联网调研"),
        ("搜索一下最新的AI agent框架", "research", "搜索"),
        ("state of the art in multi-agent systems", "research", "SOTA调研"),
        ("帮我写一份技术方案", "chat", "不应误判为research"),
        ("请帮我生成一个关于AI技术的演示文稿", "ppt", "演示文稿"),
        ("TypeError: cannot unpack non-iterable", "fix", "异常修复"),
        ("帮我看看这个函数是干什么的", "explain", "函数解释"),
    ]

    passed = 0
    failed_list = []
    for text, expected, desc in test_cases:
        action, conf, kws = _detect_action_type(text)
        is_ok = action == expected
        if is_ok:
            passed += 1
            ok(f"[{desc}] \"{text[:35]}\" → {action} (conf={conf})")
        else:
            failed_list.append((text, expected, action, conf))
            fail(f"[{desc}] \"{text[:35]}\" → {action} (expected {expected}, conf={conf})")
        collector.add("意图检测", desc, is_ok, conf)

    total = len(test_cases)
    info(f"\n  意图检测: {passed}/{total} 通过 ({passed/total:.0%})")
    return passed == total


# ═══════════════════════════════════════════════════
# Part 2: Workspace Chat 全链路 LLM 验证
# ═══════════════════════════════════════════════════

def test_workspace_module(name: str, action_type: str, prompt: str,
                          context_meta: dict, criteria: dict,
                          enable_web_search: bool = False):
    """测试单个 action_type 的 Workspace Chat 等效链路"""
    print(f"\n  {Colors.BOLD}📋 {name} (action={action_type}, web_search={enable_web_search}){Colors.RESET}")
    t0 = time.time()
    try:
        text, chunks, latency = call_workspace_pipeline(
            prompt, action_type,
            enable_web_search=enable_web_search,
            context_meta=context_meta,
        )
        if not text.strip():
            fail("输出为空")
            collector.add(name, "output_not_empty", False, 0, "输出为空", latency)
            return

        ok(f"Pipeline 完成: {chunks} chunks, {latency:.1f}s, {len(text)} chars")

        # 评分
        score, notes = score_output(text, criteria)
        label = "优秀" if score >= 4 else "良好" if score >= 3 else "及格" if score >= 2 else "不及格"
        ok(f"质量评分: {score:.1f}/5.0 ({label})")
        for n in notes:
            info(f"  {n}")

        # 输出预览
        preview = text[:200].replace("\n", " ")
        info(f"  预览: {preview}...")

        collector.add(name, "quality_score", score >= 2, score,
                       f"chunks={chunks} latency={latency:.1f}s chars={len(text)}",
                       latency)

    except Exception as e:
        fail(f"Pipeline 调用失败: {e}")
        collector.add(name, "pipeline_call", False, 0, str(e), time.time() - t0)
        traceback.print_exc()


def run_workspace_llm_tests():
    banner("Part 2: Workspace Chat 全链路 LLM 验证（真实调用）")

    available, msg = check_llm_available()
    if not available:
        fail(f"LLM 服务不可用: {msg}")
        info("跳过所有 LLM 测试。请检查 config.json 中的 API key 配置。")
        return

    info(f"LLM 服务: {msg}")

    # ── Test 1: Chat 基础对话 ──
    test_workspace_module(
        name="Chat 自由对话",
        action_type="chat",
        prompt="你好！我正在使用 Workspace 的 Chat 面板，你能帮我做些什么？",
        context_meta={"context_source": "workspace_chat"},
        criteria={
            "min_length": 30,
            "keywords": ["你好", "帮助", "可以", "能够", "助手", "支持"],
        },
    )

    # ── Test 2: Explain 代码解释 ──
    code = '''
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
'''
    test_workspace_module(
        name="Explain 代码解释",
        action_type="explain",
        prompt=f"请解释以下代码:\n\n{code}",
        context_meta={"context_source": "workspace_chat", "source_text": code},
        criteria={
            "min_length": 80,
            "keywords": ["二分", "搜索", "查找", "数组", "中间", "索引", "目标"],
        },
    )

    # ── Test 3: Fix 代码修复 ──
    buggy = '''
def flatten_list(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            flatten_list(item)
        else:
            result.append(item)
    return result
'''
    test_workspace_module(
        name="Fix 代码修复",
        action_type="fix",
        prompt=f"请修复以下代码中的问题:\n\n{buggy}",
        context_meta={"context_source": "workspace_chat", "source_text": buggy},
        criteria={
            "min_length": 50,
            "keywords": ["extend", "result", "return", "递归", "列表", "append"],
        },
    )

    # ── Test 4: Translate 翻译 ──
    test_workspace_module(
        name="Translate 翻译",
        action_type="translate",
        prompt="请将以下文本翻译为英文:\n\n人工智能正在深刻改变我们的工作方式，从自动化办公到智能决策。",
        context_meta={"context_source": "workspace_chat"},
        criteria={
            "min_length": 30,
            "keywords": ["artificial intelligence", "work", "automation", "decision"],
        },
    )

    # ── Test 5: Polish 润色 ──
    test_workspace_module(
        name="Polish 文本润色",
        action_type="polish",
        prompt="请润色优化以下文本:\n\n这个AI产品功能挺多的，用起来还行，就是有时候有点卡，不过总体来说还可以。",
        context_meta={"context_source": "workspace_chat"},
        criteria={
            "min_length": 30,
            "keywords": ["功能", "体验", "产品", "值得", "流畅"],
        },
    )

    # ── Test 6: Code Review 代码审查 ──
    test_workspace_module(
        name="Code Review 代码审查",
        action_type="code_review",
        prompt=f"请对以下代码进行审查:\n\n```python{code}```",
        context_meta={"context_source": "workspace_chat", "source_text": code},
        criteria={
            "min_length": 100,
            "keywords": ["复杂度", "边界", "性能", "安全", "建议", "问题"],
        },
    )

    # ── Test 7: PPT 生成 ──
    test_workspace_module(
        name="PPT 大纲生成",
        action_type="ppt",
        prompt="请根据以下内容生成 PPT 大纲。\n\n要求：输出 JSON 数组格式，每页包含 type/title/items。\n\n内容：AI办公助手是一款集成大语言模型的桌面应用，支持文档生成、代码辅助、翻译润色等功能。目标用户是知识工作者，核心价值是提升办公效率。",
        context_meta={"context_source": "workspace_chat", "ppt_mode": True, "output_format": "json_slides"},
        criteria={
            "min_length": 100,
            "keywords": ["title", "items", "AI", "办公", "功能"],
        },
    )

    # ── Test 8: Research 联网调研（核心新能力） ──
    test_workspace_module(
        name="Research 联网调研（Agent Memory）",
        action_type="research",
        prompt="帮我调研下 agent memory 最新技术，包括主流的 memory 架构方案、开源框架、以及在实际 agent 系统中的应用案例，以一个 md 文件形式输出。",
        context_meta={"context_source": "workspace_chat", "research_mode": True, "output_format": "markdown_report"},
        enable_web_search=True,
        criteria={
            "min_length": 200,
            "keywords": ["memory", "agent", "记忆", "架构", "框架", "检索", "存储"],
        },
    )


# ═══════════════════════════════════════════════════
# Part 3: 汇总报告
# ═══════════════════════════════════════════════════

def print_summary():
    banner("验证汇总报告")
    total = collector.total
    passed = collector.passed_count
    failed = collector.failed_count

    # 按模块汇总
    modules = {}
    for r in collector.results:
        m = r["module"]
        if m not in modules:
            modules[m] = {"total": 0, "passed": 0, "scores": []}
        modules[m]["total"] += 1
        if r["passed"]:
            modules[m]["passed"] += 1
        if r["score"] >= 0:
            modules[m]["scores"].append(r["score"])

    print(f"\n  {'模块':<30} {'通过':<8} {'平均分':<10} {'状态'}")
    print(f"  {'─'*60}")
    for m, stats in modules.items():
        avg = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else -1
        status = "✅" if stats["passed"] == stats["total"] else "⚠️" if stats["passed"] > 0 else "❌"
        score_str = f"{avg:.1f}/5.0" if avg >= 0 else "-"
        print(f"  {m:<30} {stats['passed']}/{stats['total']:<6} {score_str:<10} {status}")

    print(f"\n  总计: {passed}/{total} 通过 ({passed/total:.0%})")

    # 质量评分汇总
    all_scores = [r["score"] for r in collector.results if r["score"] >= 0]
    llm_scores = [r["score"] for r in collector.results
                  if r["score"] >= 0 and r["module"] != "意图检测"]
    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)
        print(f"  综合评分: {avg_score:.1f}/5.0")
    if llm_scores:
        print(f"  LLM 质量评分: avg={sum(llm_scores)/len(llm_scores):.1f}/5.0")

    # 延迟汇总
    latencies = [r["latency"] for r in collector.results if r["latency"] >= 0]
    if latencies:
        print(f"  延迟: avg={sum(latencies)/len(latencies):.1f}s, max={max(latencies):.1f}s, min={min(latencies):.1f}s")

    # 最终判定：所有测试通过 + LLM 质量分 >= 2.0
    avg_llm_score = sum(llm_scores) / len(llm_scores) if llm_scores else 0
    all_passed = passed == total and avg_llm_score >= 2.0
    if all_passed:
        print(f"\n  {Colors.GREEN}{'='*40}")
        print(f"  ✅ 全部验证通过，Workspace Chat 生产可用")
        print(f"  {'='*40}{Colors.RESET}")
    else:
        print(f"\n  {Colors.RED}{'='*40}")
        print(f"  ❌ 存在未通过的验证项，请检查")
        print(f"  {'='*40}{Colors.RESET}")


# ═══ 入口 ═══

def main():
    print(f"\n{Colors.BOLD}{'#'*BANNER_WIDTH}")
    print(f"  Workspace Chat 全链路生产环境验证")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*BANNER_WIDTH}{Colors.RESET}")

    # Part 1: 意图检测（离线）
    test_intent_detection()

    # Part 2: LLM 全链路验证
    run_workspace_llm_tests()

    # Part 3: 汇总报告
    print_summary()


if __name__ == "__main__":
    main()
