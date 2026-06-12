from __future__ import annotations

from opencopilot.evaluation.quality_judge import (
    JudgeBudget,
    _extract_json,
    evaluate_cocreation_output,
    evaluate_text_output,
)


def test_extract_json_handles_fenced_payload():
    raw = """```json
    {"scores":{"semantic_alignment":88},"overall_score":84,"summary":"语义基本对齐"}
    ```"""
    parsed = _extract_json(raw)
    assert parsed is not None
    assert parsed["overall_score"] == 84


def test_evaluate_text_output_without_judge_falls_back_to_proxy_scores():
    result = evaluate_text_output(
        instruction="解释这段代码并说明复杂度",
        output="这段代码是递归实现，时间复杂度较高，建议改成迭代。",
        context_text="def fib(n): ...",
        reference_text="递归实现斐波那契，时间复杂度 O(2^n)，建议改为迭代。",
        keywords=["递归", "复杂度", "迭代"],
        judge_budget=JudgeBudget(enabled=False, max_cases=0),
    )
    assert result["judge_applied"] is False
    assert result["embedding_similarity"] > 0
    assert result["embedding_backend"]
    assert result["semantic_similarity"] > 0
    assert result["description_accuracy"] > 0
    assert result["overall_score"] > 0


def test_evaluate_text_output_uses_llm_judge_when_available(monkeypatch):
    class DummyProvider:
        def _do_non_stream(self, _messages):
            return {
                "content": (
                    '{"scores":{"semantic_alignment":90,"description_accuracy":86,'
                    '"instruction_fulfillment":88,"groundedness":85,"clarity":84},'
                    '"overall_score":87,"summary":"执行到位"}'
                )
            }

    monkeypatch.setattr(
        "opencopilot.evaluation.quality_judge.ProviderFactory.create_provider",
        lambda: DummyProvider(),
    )
    result = evaluate_text_output(
        instruction="请做代码审查并给建议",
        output="存在空值和隐私泄漏风险，建议加校验并避免直接打印邮箱。",
        context_text="def process_users(users): ...",
        reference_text="需要指出风险、原因与建议。",
        keywords=["风险", "建议"],
        judge_budget=JudgeBudget(enabled=True, max_cases=1),
    )
    assert result["judge_applied"] is True
    assert result["judge_score"] == 87.0
    assert result["judge_summary"] == "执行到位"
    assert result["overall_score"] > 0


def test_evaluate_cocreation_output_combines_target_and_semantic_scores():
    result = evaluate_cocreation_output(
        instruction="把当前页标题改成更有吸引力的版本",
        output='{"render_commands":[{"slide_index":0,"slot":"title","action":"update","value":"AI Agent 全景洞察"}]}',
        current_slide={"slide_index": 0, "title": "旧标题"},
        render_commands=[{"slide_index": 0, "slot": "title", "action": "update"}],
        category="B_title",
        judge_budget=JudgeBudget(enabled=False, max_cases=0),
    )
    assert result["target_accuracy"] >= 60
    assert result["embedding_similarity"] > 0
    assert result["embedding_backend"]
    assert result["semantic_similarity"] > 0
    assert result["overall_score"] > 0
