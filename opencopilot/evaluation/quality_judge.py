from __future__ import annotations

import json
import math
import os
import re
import threading
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable

from opencopilot.providers.llm_provider import ProviderFactory

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore


_EMBED_MODEL_CACHE: dict[str, Any] = {}
_EMBED_MODEL_LOCK = threading.RLock()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _tokenize(text: str) -> list[str]:
    cleaned = _normalize_text(text).lower()
    return re.findall(r"[\u4e00-\u9fff]|[a-z0-9_]+", cleaned)


def _extract_keywords(text: str, limit: int = 8) -> list[str]:
    stop_words = {
        "请", "把", "将", "并", "再", "再给", "一个", "这段", "代码", "内容", "当前", "最后",
        "先", "然后", "以及", "一下", "进行", "需要", "可以", "一下子", "更", "的", "了",
        "and", "the", "for", "with", "that", "this", "then", "give", "make",
    }
    keywords: list[str] = []
    for token in _tokenize(text):
        if token in stop_words or len(token) <= 1:
            continue
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _token_f1(reference: str, candidate: str) -> float:
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)
    if not ref_tokens or not cand_tokens:
        return 0.0
    ref_counts: dict[str, int] = {}
    cand_counts: dict[str, int] = {}
    for token in ref_tokens:
        ref_counts[token] = ref_counts.get(token, 0) + 1
    for token in cand_tokens:
        cand_counts[token] = cand_counts.get(token, 0) + 1
    overlap = 0
    for token, count in ref_counts.items():
        overlap += min(count, cand_counts.get(token, 0))
    if overlap == 0:
        return 0.0
    precision = overlap / len(cand_tokens)
    recall = overlap / len(ref_tokens)
    return (2 * precision * recall) / (precision + recall)


def _char_ngram_jaccard(left: str, right: str, n: int = 2) -> float:
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if len(left_norm) < n or len(right_norm) < n:
        return 0.0
    left_set = {left_norm[i : i + n] for i in range(len(left_norm) - n + 1)}
    right_set = {right_norm[i : i + n] for i in range(len(right_norm) - n + 1)}
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _sequence_ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, _normalize_text(left), _normalize_text(right)).ratio()


def _keyword_coverage(output: str, keywords: Iterable[str]) -> float:
    normalized = _normalize_text(output).lower()
    keys = [kw.lower() for kw in keywords if kw]
    if not keys:
        return 0.0
    hits = sum(1 for kw in keys if kw in normalized)
    return hits / len(keys)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _hash_embedding(text: str, dims: int = 256) -> list[float]:
    vector = [0.0] * dims
    tokens = _tokenize(text)
    if not tokens:
        return vector
    counts = Counter(tokens)
    total = sum(counts.values()) or 1
    for token, count in counts.items():
        bucket = hash(token) % dims
        sign = -1.0 if (hash(f"{token}:sign") % 2) else 1.0
        vector[bucket] += sign * (count / total)
    return vector


def _load_sentence_transformer(model_name: str) -> Any | None:
    if SentenceTransformer is None:
        return None
    with _EMBED_MODEL_LOCK:
        if model_name in _EMBED_MODEL_CACHE:
            return _EMBED_MODEL_CACHE[model_name]
        try:
            model = SentenceTransformer(model_name)
        except Exception:
            return None
        _EMBED_MODEL_CACHE[model_name] = model
        return model


def _embedding_similarity(left: str, right: str) -> tuple[float, str]:
    backend = os.getenv("OPEN_COPILOT_EMBEDDING_BACKEND", "auto").strip().lower()
    model_name = os.getenv("OPEN_COPILOT_EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip() or "all-MiniLM-L6-v2"
    if not left or not right:
        return 0.0, "empty"

    if backend in {"auto", "sentence_transformers"}:
        model = _load_sentence_transformer(model_name)
        if model is not None:
            try:
                embeddings = model.encode([_normalize_text(left), _normalize_text(right)], normalize_embeddings=True)
                left_vec = list(float(x) for x in embeddings[0])
                right_vec = list(float(x) for x in embeddings[1])
                return max(0.0, _cosine_similarity(left_vec, right_vec)), f"sentence_transformers:{model_name}"
            except Exception:
                if backend == "sentence_transformers":
                    return 0.0, f"sentence_transformers_failed:{model_name}"

    left_vec = _hash_embedding(left)
    right_vec = _hash_embedding(right)
    return max(0.0, _cosine_similarity(left_vec, right_vec)), "hash_embedding_fallback"


@dataclass(slots=True)
class JudgeBudget:
    enabled: bool
    max_cases: int
    used_cases: int = 0

    @classmethod
    def from_env(cls, default_max_cases: int = 12) -> "JudgeBudget":
        enabled = os.getenv("OPEN_COPILOT_ENABLE_LLM_JUDGE", "1").strip().lower() not in {"0", "false", "off"}
        raw_limit = os.getenv("OPEN_COPILOT_LLM_JUDGE_MAX_CASES", str(default_max_cases))
        try:
            max_cases = max(0, int(raw_limit))
        except ValueError:
            max_cases = default_max_cases
        return cls(enabled=enabled, max_cases=max_cases)

    def consume(self) -> bool:
        if not self.enabled or self.max_cases <= 0 or self.used_cases >= self.max_cases:
            return False
        self.used_cases += 1
        return True


def _call_judge_llm(system_prompt: str, user_prompt: str) -> tuple[dict[str, Any] | None, str]:
    provider = ProviderFactory.create_provider()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = ""
    if hasattr(provider, "_do_non_stream"):
        response = provider._do_non_stream(messages)
        raw = str((response or {}).get("content", ""))
    else:
        chunks = []
        for chunk in provider.stream_chat_with_history(messages):
            if isinstance(chunk, tuple):
                continue
            chunks.append(str(chunk))
        raw = "".join(chunks)

    if not raw or raw.startswith("[MiMo ") or raw.startswith("[MiniMax ") or raw.startswith("[连接本地大模型失败]"):
        return None, raw
    parsed = _extract_json(raw)
    return parsed, raw


def _extract_json(raw: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"```(?:json)?", "", raw or "", flags=re.IGNORECASE).replace("```", "").strip()
    if not cleaned:
        return None
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except Exception:
        pass

    start = cleaned.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(cleaned[start : idx + 1])
                    return data if isinstance(data, dict) else None
                except Exception:
                    return None
    return None


def _judge_prompt(
    task_type: str,
    instruction: str,
    output: str,
    context_text: str,
    reference_text: str,
    extra_context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    rubric = {
        "text": [
            "semantic_alignment",
            "description_accuracy",
            "instruction_fulfillment",
            "groundedness",
            "clarity",
        ],
        "cocreation": [
            "instruction_fulfillment",
            "target_fidelity",
            "action_validity",
            "content_relevance",
            "presentation_clarity",
        ],
    }[task_type]
    system_prompt = (
        "你是严格的质量评测裁判。你只能输出 JSON，不要输出任何解释性文字。"
        "所有分数使用 0-100 的整数。若信息不足也要尽量根据给定上下文打分。"
    )
    user_prompt = json.dumps(
        {
            "task_type": task_type,
            "dimensions": rubric,
            "instruction": instruction,
            "context_text": context_text,
            "reference_text": reference_text,
            "output": output,
            "extra_context": extra_context or {},
            "required_schema": {
                "scores": {name: "0-100 integer" for name in rubric},
                "overall_score": "0-100 integer",
                "summary": "short Chinese summary",
            },
            "scoring_rules": [
                "优先判断是否真正完成指令",
                "检查描述是否准确、是否与上下文/参考信息一致",
                "若输出有明显幻觉、错页、错对象或错动作，要显著扣分",
                "summary 保持 30 字以内",
            ],
        },
        ensure_ascii=False,
    )
    return system_prompt, user_prompt


def _build_common_metrics(
    instruction: str,
    output: str,
    reference_text: str,
    keywords: list[str] | None = None,
) -> dict[str, float]:
    keywords = keywords or _extract_keywords(instruction)
    keyword_coverage = _keyword_coverage(output, keywords)
    reference_f1 = _token_f1(reference_text, output) if reference_text else 0.0
    reference_char_sim = _char_ngram_jaccard(reference_text, output) if reference_text else 0.0
    sequence_ratio = _sequence_ratio(reference_text, output) if reference_text else 0.0
    instruction_overlap = _token_f1(instruction, output)
    embedding_reference = reference_text or instruction
    embedding_score, embedding_backend = _embedding_similarity(embedding_reference, output)
    semantic_proxy = (
        0.30 * embedding_score
        + 0.20 * keyword_coverage
        + 0.15 * instruction_overlap
        + 0.20 * reference_f1
        + 0.10 * reference_char_sim
        + 0.05 * sequence_ratio
    ) if reference_text else (
        0.55 * embedding_score + 0.25 * keyword_coverage + 0.20 * instruction_overlap
    )
    description_accuracy = (
        0.20 * embedding_score + 0.45 * reference_f1 + 0.20 * reference_char_sim + 0.15 * sequence_ratio
    ) if reference_text else (
        0.50 * embedding_score + 0.30 * keyword_coverage + 0.20 * instruction_overlap
    )
    return {
        "embedding_backend": embedding_backend,
        "embedding_similarity": round(embedding_score * 100, 2),
        "keyword_coverage": round(keyword_coverage * 100, 2),
        "instruction_overlap": round(instruction_overlap * 100, 2),
        "reference_token_f1": round(reference_f1 * 100, 2),
        "reference_char_similarity": round(reference_char_sim * 100, 2),
        "reference_sequence_ratio": round(sequence_ratio * 100, 2),
        "semantic_similarity": round(semantic_proxy * 100, 2),
        "description_accuracy": round(description_accuracy * 100, 2),
    }


def evaluate_text_output(
    *,
    instruction: str,
    output: str,
    context_text: str = "",
    reference_text: str = "",
    keywords: list[str] | None = None,
    judge_budget: JudgeBudget | None = None,
) -> dict[str, Any]:
    metrics = _build_common_metrics(instruction, output, reference_text, keywords)
    judge_score = None
    judge_summary = ""
    judge_scores: dict[str, Any] = {}
    judge_applied = False
    judge_error = ""

    budget = judge_budget or JudgeBudget(enabled=False, max_cases=0)
    if output.strip() and budget.consume():
        judge_applied = True
        system_prompt, user_prompt = _judge_prompt(
            "text",
            instruction=instruction,
            output=output,
            context_text=context_text,
            reference_text=reference_text,
        )
        judged, raw = _call_judge_llm(system_prompt, user_prompt)
        if judged:
            judge_scores = judged.get("scores", {}) if isinstance(judged.get("scores"), dict) else {}
            try:
                judge_score = float(judged.get("overall_score", 0))
            except (TypeError, ValueError):
                judge_score = None
            judge_summary = str(judged.get("summary", "")).strip()
        else:
            judge_error = raw[:160]

    if judge_score is None:
        overall_score = round(0.55 * metrics["semantic_similarity"] + 0.45 * metrics["description_accuracy"], 2)
    else:
        overall_score = round(
            0.30 * metrics["semantic_similarity"]
            + 0.25 * metrics["description_accuracy"]
            + 0.45 * judge_score,
            2,
        )

    return {
        **metrics,
        "judge_applied": judge_applied,
        "judge_score": round(judge_score, 2) if judge_score is not None else None,
        "judge_scores": judge_scores,
        "judge_summary": judge_summary,
        "judge_error": judge_error,
        "overall_score": overall_score,
    }


def evaluate_cocreation_output(
    *,
    instruction: str,
    output: str,
    current_slide: dict[str, Any] | None,
    render_commands: list[dict[str, Any]] | None,
    category: str,
    judge_budget: JudgeBudget | None = None,
) -> dict[str, Any]:
    slide_context = json.dumps(current_slide or {}, ensure_ascii=False)
    action_text = json.dumps(render_commands or [], ensure_ascii=False)
    reference_hint = f"current_slide={slide_context}\nrender_commands={action_text}"
    metrics = _build_common_metrics(
        instruction=instruction,
        output=output,
        reference_text=reference_hint,
        keywords=_extract_keywords(instruction),
    )
    target_accuracy = 100.0 if any(
        cmd.get("slide_index") in {-1, (current_slide or {}).get("slide_index", 0)}
        for cmd in (render_commands or [])
    ) else (60.0 if render_commands else 30.0)
    metrics["target_accuracy"] = target_accuracy

    judge_score = None
    judge_summary = ""
    judge_scores: dict[str, Any] = {}
    judge_applied = False
    judge_error = ""
    budget = judge_budget or JudgeBudget(enabled=False, max_cases=0)
    if output.strip() and budget.consume():
        judge_applied = True
        system_prompt, user_prompt = _judge_prompt(
            "cocreation",
            instruction=instruction,
            output=output,
            context_text=slide_context,
            reference_text=action_text,
            extra_context={"category": category},
        )
        judged, raw = _call_judge_llm(system_prompt, user_prompt)
        if judged:
            judge_scores = judged.get("scores", {}) if isinstance(judged.get("scores"), dict) else {}
            try:
                judge_score = float(judged.get("overall_score", 0))
            except (TypeError, ValueError):
                judge_score = None
            judge_summary = str(judged.get("summary", "")).strip()
        else:
            judge_error = raw[:160]

    if judge_score is None:
        overall_score = round(
            0.45 * metrics["semantic_similarity"]
            + 0.25 * metrics["description_accuracy"]
            + 0.30 * target_accuracy,
            2,
        )
    else:
        overall_score = round(
            0.20 * metrics["semantic_similarity"]
            + 0.20 * metrics["description_accuracy"]
            + 0.20 * target_accuracy
            + 0.40 * judge_score,
            2,
        )

    return {
        **metrics,
        "judge_applied": judge_applied,
        "judge_score": round(judge_score, 2) if judge_score is not None else None,
        "judge_scores": judge_scores,
        "judge_summary": judge_summary,
        "judge_error": judge_error,
        "overall_score": overall_score,
    }
