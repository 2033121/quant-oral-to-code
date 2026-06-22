from __future__ import annotations

from pathlib import Path

from summarize_quant_result import summarize_quant_result


def test_result_summary_marks_performance_metrics_unavailable_and_highlights_observed_counts():
    result = {
        "main_backtest": {
            "summary": {
                "total_return": 0.21,
                "max_drawdown": -0.12,
                "sharpe_ratio": 1.1,
                "metrics_availability": "unavailable",
                "metrics_unavailable_reason": "runner_observes_action_counts_without_pnl_engine",
            }
        },
        "observed_run": {
            "total_rows": 240,
            "symbol_count": 3,
            "action_counts": {"buy": 5, "hold": 228, "sell": 4},
            "execution_mode": "read_only_duckdb",
            "bars_table_name": "bars",
        },
        "equity_curve_path": None,
        "guardrail_review": {"blocking": [], "warnings": ["same_bar_close_is_optimistic"]},
        "claim_report": {"claim_level": "portable_backtest", "decision": "downgraded"},
    }

    text = summarize_quant_result(result)

    assert "收益曲线：未提供" in text
    assert "收益指标状态：unavailable (runner_observes_action_counts_without_pnl_engine)" in text
    assert "总收益：N/A" in text
    assert "最大回撤：N/A" in text
    assert "Sharpe：N/A" in text
    assert "观测总行数：240" in text
    assert "观测标的数：3" in text
    assert "动作计数：buy=5, hold=228, sell=4" in text
    assert "portable_backtest" in text
    assert "same_bar_close_is_optimistic" in text
    assert "本摘要没有真实收益、回撤或 Sharpe 回测指标" in text
    assert "21.00%" not in text
    assert "-12.00%" not in text
    assert "1.10" not in text


def test_result_summary_highlights_demo_only_risk_language_and_writes_file(tmp_path: Path):
    output_path = tmp_path / "result_summary.md"
    result = {
        "main_backtest": {
            "summary": {
                "total_return": None,
                "max_drawdown": None,
                "sharpe_ratio": None,
                "metrics_availability": "unavailable",
                "metrics_unavailable_reason": "runner_observes_action_counts_without_pnl_engine",
            }
        },
        "observed_run": {
            "total_rows": 42,
            "symbol_count": 1,
            "action_counts": {"buy": 1, "hold": 40, "sell": 1},
            "execution_mode": "read_only_duckdb",
            "bars_table_name": "bars",
        },
        "equity_curve_path": None,
        "guardrail_review": {"blocking": ["needs_real_data"], "warnings": []},
        "claim_report": {"claim_level": "demo_only", "decision": "cutoff"},
    }

    text = summarize_quant_result(result, output_path=output_path)

    assert "demo_only" in text
    assert "这是演示级结果，只能说明代码链路可运行，不能说明策略真的有效。" in text
    assert "当前仍存在 blocking，任何收益数字都不应被直接用于交易判断。" in text
    assert "总收益：N/A" in text
    assert "收益曲线：未提供" in text
    assert output_path.read_text(encoding="utf-8") == text
