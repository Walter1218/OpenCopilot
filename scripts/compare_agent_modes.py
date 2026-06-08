#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from opencopilot.agent.caller import call_agent_pipeline_sync
from smart_copilot_api import app


@dataclass(slots=True)
class CompareCase:
    module: str
    action_type: str
    prompt: str
    context_source: str
    selection_text: str = ""
    document_title: str = ""
    context_meta: dict[str, Any] | None = None
    expected_keywords: list[str] | None = None


CASES: list[CompareCase] = [
    CompareCase(
        module="Chat",
        action_type="chat",
        prompt="你好，我现在在做一个 AI 办公助手。请用 3 点说明你能帮助开发团队做什么。",
        context_source="chat",
        expected_keywords=["开发", "代码", "方案", "测试", "文档"],
    ),
    CompareCase(
        module="Explain",
        action_type="explain",
        prompt="请解释下面这段 Python 代码的作用和潜在问题。",
        context_source="selection",
        selection_text=(
            "def lru_cache(maxsize=128):\n"
            "    def decorator(func):\n"
            "        cache = {}\n"
            "        order = []\n"
            "        def wrapper(*args):\n"
            "            if args in cache:\n"
            "                order.remove(args)\n"
            "                order.append(args)\n"
            "                return cache[args]\n"
            "            result = func(*args)\n"
            "            cache[args] = result\n"
            "            order.append(args)\n"
            "            if len(cache) > maxsize:\n"
            "                oldest = order.pop(0)\n"
            "                del cache[oldest]\n"
            "            return result\n"
            "        return wrapper\n"
            "    return decorator\n"
        ),
        document_title="cache_utils.py",
        context_meta={"source_text": "lru_cache snippet"},
        expected_keywords=["缓存", "装饰器", "LRU", "淘汰", "性能"],
    ),
    CompareCase(
        module="Polish",
        action_type="polish",
        prompt="请润色下面这段产品描述，要求更专业、更顺畅。",
        context_source="selection",
        selection_text="这个产品功能挺多的，用起来还行，就是有时候有点卡，不过总体来说还可以，值得试试。",
        document_title="product_intro.md",
        context_meta={"source_text": "产品描述"},
        expected_keywords=["产品", "体验", "性能", "流畅", "价值"],
    ),
    CompareCase(
        module="CodeReview",
        action_type="code_review",
        prompt="请对下面代码做代码审查，指出风险并给出改进建议。",
        context_source="selection",
        selection_text=(
            "def merge_sorted_lists(a, b):\n"
            "    result = []\n"
            "    i, j = 0, 0\n"
            "    while i < len(a) and j < len(b):\n"
            "        if a[i] <= b[j]:\n"
            "            result.append(a[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            result.append(b[j])\n"
            "            j += 1\n"
            "    return result\n"
        ),
        document_title="merge.py",
        context_meta={"source_text": "merge_sorted_lists"},
        expected_keywords=["问题", "风险", "剩余", "边界", "建议"],
    ),
    CompareCase(
        module="Translate",
        action_type="translate",
        prompt="请把下面中文翻译为英文。",
        context_source="selection",
        selection_text="人工智能正在深刻改变我们的工作方式，从智能客服到自动化编程，AI 技术已经进入日常办公。",
        document_title="translation.txt",
        context_meta={"source_language": "中文", "target_language": "英文"},
        expected_keywords=["artificial intelligence", "AI", "work", "office"],
    ),
    CompareCase(
        module="PPT",
        action_type="ppt",
        prompt=(
            "请根据下面内容生成一份 5 页左右的 PPT 大纲，"
            "每页给出标题和 3-5 个要点，主题是 AI 办公助手产品方案。"
        ),
        context_source="studio",
        selection_text=(
            "目标用户是企业知识工作者。核心能力包括：会议纪要、文档总结、代码辅助、"
            "知识检索、任务跟踪、多端接入。希望突出 ROI、落地路径和实施风险。"
        ),
        document_title="ai_office_solution.md",
        context_meta={"input_text_len": 66},
        expected_keywords=["目标", "能力", "价值", "风险", "实施"],
    ),
]


@dataclass(slots=True)
class ModeResult:
    mode: str
    module: str
    action_type: str
    success: bool
    latency_sec: float
    text_length: int
    keyword_hits: int
    keyword_total: int
    quality_score: float
    preview: str
    error: str = ""


def score_output(text: str, expected_keywords: list[str] | None) -> tuple[int, int, float]:
    normalized = text.lower()
    keywords = expected_keywords or []
    hits = sum(1 for keyword in keywords if keyword.lower() in normalized)

    score = 0.0
    if len(text.strip()) >= 80:
        score += 2.0
    elif len(text.strip()) >= 30:
        score += 1.0

    if keywords:
        score += (hits / len(keywords)) * 2.0

    if "\n" in text or "-" in text or "1." in text:
        score += 1.0

    return hits, len(keywords), min(score, 5.0)


def run_v5_case(case: CompareCase, timeout: float) -> ModeResult:
    start = time.time()
    try:
        chunks: list[str] = []
        for chunk in call_agent_pipeline_sync(
            text=f"{case.prompt}\n\n{case.selection_text}".strip(),
            action_type=case.action_type,
            session_id=f"cmp-v5-{uuid.uuid4().hex[:8]}",
            context_source=case.context_source,
            context_meta=case.context_meta or {},
            is_new_task=(case.action_type != "chat"),
            timeout=timeout,
        ):
            chunks.append(chunk)
        text = "".join(chunks)
        latency = time.time() - start
        hits, total, quality = score_output(text, case.expected_keywords)
        return ModeResult(
            mode="v5_self_agent",
            module=case.module,
            action_type=case.action_type,
            success=bool(text.strip()),
            latency_sec=latency,
            text_length=len(text),
            keyword_hits=hits,
            keyword_total=total,
            quality_score=quality,
            preview=text[:240].replace("\n", " "),
        )
    except Exception as exc:
        return ModeResult(
            mode="v5_self_agent",
            module=case.module,
            action_type=case.action_type,
            success=False,
            latency_sec=time.time() - start,
            text_length=0,
            keyword_hits=0,
            keyword_total=len(case.expected_keywords or []),
            quality_score=0.0,
            preview="",
            error=str(exc),
        )


def run_hermes_case(case: CompareCase, timeout: float) -> ModeResult:
    start = time.time()
    try:
        with TestClient(app) as client:
            context_response = client.post(
                "/vnext/context/snapshots",
                json={
                    "trigger": "compare_script",
                    "source_app": "Cursor",
                    "selection_text": case.selection_text,
                    "document_title": case.document_title,
                    "metadata": {"compare_module": case.module},
                },
            )
            context_response.raise_for_status()
            context_snapshot_id = context_response.json()["context_snapshot_id"]

            task_response = client.post(
                "/vnext/tasks",
                json={
                    "action": case.action_type,
                    "user_input": case.prompt,
                    "context_snapshot_id": context_snapshot_id,
                    "agent_preferences": {"provider": "hermes_local"},
                },
            )
            task_response.raise_for_status()
            task_id = task_response.json()["task_id"]

            deadline = time.time() + timeout
            while time.time() < deadline:
                events_response = client.get(f"/vnext/tasks/{task_id}/events")
                events_response.raise_for_status()
                events = events_response.json().get("events", [])
                if any(event.get("type") in {"task.completed", "task.failed", "task.cancelled"} for event in events):
                    break
                time.sleep(0.35)

            task_state = client.get(f"/vnext/tasks/{task_id}")
            task_state.raise_for_status()
            payload = task_state.json()
            result = payload.get("result") or {}
            text = result.get("summary", "")
            error = payload.get("error") or {}
            latency = time.time() - start
            hits, total, quality = score_output(text, case.expected_keywords)
            return ModeResult(
                mode="hermes_vnext",
                module=case.module,
                action_type=case.action_type,
                success=payload.get("status") == "succeeded" and bool(text.strip()),
                latency_sec=latency,
                text_length=len(text),
                keyword_hits=hits,
                keyword_total=total,
                quality_score=quality,
                preview=text[:240].replace("\n", " "),
                error=error.get("message", ""),
            )
    except Exception as exc:
        return ModeResult(
            mode="hermes_vnext",
            module=case.module,
            action_type=case.action_type,
            success=False,
            latency_sec=time.time() - start,
            text_length=0,
            keyword_hits=0,
            keyword_total=len(case.expected_keywords or []),
            quality_score=0.0,
            preview="",
            error=str(exc),
        )


def print_result(result: ModeResult) -> None:
    status = "PASS" if result.success else "FAIL"
    print(
        f"[{status}] {result.mode} | {result.module} | latency={result.latency_sec:.2f}s "
        f"| chars={result.text_length} | quality={result.quality_score:.2f} "
        f"| keywords={result.keyword_hits}/{result.keyword_total}"
    )
    if result.preview:
        print(f"  preview: {result.preview}")
    if result.error:
        print(f"  error: {result.error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare Hermes/vnext and v5 self-agent across modules")
    parser.add_argument(
        "--modules",
        default="chat,explain,polish,codereview,translate,ppt",
        help="Comma-separated module names from: chat,explain,polish,codereview,translate,ppt",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="Timeout in seconds for each mode/case",
    )
    parser.add_argument(
        "--output",
        default="output/agent_compare_report.json",
        help="Where to write the JSON report",
    )
    return parser


def normalize_module_name(name: str) -> str:
    return name.strip().lower().replace("_", "").replace("-", "")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected = {normalize_module_name(name) for name in args.modules.split(",") if name.strip()}
    selected_cases = [case for case in CASES if normalize_module_name(case.module) in selected]
    if not selected_cases:
        raise SystemExit("No valid modules selected")

    results: list[ModeResult] = []
    for case in selected_cases:
        print(f"\n=== Module: {case.module} ({case.action_type}) ===")
        v5_result = run_v5_case(case, timeout=args.timeout)
        print_result(v5_result)
        results.append(v5_result)

        hermes_result = run_hermes_case(case, timeout=args.timeout)
        print_result(hermes_result)
        results.append(hermes_result)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nReport written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
