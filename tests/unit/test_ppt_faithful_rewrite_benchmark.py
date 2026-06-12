from __future__ import annotations

import random

from tests.e2e import test_ppt_cocreation_quality_benchmark as benchmark


def test_load_faithful_rewrite_instruction_pool_contains_cases():
    pool = benchmark._load_faithful_rewrite_instruction_pool()

    assert "F_polish" in pool
    assert len(pool["F_polish"]) >= 10

    first_case = pool["F_polish"][0]
    assert first_case["case_id"].startswith("fr_")
    assert first_case["doc_key"] in benchmark.SAMPLE_DOCS
    assert isinstance(first_case["current_index"], int)
    assert "hard_constraints" in first_case


def test_build_round_samples_for_faithful_rewrite_is_deterministic():
    pool = benchmark._load_faithful_rewrite_instruction_pool()
    base_slides = {
        "tech_report": [{}, {}, {}, {}, {}],
        "business_proposal": [{}, {}, {}, {}, {}],
    }

    samples = benchmark._build_round_samples(
        task_mode="faithful_rewrite",
        instruction_pool=pool,
        base_slides=base_slides,
        rng=None,
        samples_per_round=3,
    )

    assert len(samples) == len(pool["F_polish"])
    assert all(cat_key == "F_polish" for cat_key, *_ in samples)
    assert samples[0][1]["case_id"] == "fr_001"


def test_build_round_samples_for_complex_respects_sampling():
    pool = {"F_polish": [{"instruction": "a", "label": "A"}, {"instruction": "b", "label": "B"}]}
    base_slides = {"business_proposal": [{}, {}, {}]}

    samples = benchmark._build_round_samples(
        task_mode="complex",
        instruction_pool=pool,
        base_slides=base_slides,
        rng=random.Random(42),
        samples_per_round=1,
    )

    assert len(samples) == 1
    assert samples[0][0] == "F_polish"
    assert samples[0][2] == "business_proposal"
