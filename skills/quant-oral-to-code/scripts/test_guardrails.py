from __future__ import annotations

from review_guardrails import review_guardrails


def test_guardrails_flag_required_blocking_and_warning_cases():
    spec = {
        "source_prompt": "收盘买入，用 PE 和 ROE 选股，并在全样本上把参数调到最好。",
        "translation_confidence": 0.55,
        "unresolved_terms": ["强势", "放量确认"],
        "execution_requirements": {"execution_mode": "same_bar_close"},
    }

    review = review_guardrails(spec)

    assert "financial_factor_without_pit_visibility" in review["blocking"]
    assert "optimized_on_full_sample_without_holdout" in review["blocking"]
    assert "low_translation_confidence" in review["blocking"]
    assert "ambiguous_term_unresolved" in review["blocking"]
    assert "same_bar_close_is_optimistic" in review["warnings"]
    assert review["translation_confidence"] == 0.55
    assert review["decision"] == "blocked"
    assert review["recommended_next_step"]


def test_guardrails_allow_clean_ready_spec_to_pass():
    spec = {
        "source_prompt": "A股日线 5 日均线上穿 20 日均线，次日开盘成交，样本外验证。",
        "translation_confidence": 0.86,
        "unresolved_terms": [],
        "execution": {"mode": "next_open"},
        "validation": {
            "has_holdout": True,
            "sample_split": {
                "train": "2018-01-01/2022-12-31",
                "test": "2023-01-01/2024-12-31",
            },
        },
    }

    review = review_guardrails(spec)

    assert review["blocking"] == []
    assert review["warnings"] == []
    assert review["decision"] == "pass"
    assert review["claim_level_ceiling"] == "research_grade_local"


def test_guardrails_only_warn_for_same_bar_close_when_no_other_blocking():
    spec = {
        "source_prompt": "A股日线均线策略，收盘买入，输出收益曲线。",
        "translation_confidence": 0.78,
        "unresolved_terms": [],
        "execution_requirements": {"execution_mode": "same_bar_close"},
    }

    review = review_guardrails(spec)

    assert review["blocking"] == []
    assert review["warnings"] == ["same_bar_close_is_optimistic"]
    assert review["decision"] == "warning"
