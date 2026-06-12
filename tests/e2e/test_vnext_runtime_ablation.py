"""
vNext Runtime Orchestrator 自研消融评测脚本

对同一输入比较：
1. self_hosted_full            - 完整编排
2. self_hosted_no_planner      - 关闭 Planner
3. self_hosted_no_context      - 关闭上下文前缀
4. self_hosted_no_history      - 关闭会话历史

运行：
  python tests/e2e/test_vnext_runtime_ablation.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui_next.smart_copilot.runtime import SmartCopilotApiRuntime
from opencopilot.evaluation import JudgeBudget, evaluate_text_output


@dataclass
class AblationCase:
    action: str
    label: str
    prompt: str
    selection_text: str
    reference_text: str
    keywords: list[str]
    min_length: int = 80


@dataclass
class VariantResult:
    variant: str
    success: bool
    latency_ms: float
    output: str
    overall_score: float
    rule_score: float
    embedding_score: float
    semantic_score: float
    accuracy_score: float
    embedding_backend: str = ""
    judge_score: float | None = None
    judge_applied: bool = False
    judge_summary: str = ""
    error: str = ""


SIMPLE_CASES = [
    AblationCase(
        action="explain",
        label="多步代码解释",
        prompt=(
            "请先解释这段代码在做什么，再分析它的复杂度，最后给出一个更稳健的改写版本。\n\n"
            "def fib(n):\n"
            "    return n if n < 2 else fib(n-1) + fib(n-2)\n"
        ),
        selection_text="def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)",
        reference_text=(
            "这段 fib 是递归实现的斐波那契函数。时间复杂度为 O(2^n)，空间复杂度约为 O(n)。"
            "更稳健的写法可以改为迭代或动态规划，避免重复计算和栈深问题。"
        ),
        keywords=["复杂度", "递归", "改写", "fib"],
    ),
    AblationCase(
        action="code_review",
        label="多步代码审查",
        prompt=(
            "请分三步处理这段代码：先找出风险点，再说明为什么有问题，最后给出改进建议和示例代码。\n\n"
            "def process_users(users):\n"
            "    for user in users:\n"
            "        print(user['name'], user['email'])\n"
        ),
        selection_text="def process_users(users): ...",
        reference_text=(
            "这段代码的风险包括字段缺失导致 KeyError、敏感信息直接打印、缺少空值校验和异常处理。"
            "建议使用 get 或显式校验，并避免直接输出隐私数据。"
        ),
        keywords=["风险", "异常", "建议", "代码"],
    ),
]

COMPLEX_CASES = [
    AblationCase(
        action="code_review",
        label="复杂代码审查与修复方案",
        prompt=(
            "请按四步完成这段代码的深度审查：\n"
            "1. 找出至少 4 个高优先级问题，并按严重程度排序；\n"
            "2. 说明每个问题为什么会在生产环境触发；\n"
            "3. 给出一个可落地的重构方案，要求兼顾并发安全、敏感信息保护和缓存一致性；\n"
            "4. 给出关键修复代码与需要补充的回归测试。\n\n"
            "from threading import Thread\n"
            "cache = {}\n"
            "SETTINGS = {'ADMIN_TOKEN': 'configured-at-runtime'}\n\n"
            "def get_profile(user_id, fetch_remote, logger):\n"
            "    if user_id in cache:\n"
            "        return cache[user_id]\n"
            "    profile = fetch_remote(user_id, SETTINGS['ADMIN_TOKEN'])\n"
            "    cache[user_id] = profile\n"
            "    logger.info(f'user={user_id}, profile={profile}, auth_source=admin_token')\n"
            "    return profile\n\n"
            "def warmup(ids, fetch_remote, logger):\n"
            "    threads = []\n"
            "    for uid in ids:\n"
            "        t = Thread(target=get_profile, args=(uid, fetch_remote, logger))\n"
            "        threads.append(t)\n"
            "        t.start()\n"
            "    return len(threads)\n"
        ),
        selection_text=(
            "cache/SETTINGS/get_profile/warmup 这段代码涉及全局缓存、配置读取、远程拉取用户资料、"
            "并发预热和日志打印。"
        ),
        reference_text=(
            "高优先级问题至少应包括：敏感凭据读取与使用边界不清、日志泄漏敏感信息、全局缓存并发不安全、"
            "缓存缺少 TTL/失效策略、线程未 join 且异常无处理、远程失败会污染缓存。"
            "重构方向应包含：凭据通过依赖注入传入、脱敏日志、线程安全缓存或锁、失败不写缓存、"
            "加入超时/重试/熔断、补充并发与敏感信息回归测试。"
        ),
        keywords=["并发", "敏感", "缓存", "重构", "测试", "凭据"],
        min_length=220,
    ),
    AblationCase(
        action="chat",
        label="多约束方案设计",
        prompt=(
            "你是架构负责人，请基于下面约束给出一份可执行的实施方案。\n"
            "要求按 5 个部分输出：\n"
            "1. 先拆解核心约束与冲突；\n"
            "2. 设计推荐架构，并说明为什么不是另外两种候选架构；\n"
            "3. 说明数据隔离、权限边界和故障降级策略；\n"
            "4. 给出 3 阶段上线计划与每阶段验收指标；\n"
            "5. 给出最大风险与 mitigation。\n\n"
            "背景：我们要把自研智能体接入企业知识库与代码库，要求支持生产/开发环境隔离，"
            "单次复杂任务目标时延 < 12 秒，P0 场景必须允许人工接管。"
            "企业内网不能把原始代码和客户数据发到第三方服务。"
            "团队只有 2 个后端、1 个前端、1 个算法，8 周内要交付首版。"
            "候选架构 A: 单体同步调用；B: 编排层 + 工具执行层；C: 多 Agent 协作总线。"
        ),
        selection_text=(
            "场景：企业级自研智能体接入知识库与代码库，要求数据隔离、低时延、人工接管、"
            "不能外发敏感原始数据、8 周内交付。"
        ),
        reference_text=(
            "较优方案通常是选择 B: 编排层 + 工具执行层，因为它在 8 周交付、可控复杂度、"
            "安全隔离和人工接管之间更平衡。回答应明确拆解时延、安全、资源与交付冲突，"
            "说明为何 A 难扩展、C 过重。还应给出生产/开发隔离、权限边界、失败降级、"
            "三阶段里程碑和验收指标，以及风险 mitigation。"
        ),
        keywords=["约束", "架构", "隔离", "降级", "阶段", "风险", "mitigation"],
        min_length=260,
    ),
    AblationCase(
        action="polish",
        label="长文档冲突梳理与重写",
        prompt=(
            "请对下面这份混乱的需求纪要进行重构，必须按四部分输出：\n"
            "1. 先列出互相冲突或不完整的需求点；\n"
            "2. 输出一版统一后的执行摘要；\n"
            "3. 给出风险清单与待确认问题；\n"
            "4. 再给一版适合发给研发团队的行动清单。\n\n"
            "纪要：产品说首版只做内部试用，不要求鉴权；安全说所有环境都必须做 SSO。"
            "老板要求 2 周内上线 demo，但研发说最少 6 周。"
            "客户希望支持上传合同、代码、截图三种内容，但算法同学说 OCR 和代码解析不能同时做。"
            "运营希望所有历史会话永久保存用于分析，但法务说生产数据 30 天后必须可删除。"
            "还希望支持用户一键导出全部会话。"
        ),
        selection_text=(
            "需求纪要同时包含鉴权、交付周期、多模态能力范围、会话留存与删除策略等冲突。"
        ),
        reference_text=(
            "高质量回答应先明确 SSO vs 内部试用、2 周 demo vs 6 周研发、OCR vs 代码解析资源冲突、"
            "永久留存 vs 30 天可删除之间的矛盾。然后统一成一个分阶段落地方案，区分 demo 与正式版范围，"
            "并输出风险、待确认问题和研发行动清单。"
        ),
        keywords=["冲突", "摘要", "风险", "待确认", "行动清单", "SSO"],
        min_length=220,
    ),
]


def _load_cases() -> tuple[str, list[AblationCase]]:
    mode = os.getenv("OPEN_COPILOT_ABLATION_TASK_MODE", "complex").strip().lower()
    if mode == "simple":
        return "simple", SIMPLE_CASES
    return "complex", COMPLEX_CASES

VARIANTS = {
    "self_hosted_full": {"provider": "self_hosted", "runtime_flags": {}},
    "self_hosted_no_planner": {"provider": "self_hosted", "runtime_flags": {"disable_planner": True}},
    "self_hosted_no_context": {"provider": "self_hosted", "runtime_flags": {"disable_context_prefix": True}},
    "self_hosted_no_history": {"provider": "self_hosted", "runtime_flags": {"disable_history": True}},
}


def quality_score(output: str, case: AblationCase) -> float:
    text = output.strip()
    if not text:
        return 0.0
    keyword_hits = sum(1 for kw in case.keywords if kw.lower() in text.lower())
    length_score = min(1.0, len(text) / max(case.min_length, 1))
    step_score = 1.0 if any(token in text for token in ["1.", "第一", "先", "最后"]) else 0.5
    keyword_score = keyword_hits / max(len(case.keywords), 1)
    return round((0.35 * length_score + 0.45 * keyword_score + 0.20 * step_score) * 100, 2)


def run_variant(
    client: httpx.Client,
    case: AblationCase,
    variant: str,
    config: dict[str, Any],
    judge_budget: JudgeBudget,
) -> VariantResult:
    started = time.time()
    try:
        snapshot_resp = client.post(
            "/vnext/context/snapshots",
            json={
                "trigger": "runtime_ablation",
                "source_app": "benchmark",
                "selection_text": case.selection_text,
                "document_title": case.label,
                "metadata": {
                    "context_source": "selection",
                    "context_meta": {
                        "source_text": case.selection_text,
                        "runtime_flags": config["runtime_flags"],
                    },
                    "runtime_flags": config["runtime_flags"],
                },
            },
        )
        snapshot_resp.raise_for_status()
        snapshot_id = snapshot_resp.json()["context_snapshot_id"]

        task_resp = client.post(
            "/vnext/tasks",
            json={
                "action": case.action,
                "user_input": case.prompt,
                "context_snapshot_id": snapshot_id,
                "agent_preferences": {
                    "provider": config["provider"],
                    "model": "default",
                    "temperature": 0.2,
                },
            },
        )
        task_resp.raise_for_status()
        task_id = task_resp.json()["task_id"]

        deadline = time.time() + 120
        task_payload = {}
        while time.time() < deadline:
            task_payload = client.get(f"/vnext/tasks/{task_id}").json()
            if task_payload["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.25)

        latency_ms = round((time.time() - started) * 1000, 2)
        if task_payload.get("status") != "succeeded":
            return VariantResult(
                variant=variant,
                success=False,
                latency_ms=latency_ms,
                output="",
                overall_score=0.0,
                rule_score=0.0,
                embedding_score=0.0,
                semantic_score=0.0,
                accuracy_score=0.0,
                error=json.dumps(task_payload.get("error", {}), ensure_ascii=False),
            )

        output = task_payload.get("result", {}).get("summary", "")
        rule_score = quality_score(output, case)
        quality = evaluate_text_output(
            instruction=case.prompt,
            output=output,
            context_text=case.selection_text,
            reference_text=case.reference_text,
            keywords=case.keywords,
            judge_budget=judge_budget,
        )
        overall_score = round(
            0.25 * rule_score + 0.25 * quality["semantic_similarity"] + 0.20 * quality["description_accuracy"] + 0.30 * quality["overall_score"],
            2,
        )
        return VariantResult(
            variant=variant,
            success=True,
            latency_ms=latency_ms,
            output=output,
            overall_score=overall_score,
            rule_score=rule_score,
            embedding_score=quality["embedding_similarity"],
            semantic_score=quality["semantic_similarity"],
            accuracy_score=quality["description_accuracy"],
            embedding_backend=quality["embedding_backend"],
            judge_score=quality["judge_score"],
            judge_applied=quality["judge_applied"],
            judge_summary=quality["judge_summary"],
        )
    except Exception as exc:
        return VariantResult(
            variant=variant,
            success=False,
            latency_ms=round((time.time() - started) * 1000, 2),
            output="",
            overall_score=0.0,
            rule_score=0.0,
            embedding_score=0.0,
            semantic_score=0.0,
            accuracy_score=0.0,
            error=str(exc),
        )


def main() -> None:
    runtime = SmartCopilotApiRuntime()
    try:
        base_url = runtime.ensure_ready()
        judge_budget = JudgeBudget.from_env(default_max_cases=12)
        task_mode, cases = _load_cases()
        report_lines = [
            "# vNext Runtime Orchestrator 自研消融报告",
            "",
            f"- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Base URL: {base_url}",
            f"- Task Mode: {task_mode}",
            f"- LLM Judge: {'enabled' if judge_budget.enabled else 'disabled'} / max_cases={judge_budget.max_cases}",
            f"- Embedding Backend: {os.getenv('OPEN_COPILOT_EMBEDDING_BACKEND', 'auto')}",
            "",
        ]

        with httpx.Client(base_url=base_url, timeout=httpx.Timeout(10.0, read=180.0)) as client:
            all_results: dict[str, list[VariantResult]] = {key: [] for key in VARIANTS}
            for case in cases:
                report_lines.append(f"## {case.label}")
                report_lines.append("")
                report_lines.append("| Variant | Success | Latency(ms) | Overall | Rule | Embed | Semantic | Accuracy | Judge | Preview |")
                report_lines.append("|---------|---------|-------------|---------|------|-------|----------|----------|-------|---------|")
                for variant, config in VARIANTS.items():
                    result = run_variant(client, case, variant, config, judge_budget)
                    all_results[variant].append(result)
                    preview = (result.output or result.error).replace("\n", " ")[:80]
                    judge_display = f"{result.judge_score:.1f}" if result.judge_score is not None else "-"
                    report_lines.append(
                        f"| {variant} | {'Y' if result.success else 'N'} | {result.latency_ms:.1f} | {result.overall_score:.1f} | {result.rule_score:.1f} | {result.embedding_score:.1f} | {result.semantic_score:.1f} | {result.accuracy_score:.1f} | {judge_display} | {preview} |"
                    )
                    if result.embedding_backend:
                        report_lines.append(f"- `{variant}` Embedding: {result.embedding_backend}")
                    if result.judge_summary:
                        report_lines.append(f"- `{variant}` Judge: {result.judge_summary}")
                report_lines.append("")

            report_lines.append("## 汇总")
            report_lines.append("")
            report_lines.append("| Variant | Avg Overall | Avg Rule | Avg Embed | Avg Semantic | Avg Accuracy | Judge Coverage | Avg Latency(ms) |")
            report_lines.append("|---------|-------------|----------|-----------|--------------|--------------|---------------|-----------------|")
            full_avg = 0.0
            for variant, results in all_results.items():
                avg_overall = sum(item.overall_score for item in results) / max(len(results), 1)
                avg_rule = sum(item.rule_score for item in results) / max(len(results), 1)
                avg_embed = sum(item.embedding_score for item in results) / max(len(results), 1)
                avg_semantic = sum(item.semantic_score for item in results) / max(len(results), 1)
                avg_accuracy = sum(item.accuracy_score for item in results) / max(len(results), 1)
                judge_coverage = sum(1 for item in results if item.judge_applied) / max(len(results), 1) * 100
                avg_latency = sum(item.latency_ms for item in results) / max(len(results), 1)
                if variant == "self_hosted_full":
                    full_avg = avg_overall
                report_lines.append(
                    f"| {variant} | {avg_overall:.2f} | {avg_rule:.2f} | {avg_embed:.2f} | {avg_semantic:.2f} | {avg_accuracy:.2f} | {judge_coverage:.0f}% | {avg_latency:.2f} |"
                )

            report_lines.append("")
            report_lines.append("## 增益")
            report_lines.append("")
            for variant, results in all_results.items():
                if variant == "self_hosted_full":
                    continue
                avg_score = sum(item.overall_score for item in results) / max(len(results), 1)
                delta = full_avg - avg_score
                report_lines.append(f"- `self_hosted_full` 相对 `{variant}` 的质量差值: {delta:+.2f}")

        output_path = PROJECT_ROOT / "output" / "vnext_runtime_ablation_report.md"
        output_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"[OK] report saved to {output_path}")
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    main()
