from __future__ import annotations

from pathlib import Path

from summarize_quant_result import summarize_quant_result


def test_result_summary_mentions_equity_curve_drawdown_and_plain_language_warning():
    result = {
        "main_backtest": {
            "summary": {
                "total_return": 0.21,
                "max_drawdown": -0.12,
                "sharpe_ratio": 1.1,
            }
        },
        "equity_curve_path": "generated_strategies/ma_demo/results/equity_curve.png",
        "guardrail_review": {"blocking": [], "warnings": ["same_bar_close_is_optimistic"]},
        "claim_report": {"claim_level": "portable_backtest", "decision": "downgraded"},
    }

    text = summarize_quant_result(result)

    assert "收益曲线" in text
    assert "generated_strategies/ma_demo/results/equity_curve.png" in text
    assert "总收益" in text and "21.00%" in text
    assert "最大回撤" in text and "-12.00%" in text
    assert "Sharpe" in text and "1.10" in text
    assert "可信度 / claim_level" in text
    assert "portable_backtest" in text
    assert "same_bar_close_is_optimistic" in text
    assert "便携回测结果" in text


def test_result_summary_highlights_demo_only_risk_language_and_writes_file(tmp_path: Path):
    output_path = tmp_path / "result_summary.md"
    result = {
        "main_backtest": {
            "summary": {
                "total_return": 0.03,
                "max_drawdown": -0.08,
                "sharpe_ratio": 0.4,
            }
        },
        "equity_curve_path": "results/equity_curve.png",
        "guardrail_review": {"blocking": ["needs_real_data"], "warnings": []},
        "claim_report": {"claim_level": "demo_only", "decision": "cutoff"},
    }

    text = summarize_quant_result(result, output_path=output_path)

    assert "demo_only" in text
    assert "这是演示级结果" in text
    assert "任何收益数字都不应被直接用于交易判断" in text
    assert output_path.read_text(encoding="utf-8") == text
