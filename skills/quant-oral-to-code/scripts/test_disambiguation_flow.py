from __future__ import annotations

from pathlib import Path

from apply_disambiguation_answers import apply_disambiguation_answers
from build_disambiguation_pack import build_disambiguation_pack
from build_strategy_spec import build_strategy_spec
from emit_translation_trace import emit_translation_trace
from generate_strategy_code import generate_strategy_code
from load_generated_strategy import load_generated_strategy
from resolve_codegen_mode import resolve_codegen_mode
from review_guardrails import review_guardrails


def test_build_disambiguation_pack_for_abstract_a_share_terms():
    prompt = "只做龙头，筹码稳，最好回踩后再突破，别盘中破均价线。"
    spec = build_strategy_spec(prompt)
    pack = build_disambiguation_pack(prompt, spec)

    assert pack["can_continue_after_answers"] is True
    terms = {item["term"] for item in pack["questions"]}
    assert "龙头" in terms
    assert "筹码" in terms
    assert "均价线" in terms
    assert pack["search_hints"]


def test_apply_disambiguation_answers_reduces_unresolved_terms_and_adds_filters():
    prompt = "只做龙头，筹码稳，最好回踩后再突破。"
    spec = build_strategy_spec(prompt)

    updated = apply_disambiguation_answers(
        spec,
        {
            "龙头": "leader_return_rank",
            "筹码": "chip_platform_consolidation",
            "分歧转一致": "pullback_then_breakout",
        },
    )

    assert "龙头" not in updated["unresolved_terms"]
    assert "筹码" not in updated["unresolved_terms"]
    assert isinstance(updated.get("selection_filters"), list)
    kinds = {item["kind"] for item in updated["selection_filters"]}
    assert "rolling_return_rank" in kinds
    assert "consolidation_filter" in kinds


def test_disambiguated_terms_are_written_to_translation_trace():
    prompt = "只做龙头，筹码稳。"
    spec = build_strategy_spec(prompt)
    updated = apply_disambiguation_answers(
        spec,
        {
            "龙头": "leader_return_rank",
            "筹码": "chip_platform_consolidation",
        },
    )
    trace = emit_translation_trace(prompt, updated)

    mapping_paths = [item["field_path"] for item in trace["mappings"]]
    assert "disambiguated_terms[]" in mapping_paths


def test_disambiguated_spec_can_pass_guardrail_when_remaining_terms_cleared():
    prompt = "A股日线，5日均线上穿20日均线买入，只做龙头，筹码稳，价格跌破10日均线就走。"
    spec = build_strategy_spec(prompt)
    updated = apply_disambiguation_answers(
        spec,
        {
            "龙头": "leader_return_rank",
            "筹码": "chip_platform_consolidation",
        },
    )
    review = review_guardrails(updated)

    assert "ambiguous_term_unresolved" not in review["blocking"]


def test_disambiguated_filters_flow_into_generated_strategy(tmp_path: Path):
    prompt = "A股日线，5日均线上穿20日均线买入，只做龙头，筹码稳，价格跌破10日均线就走。"
    spec = build_strategy_spec(prompt)
    updated = apply_disambiguation_answers(
        spec,
        {
            "龙头": "leader_return_rank",
            "筹码": "chip_platform_consolidation",
        },
    )
    updated["strategy_name"] = "abstract_proxy_demo"
    updated["strategy_family"] = "trend_basic"
    updated["market"] = "A股"
    updated["timeframe"] = "daily"
    mode = resolve_codegen_mode(updated)
    result = generate_strategy_code(updated, mode, tmp_path)

    strategy_file = Path(result["strategy_file"])
    text = strategy_file.read_text(encoding="utf-8")
    assert "use_return_rank_filter" in text
    assert "use_consolidation_filter" in text

    strategy_class = load_generated_strategy(strategy_file)
    strategy = strategy_class()
    description = strategy.describe()
    assert description["use_return_rank_filter"] is True
    assert description["use_consolidation_filter"] is True


def test_general_abstract_short_term_jargon_can_flow_into_supported_filters(tmp_path: Path):
    prompt = "A股日线里我想做那种龙回头二波的票，只做龙头，最好先经历情绪冰点，再出现弱转强，放量确认后上车。"
    spec = build_strategy_spec(prompt)
    updated = apply_disambiguation_answers(
        spec,
        {
            "龙回头": "dragon_return_retest",
            "二波": "second_leg_breakout",
            "龙头": "leader_return_rank",
            "情绪冰点": "emotion_low_volatility_proxy",
            "弱转强": "weak_to_strong_gap_followthrough",
            "放量确认": "volume_ratio_confirmation",
        },
    )
    updated["strategy_name"] = "general_abstract_demo"
    updated["strategy_family"] = "trend_basic"
    updated["market"] = "A股"
    updated["timeframe"] = "daily"
    mode = resolve_codegen_mode(updated)
    result = generate_strategy_code(updated, mode, tmp_path)

    strategy_file = Path(result["strategy_file"])
    text = strategy_file.read_text(encoding="utf-8")
    assert "use_retest_breakout_filter" in text
    assert "use_gap_open_filter" in text
    assert "use_volume_ratio_filter" in text
