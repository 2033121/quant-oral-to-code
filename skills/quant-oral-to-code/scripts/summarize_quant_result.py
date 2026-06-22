from __future__ import annotations

from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "result_summary.md.tmpl"

CLAIM_LEVEL_EXPLAINERS = {
    "demo_only": "当前结果仅用于演示链路或样例数据验证，不能当作真实研究结论，更不能直接视为可实盘策略。",
    "portable_backtest": "当前结果来自可移植回测路径，通常基于用户提供的数据完成基础校验，可信度高于 demo_only，但仍不等于研究级结论。",
    "research_grade_local": "当前结果满足本地研究级数据与协议要求，但仍需要结合样本外验证、交易成本和执行约束一起解读。",
}


def _format_percent(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.2f}%"
    return "N/A"


def _format_ratio(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return "N/A"


def _build_plain_language_warning(
    claim_level: str,
    warnings: list[str],
    blocking: list[str],
) -> str:
    pieces: list[str] = []
    if claim_level == "demo_only":
        pieces.append("这是演示级结果，只能说明代码链路可运行，不能说明策略真的有效。")
    elif claim_level == "portable_backtest":
        pieces.append("这是便携回测结果，说明策略在当前数据上可复现，但还没有达到本地研究级证据强度。")
    elif claim_level == "research_grade_local":
        pieces.append("这是研究级本地结果，但仍可能受到交易成本、流动性和样本外表现影响。")
    else:
        pieces.append("结果可信度未知，请先确认数据来源、执行假设和守护栏审查。")

    if blocking:
        pieces.append("当前仍存在阻断项，任何收益数字都不应被直接用于交易判断。")
    elif warnings:
        pieces.append("当前存在守护栏告警，收益和回撤可能偏乐观，需要谨慎解读。")

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
    summary = (
        result.get("main_backtest", {})
        if isinstance(result.get("main_backtest"), dict)
        else {}
    )
    summary = summary.get("summary", {}) if isinstance(summary.get("summary"), dict) else {}

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
        equity_curve_path=result.get("equity_curve_path", "未提供"),
        total_return=_format_percent(summary.get("total_return")),
        max_drawdown=_format_percent(summary.get("max_drawdown")),
        sharpe_ratio=_format_ratio(summary.get("sharpe_ratio")),
        claim_level=claim_level,
        decision=decision,
        plain_language_warning=_build_plain_language_warning(claim_level, warnings, blocking),
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
                    "total_return": 0.21,
                    "max_drawdown": -0.12,
                    "sharpe_ratio": 1.1,
                }
            },
            "equity_curve_path": "generated_strategies/ma_demo/results/equity_curve.png",
            "guardrail_review": {"blocking": [], "warnings": ["same_bar_close_is_optimistic"]},
            "claim_report": {"claim_level": "portable_backtest", "decision": "downgraded"},
        }
    )
    print(sample)
