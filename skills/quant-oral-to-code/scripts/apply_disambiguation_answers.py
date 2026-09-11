from __future__ import annotations

import json
from pathlib import Path

from build_strategy_spec import estimate_translation_confidence


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_library() -> dict[str, object]:
    path = _skill_root() / "references" / "term_disambiguation_library.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _normalized_answers(answers: object) -> dict[str, str]:
    if not isinstance(answers, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in answers.items():
        if isinstance(key, str) and isinstance(value, str):
            normalized[key] = value
    return normalized


def apply_disambiguation_answers(spec: dict, answers: dict[str, str]) -> dict[str, object]:
    updated = json.loads(json.dumps(spec, ensure_ascii=False))
    library = _load_library()
    normalized_answers = _normalized_answers(answers)

    unresolved_terms = [
        str(term)
        for term in updated.get("unresolved_terms", [])
        if isinstance(term, str) and term.strip()
    ]
    assumptions = [
        str(item)
        for item in updated.get("assumptions", [])
        if isinstance(item, str) and item.strip()
    ]
    entry_rules = list(updated.get("entry_rules", [])) if isinstance(updated.get("entry_rules"), list) else []
    filters = list(updated.get("selection_filters", [])) if isinstance(updated.get("selection_filters"), list) else []
    data_requirements = (
        dict(updated.get("data_requirements", {}))
        if isinstance(updated.get("data_requirements"), dict)
        else {}
    )
    disambiguated_terms = (
        list(updated.get("disambiguated_terms", []))
        if isinstance(updated.get("disambiguated_terms"), list)
        else []
    )

    remaining_terms: list[str] = []

    for term in unresolved_terms:
        answer_id = normalized_answers.get(term)
        library_entry = library.get(term)
        if not answer_id or not isinstance(library_entry, dict):
            remaining_terms.append(term)
            continue

        matched_choice = None
        for choice in library_entry.get("choices", []):
            if isinstance(choice, dict) and str(choice.get("id")) == answer_id:
                matched_choice = choice
                break

        if not isinstance(matched_choice, dict):
            remaining_terms.append(term)
            continue

        rule = matched_choice.get("rule", {})
        if not isinstance(rule, dict):
            remaining_terms.append(term)
            continue

        kind = str(rule.get("kind", ""))
        if kind in {
            "rolling_return_rank",
            "breakout_with_rank_filter",
            "liquidity_quantile_filter",
            "volume_ratio_filter",
            "group_relative_strength",
            "followthrough_strength",
            "consolidation_filter",
            "close_location_value_filter",
            "volume_price_strength_proxy",
            "swing_overlap_zone",
            "box_consolidation",
            "macd_divergence_proxy",
            "rsi_divergence_proxy",
            "retest_then_breakout",
            "gap_open_filter",
            "vwap_support",
        }:
            filters.append(rule)
        elif kind in {
            "intraday_vwap_support",
            "intraday_reclaim_level",
            "intraday_granularity_required",
            "auction_detail_required",
            "external_chip_distribution_required",
            "external_net_inflow_required",
        }:
            filters.append(rule)
        elif kind == "daily_proxy_requested":
            _append_unique(assumptions, f"术语“{term}”已按日线代理处理，未保留原始分时语义。")
        elif kind == "manual_definition_required":
            remaining_terms.append(term)
            _append_unique(assumptions, f"术语“{term}”仍需用户补充自定义规则。")
            continue
        else:
            filters.append(rule)

        requires = matched_choice.get("requires", [])
        if isinstance(requires, list):
            data_requirements[term] = requires
            for requirement in requires:
                if isinstance(requirement, str):
                    _append_unique(assumptions, f"术语“{term}”已选择定义，依赖条件：{requirement}")

        disambiguated_terms.append(
            {
                "term": term,
                "choice_id": str(matched_choice.get("id", "")),
                "label": str(matched_choice.get("label", "")),
                "rule": rule,
            }
        )

    updated["unresolved_terms"] = remaining_terms
    updated["assumptions"] = assumptions
    updated["entry_rules"] = entry_rules
    updated["selection_filters"] = filters
    updated["data_requirements"] = data_requirements
    updated["disambiguated_terms"] = disambiguated_terms
    updated["translation_confidence"] = estimate_translation_confidence(updated)
    return updated


if __name__ == "__main__":
    demo_spec = {"unresolved_terms": ["龙头", "筹码"], "assumptions": []}
    demo_answers = {"龙头": "leader_return_rank", "筹码": "chip_platform_consolidation"}
    print(json.dumps(apply_disambiguation_answers(demo_spec, demo_answers), ensure_ascii=False, indent=2))
