from __future__ import annotations

import json
from pathlib import Path
import re


SKILL_ROOT = Path(__file__).resolve().parents[1]


def _load_rules() -> dict[str, object]:
    rules_path = SKILL_ROOT / "references" / "guardrail_rules.json"
    return json.loads(rules_path.read_text(encoding="utf-8"))


def _flatten_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(_flatten_strings(nested))
        return flattened
    if isinstance(value, list):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_strings(item))
        return flattened
    return []


def _contains_any(haystacks: list[str], needles: list[str]) -> bool:
    lowered_haystacks = [item.lower() for item in haystacks if item]
    for needle in needles:
        lowered = needle.lower()
        if re.fullmatch(r"[a-z0-9_ ]+", lowered):
            pattern = re.compile(rf"(?<![a-z0-9_]){re.escape(lowered)}(?![a-z0-9_])")
            if any(pattern.search(haystack) for haystack in lowered_haystacks):
                return True
        elif any(lowered in haystack for haystack in lowered_haystacks):
            return True
    return False


def _collect_matches(haystacks: list[str], needles: list[str]) -> list[str]:
    matches: list[str] = []
    lowered_haystacks = [item.lower() for item in haystacks if item]
    for needle in needles:
        lowered = needle.lower()
        if re.fullmatch(r"[a-z0-9_ ]+", lowered):
            pattern = re.compile(rf"(?<![a-z0-9_]){re.escape(lowered)}(?![a-z0-9_])")
            if any(pattern.search(haystack) for haystack in lowered_haystacks):
                matches.append(needle)
        elif any(lowered in haystack for haystack in lowered_haystacks):
            matches.append(needle)
    return _dedupe(matches)


def _is_negated_match(haystack: str, needle: str) -> bool:
    index = haystack.find(needle)
    if index < 0:
        return False
    prefix = haystack[max(0, index - 8) : index]
    negation_markers = ("不要", "避免", "禁止", "不使用", "不能", "勿", "别")
    return any(marker in prefix for marker in negation_markers)


def _collect_matches_without_negated_context(
    haystacks: list[str], needles: list[str]
) -> list[str]:
    matches: list[str] = []
    for haystack in [item for item in haystacks if item]:
        lowered_haystack = haystack.lower()
        for needle in needles:
            lowered = needle.lower()
            if re.fullmatch(r"[a-z0-9_ ]+", lowered):
                pattern = re.compile(rf"(?<![a-z0-9_]){re.escape(lowered)}(?![a-z0-9_])")
                if pattern.search(lowered_haystack) and not _is_negated_match(haystack, needle):
                    matches.append(needle)
            elif lowered in lowered_haystack and not _is_negated_match(haystack, needle):
                matches.append(needle)
    return _dedupe(matches)


def _has_pit_visibility(spec: dict[str, object]) -> bool:
    if spec.get("pit_visibility") is True:
        return True
    if spec.get("point_in_time_visible") is True:
        return True

    validation = spec.get("validation")
    if isinstance(validation, dict):
        if validation.get("pit_visibility") is True:
            return True
        if validation.get("point_in_time_visible") is True:
            return True

    factor_inputs = spec.get("factor_inputs")
    if isinstance(factor_inputs, list):
        for factor in factor_inputs:
            if isinstance(factor, dict) and (
                factor.get("pit_visible") is True
                or factor.get("pit_visibility") is True
                or factor.get("as_of_date_field")
            ):
                return True
    return False


def _has_holdout(spec: dict[str, object]) -> bool:
    validation = spec.get("validation")
    if isinstance(validation, dict):
        if validation.get("has_holdout") is True:
            return True
        if validation.get("holdout") is True:
            return True
        if validation.get("sample_split") or validation.get("holdout_period"):
            return True

    experiment_protocol = spec.get("experiment_protocol")
    if isinstance(experiment_protocol, dict) and experiment_protocol.get("sample_split"):
        return True

    return False


def _has_same_bar_close(
    spec: dict[str, object], text_fragments: list[str], rules: dict[str, object]
) -> bool:
    execution_requirements = spec.get("execution_requirements")
    if isinstance(execution_requirements, dict):
        if execution_requirements.get("execution_mode") == "same_bar_close":
            return True

    execution = spec.get("execution")
    if isinstance(execution, dict) and execution.get("mode") == "same_bar_close":
        return True

    return _contains_any(text_fragments, list(rules.get("same_bar_close_terms", [])))


def _has_explicit_intraday_granularity(spec: dict[str, object]) -> bool:
    direct_keys = [
        "timeframe",
        "bar_interval",
        "data_granularity",
        "frequency",
        "execution_timeframe",
    ]
    explicit_values = {
        "1m",
        "3m",
        "5m",
        "10m",
        "15m",
        "30m",
        "60m",
        "minute",
        "minutes",
        "min",
        "tick",
        "ticks",
        "intraday",
    }

    for key in direct_keys:
        value = spec.get(key)
        if isinstance(value, str) and value.strip().lower() in explicit_values:
            return True

    for section_key in ("execution_requirements", "execution", "data_contract", "market_data"):
        section = spec.get(section_key)
        if not isinstance(section, dict):
            continue
        for key in direct_keys:
            value = section.get(key)
            if isinstance(value, str) and value.strip().lower() in explicit_values:
                return True

    data_requirements = spec.get("data_requirements")
    if isinstance(data_requirements, dict):
        granularity = data_requirements.get("granularity")
        if isinstance(granularity, str) and granularity.strip().lower() in explicit_values:
            return True

    return False


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def review_guardrails(spec: dict[str, object]) -> dict[str, object]:
    rules = _load_rules()
    flattened = _flatten_strings(spec)
    unresolved_terms = [
        str(item)
        for item in spec.get("unresolved_terms", [])
        if isinstance(item, str) and item.strip()
    ]
    translation_confidence = float(spec.get("translation_confidence", 0.0))

    blocking: list[str] = []
    warnings: list[str] = []
    rule_hits: dict[str, dict[str, object]] = {}

    if unresolved_terms:
        blocking.append("ambiguous_term_unresolved")
        rule_hits["ambiguous_term_unresolved"] = {"unresolved_terms": unresolved_terms}

    if translation_confidence < float(rules.get("translation_confidence_blocking_below", 0.6)):
        blocking.append("low_translation_confidence")
        rule_hits["low_translation_confidence"] = {
            "translation_confidence": translation_confidence
        }

    if _contains_any(flattened, list(rules.get("financial_factor_terms", []))) and not _has_pit_visibility(spec):
        blocking.append("financial_factor_without_pit_visibility")
        rule_hits["financial_factor_without_pit_visibility"] = {
            "evidence": "financial_factor_terms_detected_without_pit_visibility"
        }

    full_sample_matches = _collect_matches(
        flattened, list(rules.get("full_sample_optimization_terms", []))
    )
    if full_sample_matches and not _has_holdout(spec):
        blocking.append("optimized_on_full_sample_without_holdout")
        rule_hits["optimized_on_full_sample_without_holdout"] = {
            "evidence": full_sample_matches,
            "recommended_next_step": "补充样本外验证、时间切分或 walk-forward 方案，禁止先挑最好看版本再定规则。",  # noqa: E501
        }

    future_leakage_matches = _collect_matches_without_negated_context(
        flattened, list(rules.get("future_leakage_terms", []))
    )
    if future_leakage_matches:
        blocking.append("future_leakage_or_hindsight_filtering")
        rule_hits["future_leakage_or_hindsight_filtering"] = {
            "evidence": future_leakage_matches,
            "recommended_next_step": "把入场判定改写成下单时点可见条件，移除收盘后确认、次日结果反筛或其他前视过滤。",  # noqa: E501
        }

    if _has_same_bar_close(spec, flattened, rules):
        warnings.append("same_bar_close_is_optimistic")
        rule_hits["same_bar_close_is_optimistic"] = {
            "suggested_execution_mode": "next_open"
        }

    intraday_matches = _collect_matches(flattened, list(rules.get("intraday_terms", [])))
    if intraday_matches and not _has_explicit_intraday_granularity(spec):
        warnings.append("intraday_semantics_without_granularity")
        rule_hits["intraday_semantics_without_granularity"] = {
            "evidence": intraday_matches,
            "recommended_data_granularity": "minute_or_tick",
            "recommended_next_step": "明确 timeframe、分钟级数据粒度、撮合口径和可回测执行时点，不要用日线外壳承接盘中语义。",  # noqa: E501
        }

    blocking = _dedupe(blocking)
    warnings = _dedupe(warnings)

    if blocking:
        recommended_next_step = (
            "先消除未解释术语，并补齐样本外验证、PIT 可见性与前视隔离口径；未完成前不要进入 DATA_REQUIRED 或代码生成。"
        )
        decision = "blocked"
        claim_level_ceiling = "demo_only"
    elif warnings:
        recommended_next_step = (
            "保留当前 spec，但把执行与数据口径写明确：同 bar 收盘改成 next_open，盘中语义补足分钟级 granularity 和撮合假设。"
        )
        decision = "warning"
        claim_level_ceiling = "portable_backtest"
    else:
        recommended_next_step = "guardrail 通过，可以继续进入数据契约与代码生成阶段。"
        decision = "pass"
        claim_level_ceiling = "research_grade_local"

    return {
        "blocking": blocking,
        "warnings": warnings,
        "recommended_next_step": recommended_next_step,
        "translation_confidence": translation_confidence,
        "decision": decision,
        "claim_level_ceiling": claim_level_ceiling,
        "rule_hits": rule_hits,
    }


if __name__ == "__main__":
    import json as _json

    demo_spec = {
        "source_prompt": "当天收盘最终站稳，且次日还有溢价才算有效。",
        "translation_confidence": 0.91,
        "unresolved_terms": [],
    }
    print(_json.dumps(review_guardrails(demo_spec), ensure_ascii=False, indent=2))
