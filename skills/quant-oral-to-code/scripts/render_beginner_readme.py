from __future__ import annotations

from pathlib import Path


def render_beginner_readme(
    claim_report: dict[str, object],
    data_contract: dict[str, object] | None = None,
    preflight_report: dict[str, object] | None = None,
    output_path: str | Path | None = None,
) -> str:
    claim_level = str(claim_report.get("claim_level", "unknown"))
    artifact_policy = str(claim_report.get("artifact_policy", "unknown"))
    reasons = claim_report.get("reasons", [])
    missing_dependencies = (preflight_report or {}).get("missing_dependencies", [])
    storage_target = (data_contract or {}).get("storage_target", "未提供")

    if artifact_policy == "data_required_cutoff":
        next_step = "先补齐 DuckDB 可运行环境、真实数据或核心字段映射，再重新生成完整工作区。"
    elif claim_level == "portable_backtest":
        next_step = "当前可以做可移植回测；若要升级为 research_grade_local，需要接入本地研究级数据与更严格验证。"
    elif claim_level == "research_grade_local":
        next_step = "当前已达到本地研究级档位，但仍需结合样本外验证、成本建模和风险审查解读。"
    else:
        next_step = "当前仅是演示级产物，不代表真实研究结论。优先准备可审计的历史行情数据。"

    text = "\n".join(
        [
            "# README_beginner",
            "",
            f"- 当前 claim_level: `{claim_level}`",
            f"- 当前 artifact_policy: `{artifact_policy}`",
            f"- DuckDB 数据目标: `{storage_target}`",
            f"- 缺失依赖: `{', '.join(missing_dependencies) if missing_dependencies else '无'}`",
            f"- 截断/说明原因: `{', '.join(reasons) if reasons else '无'}`",
            "",
            "## 这代表什么",
            "",
            (
                "当前流程被强制截断，只交付 cutoff 产物，目的是避免在缺数据或护栏未通过时伪装成完整回测。"
                if artifact_policy == "data_required_cutoff"
                else "当前流程允许生成完整工作区，但结果可信度仍受 claim_level 限制。"
            ),
            "",
            "## 下一步",
            "",
            next_step,
        ]
    )

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    sample = render_beginner_readme(
        {"claim_level": "demo_only", "artifact_policy": "data_required_cutoff", "reasons": ["needs_data"]},
    )
    print(sample)
