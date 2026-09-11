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
        "source_prompt": "A股日线 5 日均线上穿 20 日均线，次日开盘成交，并做样本外验证。",
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


def test_guardrails_block_overfit_wording_without_holdout():
    spec = {
        "source_prompt": "先把最好看的版本找出来，某几年特别好使就往那个方向靠，再拟合一下胜率。",
        "translation_confidence": 0.92,
        "unresolved_terms": [],
    }

    review = review_guardrails(spec)

    assert "optimized_on_full_sample_without_holdout" in review["blocking"]
    assert review["rule_hits"]["optimized_on_full_sample_without_holdout"]["evidence"]
    assert review["decision"] == "blocked"


def test_guardrails_block_hindsight_filtering_and_future_leakage():
    spec = {
        "source_prompt": "当天收盘最终站稳、次日还有溢价才算有效，然后当日收盘就进。",
        "translation_confidence": 0.9,
        "unresolved_terms": [],
    }

    review = review_guardrails(spec)

    assert "future_leakage_or_hindsight_filtering" in review["blocking"]
    assert review["rule_hits"]["future_leakage_or_hindsight_filtering"]["evidence"]
    assert review["decision"] == "blocked"


def test_guardrails_warn_when_intraday_language_lacks_explicit_granularity():
    spec = {
        "source_prompt": "竞价看强弱，盘中回落不破分时前高，均价线上方进场。",
        "translation_confidence": 0.88,
        "unresolved_terms": [],
    }

    review = review_guardrails(spec)

    assert review["blocking"] == []
    assert "intraday_semantics_without_granularity" in review["warnings"]
    assert (
        review["rule_hits"]["intraday_semantics_without_granularity"][
            "recommended_data_granularity"
        ]
        == "minute_or_tick"
    )
    assert review["decision"] == "warning"


def test_guardrails_allow_intraday_when_granularity_is_explicit():
    spec = {
        "source_prompt": "竞价后 5 分钟突破分时前高买入。",
        "translation_confidence": 0.9,
        "unresolved_terms": [],
        "timeframe": "5m",
        "execution_requirements": {"bar_interval": "5m"},
    }

    review = review_guardrails(spec)

    assert "intraday_semantics_without_granularity" not in review["warnings"]
    assert review["blocking"] == []


def test_guardrails_do_not_block_when_prompt_explicitly_avoids_future_leakage():
    spec = {
        "source_prompt": "先看高级别方向，再在次级别寻找三买结构，默认使用次日开盘成交，不要使用前视信息。",
        "translation_confidence": 0.82,
        "unresolved_terms": [],
    }

    review = review_guardrails(spec)

    assert "future_leakage_or_hindsight_filtering" not in review["blocking"]
