from __future__ import annotations

from pathlib import Path


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_template(template_name: str) -> str:
    template_path = _skill_root() / "templates" / template_name
    return template_path.read_text(encoding="utf-8")


def _pick_entry_rule(spec: dict) -> dict:
    entry_rules = spec.get("entry_rules")
    if isinstance(entry_rules, list):
        for rule in entry_rules:
            if isinstance(rule, dict) and rule.get("kind") == "moving_average_cross":
                return rule
    return {"kind": "moving_average_cross", "fast": 5, "slow": 20}


def _pick_exit_rule(spec: dict) -> dict | None:
    exit_rules = spec.get("exit_rules")
    if isinstance(exit_rules, list):
        for rule in exit_rules:
            if isinstance(rule, dict):
                return rule
    return None


def _build_template_context(spec: dict) -> dict[str, object]:
    entry_rule = _pick_entry_rule(spec)
    exit_rule = _pick_exit_rule(spec)
    selection_filters = (
        list(spec.get("selection_filters", []))
        if isinstance(spec.get("selection_filters"), list)
        else []
    )

    exit_ma: str | int | None = "None"
    stop_loss_pct: str | float | None = "None"
    if exit_rule:
        if exit_rule.get("kind") == "price_below_ma":
            exit_ma = int(exit_rule["ma"])
        elif exit_rule.get("kind") == "stop_loss_pct":
            stop_loss_pct = float(exit_rule["pct"])

    use_return_rank_filter = False
    return_rank_lookback = 20
    use_consolidation_filter = False
    consolidation_lookback = 10
    consolidation_max_range_pct = 0.12
    use_retest_breakout_filter = False
    retest_lookback = 20
    retest_tolerance = 0.02
    use_trend_ma_filter = False
    trend_ma = 60
    use_support_ma_filter = False
    support_ma = 20
    use_gap_open_filter = False
    min_gap_pct = 0.01
    use_volume_ratio_filter = False
    volume_ratio_lookback = 20
    volume_ratio_min = 1.8
    use_close_location_filter = False
    min_clv = 0.65
    use_group_relative_strength_filter = False
    group_relative_strength_lookback = 5
    group_relative_strength_min_excess_return = 0.02
    use_rank_improvement_filter = False
    rank_improvement_lookback = 10
    use_liquidity_quantile_filter = False
    liquidity_quantile_metric = "turnover_or_amount"
    liquidity_quantile = 0.85
    use_breakout_rank_filter = False
    breakout_rank_lookback = 20
    breakout_rank_top_n = 5
    use_reclaim_breakout_filter = False
    reclaim_breakout_lookback = 20
    use_sector_breakout_confirmation_filter = False
    sector_breakout_lookback = 20

    for rule in selection_filters:
        if not isinstance(rule, dict):
            continue
        kind = str(rule.get("kind", ""))
        if kind == "rolling_return_rank":
            use_return_rank_filter = True
            return_rank_lookback = int(rule.get("lookback", return_rank_lookback))
        elif kind == "consolidation_filter":
            use_consolidation_filter = True
            consolidation_lookback = int(rule.get("lookback", consolidation_lookback))
            consolidation_max_range_pct = float(
                rule.get("max_range_pct", consolidation_max_range_pct)
            )
        elif kind == "retest_then_breakout":
            use_retest_breakout_filter = True
            retest_lookback = int(rule.get("lookback", retest_lookback))
            retest_tolerance = float(rule.get("retest_tolerance", retest_tolerance))
        elif kind == "higher_timeframe_trend_filter":
            use_trend_ma_filter = True
            trend_ma = int(rule.get("trend_ma", trend_ma))
        elif kind == "support_above_ma":
            use_support_ma_filter = True
            support_ma = int(rule.get("ma", support_ma))
        elif kind == "gap_open_filter":
            use_gap_open_filter = True
            min_gap_pct = float(rule.get("min_gap_pct", min_gap_pct))
        elif kind == "volume_ratio_filter":
            use_volume_ratio_filter = True
            volume_ratio_lookback = int(rule.get("lookback", volume_ratio_lookback))
            volume_ratio_min = float(rule.get("min_ratio", volume_ratio_min))
        elif kind == "close_location_value_filter":
            use_close_location_filter = True
            min_clv = float(rule.get("min_clv", min_clv))
        elif kind in {"group_relative_strength", "sector_relative_strength_resonance"}:
            use_group_relative_strength_filter = True
            group_relative_strength_lookback = int(rule.get("lookback", group_relative_strength_lookback))
            group_relative_strength_min_excess_return = float(
                rule.get("min_excess_return", group_relative_strength_min_excess_return)
            )
        elif kind == "rank_improvement_proxy":
            use_rank_improvement_filter = True
            rank_improvement_lookback = int(rule.get("lookback", rank_improvement_lookback))
        elif kind == "liquidity_quantile_filter":
            use_liquidity_quantile_filter = True
            liquidity_quantile_metric = str(rule.get("metric", liquidity_quantile_metric))
            liquidity_quantile = float(rule.get("quantile", liquidity_quantile))
        elif kind == "breakout_with_rank_filter":
            use_breakout_rank_filter = True
            breakout_rank_lookback = int(rule.get("lookback", breakout_rank_lookback))
            breakout_rank_top_n = int(rule.get("top_n", breakout_rank_top_n))
        elif kind == "reclaim_breakout_level":
            use_reclaim_breakout_filter = True
            reclaim_breakout_lookback = int(rule.get("lookback", reclaim_breakout_lookback))
        elif kind == "sector_breakout_confirmation":
            use_sector_breakout_confirmation_filter = True
            sector_breakout_lookback = int(rule.get("lookback", sector_breakout_lookback))

    return {
        "strategy_name": str(spec.get("strategy_name", "generated_strategy")),
        "strategy_family": str(spec.get("strategy_family", "trend_basic")),
        "market": str(spec.get("market", "unknown")),
        "timeframe": str(spec.get("timeframe", "unknown")),
        "fast_ma": int(entry_rule.get("fast", 5)),
        "slow_ma": int(entry_rule.get("slow", 20)),
        "exit_ma": exit_ma,
        "stop_loss_pct": stop_loss_pct,
        "use_return_rank_filter": str(use_return_rank_filter),
        "return_rank_lookback": return_rank_lookback,
        "use_consolidation_filter": str(use_consolidation_filter),
        "consolidation_lookback": consolidation_lookback,
        "consolidation_max_range_pct": consolidation_max_range_pct,
        "use_retest_breakout_filter": str(use_retest_breakout_filter),
        "retest_lookback": retest_lookback,
        "retest_tolerance": retest_tolerance,
        "use_trend_ma_filter": str(use_trend_ma_filter),
        "trend_ma": trend_ma,
        "use_support_ma_filter": str(use_support_ma_filter),
        "support_ma": support_ma,
        "use_gap_open_filter": str(use_gap_open_filter),
        "min_gap_pct": min_gap_pct,
        "use_volume_ratio_filter": str(use_volume_ratio_filter),
        "volume_ratio_lookback": volume_ratio_lookback,
        "volume_ratio_min": volume_ratio_min,
        "use_close_location_filter": str(use_close_location_filter),
        "min_clv": min_clv,
        "use_group_relative_strength_filter": str(use_group_relative_strength_filter),
        "group_relative_strength_lookback": group_relative_strength_lookback,
        "group_relative_strength_min_excess_return": group_relative_strength_min_excess_return,
        "use_rank_improvement_filter": str(use_rank_improvement_filter),
        "rank_improvement_lookback": rank_improvement_lookback,
        "use_liquidity_quantile_filter": str(use_liquidity_quantile_filter),
        "liquidity_quantile_metric": liquidity_quantile_metric,
        "liquidity_quantile": liquidity_quantile,
        "use_breakout_rank_filter": str(use_breakout_rank_filter),
        "breakout_rank_lookback": breakout_rank_lookback,
        "breakout_rank_top_n": breakout_rank_top_n,
        "use_reclaim_breakout_filter": str(use_reclaim_breakout_filter),
        "reclaim_breakout_lookback": reclaim_breakout_lookback,
        "use_sector_breakout_confirmation_filter": str(use_sector_breakout_confirmation_filter),
        "sector_breakout_lookback": sector_breakout_lookback,
    }


def generate_strategy_code(spec: dict, mode: dict, output_dir: str | Path) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if mode.get("mode") != "standalone_generated":
        raise ValueError(f"unsupported codegen mode: {mode.get('mode')}")

    template_name = str(mode.get("template", "single_asset_strategy.py.tmpl"))
    template = _load_template(template_name)
    context = _build_template_context(spec)
    rendered = template.format(**context)

    strategy_file = output_path / "strategy.py"
    strategy_file.write_text(rendered, encoding="utf-8")
    return {
        "strategy_file": str(strategy_file),
        "mode": mode.get("mode"),
        "template": template_name,
    }
