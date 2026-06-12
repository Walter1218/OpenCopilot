#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from gui.v5.agent_worker import V5AgentWorker
from opencopilot.agent.caller import call_agent_pipeline_sync
from opencopilot.capabilities.ppt.ai_chat_widget import AIWorker
from opencopilot.capabilities.ppt.render_command import RenderCommandParser
from opencopilot.capabilities.ppt.render_executor import RenderDispatcher


OUTPUT_JSON = PROJECT_ROOT / "output" / "ppt_cocreation_benchmark.json"
OUTPUT_MD = PROJECT_ROOT / "output" / "ppt_cocreation_benchmark.md"


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    label: str
    instruction: str
    original_text: str
    slides: list[dict[str, Any]]
    current_index: int
    expected_render_types: list[str] = field(default_factory=list)
    require_title_slot: bool = False
    require_recommendations: bool = False
    expected_layouts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ModeResult:
    mode: str
    latency_sec: float
    raw_length: int
    render_command_count: int
    parse_success: bool
    current_page_hit_rate: float
    expected_type_hit_rate: float
    title_slot_hit: bool
    recommendation_hit: bool
    layout_hit: bool
    source_anchor_rate: float
    execution_success_rate: float
    total_score: float
    preview: str
    title_after: str
    item_types_after: list[str]
    command_brief: list[dict[str, Any]]
    error: str = ""


@dataclass(slots=True)
class CaseReport:
    case_id: str
    label: str
    summary: str
    self_agent: ModeResult
    hermes: ModeResult


def _normalize_preview(text: str, *, limit: int = 800) -> str:
    return text[:limit].replace("\n", " ")


def _recommendation_terms() -> tuple[str, ...]:
    return (
        "focus",
        "improve",
        "accelerate",
        "strengthen",
        "expand",
        "optimize",
        "priority",
        "action",
        "recommend",
    )


def _build_user_message(case: BenchmarkCase) -> str:
    worker = AIWorker()
    worker.set_task(
        case.instruction,
        deepcopy(case.slides),
        case.current_index,
        case.original_text,
        f"bench-{case.case_id}",
    )
    return worker._build_user_message()


def _run_self_agent(user_message: str) -> tuple[str, str, float]:
    start = time.time()
    chunks: list[str] = []
    try:
        for chunk in call_agent_pipeline_sync(
            text=user_message,
            action_type="chat",
            session_id=f"bench-self-{uuid.uuid4().hex[:8]}",
            context_source="ppt_editor",
            is_new_task=True,
            timeout=180,
        ):
            chunks.append(chunk)
        return "".join(chunks), "", time.time() - start
    except Exception as exc:
        return "".join(chunks), str(exc), time.time() - start


def _run_hermes(case: BenchmarkCase, user_message: str) -> tuple[str, str, float]:
    start = time.time()
    finished: list[str] = []
    errors: list[str] = []
    current_slide = case.slides[case.current_index]
    worker = V5AgentWorker(
        prompt=user_message,
        action_type="chat",
        session_id=f"bench-hermes-{uuid.uuid4().hex[:8]}",
        context_source="ppt_editor",
        context_meta={
            "ppt_cocreation": True,
            "slides_count": len(case.slides),
            "current_index": case.current_index,
            "current_slide_title": current_slide.get("title", ""),
            "current_slide_layout": current_slide.get("layout", ""),
            "original_text_len": len(case.original_text),
            "benchmark_case_id": case.case_id,
        },
        is_new_task=True,
    )
    worker.finished_signal.connect(lambda text: finished.append(text))
    worker.error_signal.connect(lambda text: errors.append(text))
    worker.run()
    return (finished[-1] if finished else "", errors[-1] if errors else "", time.time() - start)


def _evaluate(case: BenchmarkCase, mode: str, raw_text: str, error: str, latency_sec: float) -> ModeResult:
    commands = RenderCommandParser.parse(raw_text, case.original_text)
    parse_success = bool(commands)
    dispatcher = RenderDispatcher(deepcopy(case.slides), case.original_text)
    results = dispatcher.dispatch_from_render_commands(commands, current_index=case.current_index) if commands else []
    executed_slides = dispatcher.executor.slides_data
    target_slide = executed_slides[case.current_index]

    current_page_hits = 0
    type_hits = 0
    title_slot_hit = False
    recommendation_hit = False
    layout_hit = False
    source_anchor_hits = 0
    command_brief: list[dict[str, Any]] = []

    expected_types = set(case.expected_render_types)
    observed_types = set()

    for command in commands:
        if command.slide_index in (-1, case.current_index):
            current_page_hits += 1
        if command.render_type in expected_types:
            observed_types.add(command.render_type)
        if command.source_text.strip():
            source_anchor_hits += 1
        if command.slot == "title":
            title_slot_hit = True
        if case.require_title_slot and command.slot == "title":
            if command.render_params.get("title") or command.render_params.get("text"):
                title_slot_hit = True
        if case.expected_layouts and (
            command.render_type in case.expected_layouts
            or command.render_params.get("layout") in case.expected_layouts
        ):
            layout_hit = True

        combined_text = " ".join(
            str(value)
            for value in (
                command.render_params.get("text", ""),
                command.render_params.get("title", ""),
                json.dumps(command.render_params, ensure_ascii=False),
            )
        ).lower()
        if sum(1 for term in _recommendation_terms() if term in combined_text) >= 2:
            recommendation_hit = True

        command_brief.append(
            {
                "slide_index": command.slide_index,
                "slot": command.slot,
                "render_type": command.render_type,
                "title": command.render_params.get("title", ""),
                "source_text": command.source_text[:140],
            }
        )

    if expected_types:
        type_hits = len(observed_types)
        expected_type_hit_rate = type_hits / len(expected_types)
    else:
        expected_type_hit_rate = 1.0

    current_page_hit_rate = current_page_hits / len(commands) if commands else 0.0
    source_anchor_rate = source_anchor_hits / len(commands) if commands else 0.0
    execution_success_rate = (
        sum(1 for result in results if result.success) / len(results) if results else 0.0
    )

    title_after = target_slide.get("title", "")
    item_types_after = [item.get("content_type", "text") for item in target_slide.get("items", [])]
    item_texts_after = [item.get("text", "") for item in target_slide.get("items", [])]

    if case.require_recommendations and not recommendation_hit:
        recommendation_hit = sum(
            1
            for text in item_texts_after
            if any(term in text.lower() for term in _recommendation_terms())
        ) >= 2

    if case.expected_layouts and not layout_hit:
        layout_hit = target_slide.get("layout", "") in case.expected_layouts

    score = 0.0
    score += 1.5 if parse_success else 0.0
    score += current_page_hit_rate * 2.0
    score += expected_type_hit_rate * 2.0
    score += (1.0 if title_slot_hit else 0.0) if case.require_title_slot else 1.0
    score += (1.0 if recommendation_hit else 0.0) if case.require_recommendations else 1.0
    score += (1.0 if layout_hit else 0.0) if case.expected_layouts else 1.0
    score += source_anchor_rate * 1.0
    score += execution_success_rate * 1.5
    total_score = round((score / 11.0) * 10.0, 2)

    return ModeResult(
        mode=mode,
        latency_sec=round(latency_sec, 2),
        raw_length=len(raw_text),
        render_command_count=len(commands),
        parse_success=parse_success,
        current_page_hit_rate=round(current_page_hit_rate, 2),
        expected_type_hit_rate=round(expected_type_hit_rate, 2),
        title_slot_hit=title_slot_hit,
        recommendation_hit=recommendation_hit,
        layout_hit=layout_hit,
        source_anchor_rate=round(source_anchor_rate, 2),
        execution_success_rate=round(execution_success_rate, 2),
        total_score=total_score,
        preview=_normalize_preview(raw_text),
        title_after=title_after,
        item_types_after=item_types_after[:8],
        command_brief=command_brief[:8],
        error=error,
    )


def _make_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            case_id="exec_summary",
            label="Executive Summary With Chart And Table",
            instruction=(
                "Turn the current slide into a leadership-ready page. Use a conclusion-style title that "
                "highlights growth, convert the financial data into a bar chart, convert the product line "
                "differences into a comparison table, and add two crisp action recommendations."
            ),
            original_text=(
                "Executive summary: Total revenue in H1 2026 reached 850M RMB, up 32 percent year over year. "
                "Financial data: Q1 revenue was 380M RMB and Q2 revenue was 470M RMB. "
                "Product lines: Copilot Pro renewal 91 percent, Knowledge Hub renewal 84 percent, "
                "Meeting Bot trial-to-paid 27 percent. Management actions: focus on enterprise expansion, "
                "improve Meeting Bot conversion, and strengthen cross product selling."
            ),
            slides=[
                {"type": "title", "layout": "center", "title": "2026 H1 Business Review", "subtitle": "Leadership Review"},
                {
                    "type": "content",
                    "layout": "text_only",
                    "title": "Business Overview",
                    "items": [
                        {"level": 0, "text": "Revenue grew 32 percent year over year and enterprise plans led growth.", "content_type": "text"},
                        {"level": 0, "text": "Q1 revenue was 380M RMB and Q2 revenue was 470M RMB.", "content_type": "text"},
                        {"level": 0, "text": "Copilot Pro, Knowledge Hub, and Meeting Bot showed different retention patterns.", "content_type": "text"},
                        {"level": 0, "text": "We should expand enterprise sales and improve Meeting Bot conversion.", "content_type": "text"},
                    ],
                },
                {"type": "ending", "layout": "center", "title": "Thanks", "subtitle": "Q and A"},
            ],
            current_index=1,
            expected_render_types=["chart", "table", "text"],
            require_title_slot=True,
            require_recommendations=True,
        ),
        BenchmarkCase(
            case_id="flowchart_update",
            label="Onboarding Flow Update",
            instruction=(
                "Update the current slide for a customer onboarding review. Keep it concise, insert a risk check "
                "step after account creation, and convert the process into a clear flowchart."
            ),
            original_text=(
                "Customer onboarding currently follows these steps: submit company profile, create account, "
                "connect data source, run first sync, review dashboard, start pilot. Compliance asked us to add "
                "a risk review before data sync for enterprise accounts."
            ),
            slides=[
                {"type": "title", "layout": "center", "title": "Customer Onboarding", "subtitle": "Operations"},
                {
                    "type": "content",
                    "layout": "text_only",
                    "title": "Current Process",
                    "items": [
                        {"level": 0, "text": "Submit company profile", "content_type": "text"},
                        {"level": 0, "text": "Create account", "content_type": "text"},
                        {"level": 0, "text": "Connect data source", "content_type": "text"},
                        {"level": 0, "text": "Run first sync", "content_type": "text"},
                    ],
                },
            ],
            current_index=1,
            expected_render_types=["flowchart"],
            require_title_slot=False,
            require_recommendations=False,
        ),
        BenchmarkCase(
            case_id="layout_image",
            label="Product Hero Image Layout",
            instruction=(
                "Rework the current slide into an image-right layout. Keep one short positioning line, add a caption "
                "for the hero image, and make the page suitable for a product launch keynote."
            ),
            original_text=(
                "NovaPad X1 is a flagship tablet with a 5.8mm body, custom M3 chip, 14-hour battery life, and a "
                "studio-grade display. Marketing wants the page to feel premium and visual-first."
            ),
            slides=[
                {"type": "title", "layout": "center", "title": "NovaPad X1 Launch", "subtitle": "Marketing"},
                {
                    "type": "content",
                    "layout": "text_only",
                    "title": "Product Highlights",
                    "items": [
                        {"level": 0, "text": "5.8mm ultra-thin body", "content_type": "text"},
                        {"level": 0, "text": "Custom M3 chip", "content_type": "text"},
                        {"level": 0, "text": "14-hour battery life", "content_type": "text"},
                    ],
                },
            ],
            current_index=1,
            expected_render_types=["image_right", "text"],
            expected_layouts=["image_right"],
        ),
        BenchmarkCase(
            case_id="comparison_table",
            label="Competitor Comparison Table",
            instruction=(
                "Turn the current competitor bullets into a structured comparison table, sharpen the headline, "
                "and keep the tone suitable for an executive strategy review."
            ),
            original_text=(
                "DevFlow 2.0 uses a native AI engine and zero-config onboarding. GitLab Premium is feature rich but "
                "has a steep learning curve. Jenkins X is flexible but costly to operate."
            ),
            slides=[
                {"type": "title", "layout": "center", "title": "DevFlow 2.0 Launch", "subtitle": "R&D Productivity"},
                {
                    "type": "content",
                    "layout": "three_columns",
                    "title": "Competitive Notes",
                    "items": [
                        {"level": 0, "text": "DevFlow 2.0: native AI, zero-config", "content_type": "text"},
                        {"level": 0, "text": "GitLab Premium: rich features, high learning cost", "content_type": "text"},
                        {"level": 0, "text": "Jenkins X: flexible, but complex to operate", "content_type": "text"},
                    ],
                },
            ],
            current_index=1,
            expected_render_types=["table", "text"],
            require_title_slot=True,
        ),
        BenchmarkCase(
            case_id="kpi_chart",
            label="KPI Trend Chart",
            instruction=(
                "Make the current page more data-driven. Turn the quarterly KPI data into a line chart, keep one "
                "short takeaway sentence, and preserve the current slide instead of creating a new page."
            ),
            original_text=(
                "Support ticket resolution time improved from 18 hours in Q1 to 11 hours in Q2 and 7 hours in Q3. "
                "Customer satisfaction rose from 82 to 88 to 91 over the same period."
            ),
            slides=[
                {"type": "title", "layout": "center", "title": "Customer Success KPI Review", "subtitle": "Operations"},
                {
                    "type": "content",
                    "layout": "text_only",
                    "title": "Quarterly KPI Snapshot",
                    "items": [
                        {"level": 0, "text": "Resolution time: Q1 18h, Q2 11h, Q3 7h", "content_type": "text"},
                        {"level": 0, "text": "CSAT: Q1 82, Q2 88, Q3 91", "content_type": "text"},
                    ],
                },
            ],
            current_index=1,
            expected_render_types=["chart", "text"],
        ),
        BenchmarkCase(
            case_id="action_page",
            label="Action Page With Recommendations",
            instruction=(
                "Rewrite the current page as an action page for the COO. Keep the current page, add two prioritized "
                "recommendations with owner-style wording, and make the slide read like a decision memo."
            ),
            original_text=(
                "The team sees three issues: enterprise sales coverage is uneven, onboarding for Meeting Bot converts "
                "poorly, and cross-sell between products is inconsistent. The COO wants a page with next actions."
            ),
            slides=[
                {"type": "title", "layout": "center", "title": "Growth Review", "subtitle": "COO Weekly"},
                {
                    "type": "content",
                    "layout": "text_only",
                    "title": "Current Observations",
                    "items": [
                        {"level": 0, "text": "Enterprise sales coverage is uneven.", "content_type": "text"},
                        {"level": 0, "text": "Meeting Bot onboarding conversion is weak.", "content_type": "text"},
                        {"level": 0, "text": "Cross-sell execution is inconsistent.", "content_type": "text"},
                    ],
                },
            ],
            current_index=1,
            expected_render_types=["text"],
            require_title_slot=True,
            require_recommendations=True,
        ),
    ]


def _mode_winner(self_result: ModeResult, hermes_result: ModeResult) -> str:
    if abs(self_result.total_score - hermes_result.total_score) < 0.01:
        return "tie"
    return "self_agent" if self_result.total_score > hermes_result.total_score else "hermes"


def _case_summary(report: CaseReport) -> str:
    winner = _mode_winner(report.self_agent, report.hermes)
    if winner == "tie":
        return "Both models tie on the current heuristics."
    if winner == "self_agent":
        return "Self agent wins on expression quality, but target accuracy should be checked."
    return "Hermes wins on execution alignment and current-page targeting."


def _render_markdown(reports: list[CaseReport], generated_at: str) -> str:
    self_scores = [report.self_agent.total_score for report in reports]
    hermes_scores = [report.hermes.total_score for report in reports]
    lines = [
        "# PPT Co-Creation Agent Benchmark",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Cases: `{len(reports)}`",
        f"- Self agent average: `{sum(self_scores) / len(self_scores):.2f}`",
        f"- Hermes average: `{sum(hermes_scores) / len(hermes_scores):.2f}`",
        "",
        "## Case Results",
        "",
        "| Case | Self | Hermes | Winner |",
        "| --- | ---: | ---: | --- |",
    ]
    for report in reports:
        winner = _mode_winner(report.self_agent, report.hermes)
        lines.append(
            f"| {report.label} | {report.self_agent.total_score:.2f} | {report.hermes.total_score:.2f} | {winner} |"
        )

    lines.extend(["", "## Notes", ""])
    for report in reports:
        lines.append(f"### {report.label}")
        lines.append(f"- Summary: {report.summary}")
        lines.append(
            f"- Self agent: score `{report.self_agent.total_score:.2f}`, current-page `{report.self_agent.current_page_hit_rate:.2f}`, "
            f"types `{report.self_agent.expected_type_hit_rate:.2f}`, title-slot `{report.self_agent.title_slot_hit}`"
        )
        lines.append(
            f"- Hermes: score `{report.hermes.total_score:.2f}`, current-page `{report.hermes.current_page_hit_rate:.2f}`, "
            f"types `{report.hermes.expected_type_hit_rate:.2f}`, title-slot `{report.hermes.title_slot_hit}`"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    cases = _make_cases()
    reports: list[CaseReport] = []
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")

    for case in cases:
        print(f"[RUN] {case.case_id} - {case.label}")
        user_message = _build_user_message(case)
        self_text, self_error, self_latency = _run_self_agent(user_message)
        hermes_text, hermes_error, hermes_latency = _run_hermes(case, user_message)

        self_result = _evaluate(case, "self_agent", self_text, self_error, self_latency)
        hermes_result = _evaluate(case, "hermes", hermes_text, hermes_error, hermes_latency)
        report = CaseReport(
            case_id=case.case_id,
            label=case.label,
            summary="",
            self_agent=self_result,
            hermes=hermes_result,
        )
        report.summary = _case_summary(report)
        reports.append(report)
        print(
            f"  self={self_result.total_score:.2f} "
            f"hermes={hermes_result.total_score:.2f} "
            f"winner={_mode_winner(self_result, hermes_result)}"
        )

    payload = {
        "generated_at": generated_at,
        "cases": [asdict(report) for report in reports],
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(_render_markdown(reports, generated_at), encoding="utf-8")
    print(f"[DONE] JSON -> {OUTPUT_JSON}")
    print(f"[DONE] Markdown -> {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
