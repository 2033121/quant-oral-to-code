from __future__ import annotations

from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "result_summary.md.tmpl"

CLAIM_LEVEL_EXPLAINERS = {
    "demo_only": "当前结果仅用于演示链路或样例数据验证，不能当作真实研究结论，更不能直接视为可实盘策略。",
    "portable_backtest": "当前结果来自可移植回测链路，通常基于用户提供的数据完成基础校验，可信度高于 demo_only，但仍不等于研究级结论。",
    "research_grade_local": "当前结果满足本地 research-grade 的显式证据门槛，但仍需要结合样本外验证、交易成本和执行约束一起解读。",
}


def _format_percent(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.2f}%"
    return "N/A"


def _format_ratio(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return "N/A"


def _format_observed_action_counts(action_counts: object) -> str:
    if not isinstance(action_counts, dict) or not action_counts:
        return "N/A"
    ordered = [f"{key}={action_counts[key]}" for key in sorted(action_counts)]
    return ", ".join(ordered)


def _format_equity_curve_path(path_value: object) -> str:
    if path_value in (None, "", False):
        return "未提供"
    return str(path_value)


def _build_plain_language_warning(
    claim_level: str,
    warnings: list[str],
    blocking: list[str],
    metrics_available: bool,
    metrics_unavailable_reason: str,
) -> str:
    pieces: list[str] = []
    if claim_level == "demo_only":
        pieces.append("这是演示级结果，只能说明代码链路可运行，不能说明策略真的有效。")
    elif claim_level == "portable_backtest":
        pieces.append("这是可移植回测结果，说明策略在当前数据上可复现，但还没达到本地研究级证据强度。")
    elif claim_level == "research_grade_local":
        pieces.append("这是本地 research-grade 结果，但仍可能受到交易成本、流动性和样本外表现影响。")
    else:
        pieces.append("结果可信度未知，请先确认数据来源、执行假设和守护栏审查。")

    if not metrics_available:
        pieces.append(
            "本摘要没有真实收益、回撤或 Sharpe 回测指标；当前 runner 只观测动作计数等执行信号。"
        )
        if metrics_unavailable_reason:
            pieces.append(f"指标不可用原因：{metrics_unavailable_reason}。")

    if blocking:
        pieces.append("当前仍存在 blocking，任何收益数字都不应被直接用于交易判断。")
    elif warnings:
        pieces.append("当前存在守护栏告警，解释结果时需要额外谨慎。")

    return " ".join(pieces)


def _render_guardrail_warning_lines(warnings: list[str], blocking: list[str]) -> str:
    lines: list[str] = []
    if blocking:
        lines.extend(f"- blocking: `{item}`" for item in blocking)
    if warnings:
        lines.extend(f"- warning: `{item}`" for item in warnings)
    if not lines:
        lines.append("- 无额外 blocking / warning。")
    return "\n".join(lines)


def summarize_quant_result(
    result: dict[str, object],
    output_path: str | Path | None = None,
) -> str:
    main_backtest = result.get("main_backtest", {})
    main_backtest = main_backtest if isinstance(main_backtest, dict) else {}
    summary = main_backtest.get("summary", {})
    summary = summary if isinstance(summary, dict) else {}
    metrics_available = summary.get("metrics_availability") == "available"
    metrics_unavailable_reason = str(summary.get("metrics_unavailable_reason", ""))
    total_return_value = summary.get("total_return") if metrics_available else None
    max_drawdown_value = summary.get("max_drawdown") if metrics_available else None
    sharpe_ratio_value = summary.get("sharpe_ratio") if metrics_available else None

    observed_run = result.get("observed_run", {})
    observed_run = observed_run if isinstance(observed_run, dict) else {}

    guardrail_review = result.get("guardrail_review", {})
    guardrail_review = guardrail_review if isinstance(guardrail_review, dict) else {}
    warnings = [str(item) for item in guardrail_review.get("warnings", [])]
    blocking = [str(item) for item in guardrail_review.get("blocking", [])]

    claim_report = result.get("claim_report", {})
    claim_report = claim_report if isinstance(claim_report, dict) else {}
    claim_level = str(claim_report.get("claim_level", "unknown"))
    decision = str(claim_report.get("decision", "unknown"))

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    text = template.format(
        equity_curve_path=_format_equity_curve_path(result.get("equity_curve_path")),
        metrics_status=(
            "available"
            if metrics_available
            else f"unavailable ({metrics_unavailable_reason or 'reason_unspecified'})"
        ),
        total_return=_format_percent(total_return_value),
        max_drawdown=_format_percent(max_drawdown_value),
        sharpe_ratio=_format_ratio(sharpe_ratio_value),
        total_rows=observed_run.get("total_rows", "N/A"),
        symbol_count=observed_run.get("symbol_count", "N/A"),
        action_counts=_format_observed_action_counts(observed_run.get("action_counts")),
        execution_mode=observed_run.get("execution_mode", "N/A"),
        bars_table_name=observed_run.get("bars_table_name", "N/A"),
        claim_level=claim_level,
        decision=decision,
        plain_language_warning=_build_plain_language_warning(
            claim_level,
            warnings,
            blocking,
            metrics_available,
            metrics_unavailable_reason,
        ),
        guardrail_warning_lines=_render_guardrail_warning_lines(warnings, blocking),
        claim_level_explainer=CLAIM_LEVEL_EXPLAINERS.get(
            claim_level,
            "claim_level 未知，请先核对 claim_report.json 中的等级定义与降级原因。",
        ),
    )

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    sample = summarize_quant_result(
        {
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
    )
    print(sample)
