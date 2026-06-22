from __future__ import annotations

from apply_disambiguation_answers import apply_disambiguation_answers
from build_strategy_spec import build_strategy_spec
from run_full_validation import _read_disambiguation_answers


def test_example_sidecar_answers_exist_for_chanlun_and_liangxue():
    chanlun_answers = _read_disambiguation_answers("chanlun_third_buy_prompt.md")
    liangxue_answers = _read_disambiguation_answers("liangxue_breakout_prompt.md")
    abstract_answers = _read_disambiguation_answers("abstract_a_share_prompt.md")

    assert chanlun_answers == {"三买结构": "third_buy_retest_breakout"}
    assert liangxue_answers == {"关键线": "key_line_prev_high"}
    assert abstract_answers["龙回头"] == "dragon_return_retest"
    assert abstract_answers["放量确认"] == "volume_ratio_confirmation"


def test_example_sidecar_answers_can_resolve_core_terms():
    chanlun_prompt = "请把这个偏缠论口径的想法落成可运行研究代码：先看高级别方向，再在次级别寻找三买结构，默认使用次日开盘成交，不要使用前视信息，并输出收益曲线和最大回撤。"
    liangxue_prompt = "请把这个量学突破思路直接写成可回测代码：寻找前高突破后回踩关键线再次上行的个股，要求避免过拟合，按统一 DuckDB 数据契约运行，并输出收益曲线和最大回撤。"

    chanlun_spec = apply_disambiguation_answers(
        build_strategy_spec(chanlun_prompt),
        _read_disambiguation_answers("chanlun_third_buy_prompt.md"),
    )
    liangxue_spec = apply_disambiguation_answers(
        build_strategy_spec(liangxue_prompt),
        _read_disambiguation_answers("liangxue_breakout_prompt.md"),
    )

    assert "三买结构" not in chanlun_spec["unresolved_terms"]
    assert "关键线" not in liangxue_spec["unresolved_terms"]
    assert chanlun_spec["translation_confidence"] >= 0.6
    assert liangxue_spec["translation_confidence"] >= 0.6


def test_abstract_a_share_sidecar_answers_resolve_general_short_term_jargon():
    prompt = "请把这个偏 A 股短线抽象口语的想法落成可回测代码：A股日线里我想做那种龙回头二波的票，只做龙头，最好先经历情绪冰点，再出现弱转强，放量确认后上车；默认次日开盘成交，避免前视，并输出收益曲线和最大回撤。"
    spec = apply_disambiguation_answers(
        build_strategy_spec(prompt),
        _read_disambiguation_answers("abstract_a_share_prompt.md"),
    )

    for term in ["龙回头", "二波", "龙头", "情绪冰点", "弱转强", "放量确认", "放量"]:
        assert term not in spec["unresolved_terms"]
    assert spec["translation_confidence"] >= 0.75
