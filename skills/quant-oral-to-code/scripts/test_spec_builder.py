from build_strategy_spec import build_strategy_spec
from emit_translation_trace import emit_translation_trace


def test_strategy_spec_and_trace_capture_rules_assumptions_and_confidence():
    prompt = "5日均线上穿20日均线，价格跌破10日均线就走，只做日线A股，输出收益曲线和最大回撤。"
    spec = build_strategy_spec(prompt)
    trace = emit_translation_trace(prompt, spec)
    assert spec["strategy_family"] == "trend_basic"
    assert spec["entry_rules"][0]["kind"] == "moving_average_cross"
    assert spec["market"] == "A股"
    assert spec["timeframe"] == "daily"
    assert "equity_curve" in spec["outputs_requested"]
    assert "max_drawdown" in spec["outputs_requested"]
    assert trace["translation_confidence"] >= 0.6
    assert any(m["field_path"] == "entry_rules[0]" for m in trace["mappings"])


def test_strategy_spec_keeps_vague_language_in_unresolved_terms():
    prompt = "做一个强势股策略，放量确认后再买，A股日线，输出收益曲线。"
    spec = build_strategy_spec(prompt)
    trace = emit_translation_trace(prompt, spec)
    assert "强势" in spec["unresolved_terms"]
    assert "放量确认" in spec["unresolved_terms"]
    assert "equity_curve" in spec["outputs_requested"]
    assert trace["unresolved_terms"] == spec["unresolved_terms"]
    assert any(item["field_path"] == "unresolved_terms[]" for item in trace["mappings"])


def test_strategy_spec_can_capture_a_share_daily_risk_outputs():
    prompt = "A股日线，做5日均线和20日均线交叉策略，要求收益曲线、最大回撤、胜率和夏普。"
    spec = build_strategy_spec(prompt)
    trace = emit_translation_trace(prompt, spec)
    assert spec["market"] == "A股"
    assert spec["timeframe"] == "daily"
    assert spec["outputs_requested"] == ["equity_curve", "max_drawdown", "win_rate", "sharpe_ratio"]
    assert trace["mappings"][0]["field_path"] == "market"


def test_trend_strategy_without_explicit_entry_rule_keeps_entry_rules_empty():
    prompt = "做一个趋势策略，A股日线，输出收益曲线"
    spec = build_strategy_spec(prompt)
    assert spec["strategy_family"] == "trend_basic"
    assert spec["entry_rules"] == []
    assert "缺少明确入场规则" in spec["unresolved_terms"]
    assert any("未给出可执行入场条件" in item for item in spec["assumptions"])


def test_ma_entry_without_exit_does_not_invent_default_ma_stop():
    prompt = "A股日线，5日均线上穿20日均线买入，输出收益曲线"
    spec = build_strategy_spec(prompt)
    assert spec["entry_rules"] == [{"kind": "moving_average_cross", "fast": 5, "slow": 20}]
    assert spec["exit_rules"] == []
    assert "缺少明确退出规则" in spec["unresolved_terms"]
    assert any("未给出明确退出条件" in item for item in spec["assumptions"])


def test_translation_trace_source_text_must_come_from_real_prompt_spans():
    prompt = "沪深，日K，5日均线上穿20日均线买入，输出收益曲线"
    spec = build_strategy_spec(prompt)
    trace = emit_translation_trace(prompt, spec)
    mapping_by_field = {item["field_path"]: item for item in trace["mappings"]}
    assert mapping_by_field["market"]["mapped_value"] == "A股"
    assert mapping_by_field["market"]["source_text"] == "沪深"
    assert mapping_by_field["timeframe"]["mapped_value"] == "daily"
    assert mapping_by_field["timeframe"]["source_text"] == "日K"
    assert mapping_by_field["entry_rules[0]"]["source_text"] in prompt


def test_exit_rule_supports_price_below_ma_colloquial_sell_phrases():
    prompts = [
        "价格跌破10日均线就走",
        "跌破10日均线卖出",
        "跌破10日均线离场",
        "跌破10日均线止损",
    ]
    for prompt in prompts:
        spec = build_strategy_spec(prompt)
        assert spec["exit_rules"] == [{"kind": "price_below_ma", "ma": 10}]
        assert "缺少明确退出规则" not in spec["unresolved_terms"]


def test_data_sensitive_terms_are_explicitly_exposed_in_assumptions():
    prompt = "竞价爆量后看承接，分时不破均价线再盯净流入和筹码"
    spec = build_strategy_spec(prompt)
    assert all(term in spec["unresolved_terms"] for term in ("竞价", "承接", "均价线", "净流入", "筹码"))
    assert any("术语“竞价”依赖特定数据口径" in item for item in spec["assumptions"])
    assert any("术语“均价线”依赖特定数据口径" in item for item in spec["assumptions"])


def test_complex_leaderboard_judgment_terms_stay_unresolved_for_followup():
    prompt = "只做龙头，辨识度高、带动性强，筹码稳，承接够，最好还有净流入"
    spec = build_strategy_spec(prompt)
    trace = emit_translation_trace(prompt, spec)

    expected_terms = ["龙头", "辨识度", "带动性", "筹码", "承接", "净流入"]
    assert all(term in spec["unresolved_terms"] for term in expected_terms)
    assert trace["unresolved_terms"] == spec["unresolved_terms"]
    unresolved_sources = {
        item["source_text"]
        for item in trace["mappings"]
        if item["field_path"] == "unresolved_terms[]"
    }
    assert set(expected_terms).issubset(unresolved_sources)
