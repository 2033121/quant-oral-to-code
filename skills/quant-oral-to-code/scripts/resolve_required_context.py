from __future__ import annotations


DEFAULT_A_SHARE_CONTEXT = {
    "security_master",
    "st_status",
    "suspension_status",
}

DATA_REQUIREMENT_TO_CONTEXT = {
    "group_membership": "group_membership",
    "benchmark_series": "benchmark_series",
    "minute_or_tick": "minute_or_tick",
}

CROSS_SECTIONAL_FILTER_KINDS = {
    "rolling_return_rank",
    "breakout_with_rank_filter",
    "group_relative_strength",
    "rank_improvement_proxy",
    "liquidity_quantile_filter",
    "sector_breakout_confirmation",
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def resolve_required_context(spec: dict | None) -> dict[str, object]:
    if not isinstance(spec, dict):
        return {
            "required_context_keys": [],
            "blocking_requirements": [],
            "requires_real_data": True,
            "requires_cross_sectional_universe": False,
        }

    required_context: list[str] = []
    blocking_requirements: list[str] = []

    market = str(spec.get("market", ""))
    if market == "A股":
        required_context.extend(sorted(DEFAULT_A_SHARE_CONTEXT))

    selection_filters = spec.get("selection_filters", [])
    requires_cross_sectional_universe = False
    if isinstance(selection_filters, list):
        for item in selection_filters:
            if not isinstance(item, dict):
                continue
            if str(item.get("kind", "")) in CROSS_SECTIONAL_FILTER_KINDS:
                requires_cross_sectional_universe = True
                break

    data_requirements = spec.get("data_requirements", {})
    if isinstance(data_requirements, dict):
        for requirement_list in data_requirements.values():
            if not isinstance(requirement_list, list):
                continue
            for requirement in requirement_list:
                context_key = DATA_REQUIREMENT_TO_CONTEXT.get(str(requirement))
                if context_key == "minute_or_tick":
                    blocking_requirements.append("minute_or_tick_required")
                    continue
                if context_key:
                    required_context.append(context_key)

    return {
        "required_context_keys": _dedupe(required_context),
        "blocking_requirements": _dedupe(blocking_requirements),
        "requires_real_data": True,
        "requires_cross_sectional_universe": requires_cross_sectional_universe,
    }


if __name__ == "__main__":
    import json

    demo = {
        "market": "A股",
        "selection_filters": [{"kind": "group_relative_strength", "lookback": 5}],
        "data_requirements": {
            "板块共振": ["daily_ohlcv", "group_membership", "benchmark_series"],
        },
    }
    print(json.dumps(resolve_required_context(demo), ensure_ascii=False, indent=2))
