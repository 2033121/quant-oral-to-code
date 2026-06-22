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
        flattened = []
        for item in value:
            flattened.extend(_flatten_strings(item))
        return flattened
    return []


def _contains_any(haystacks: list[str], needles: list[str]) -> bool:
    lowered_haystacks = [item.lower() for item in haystacks if item]
    for needle in needles:
        lowered = needle.lower()
        if re.fullmatch(r"[a-z_ ]+", lowered):
            pattern = re.compile(rf"(?<![a-z0-9_]){re.escape(lowered)}(?![a-z0-9_])")
            if any(pattern.search(haystack) for haystack in lowered_haystacks):
                return True
        elif any(lowered in haystack for haystack in lowered_haystacks):
            return True
    return False


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


def _has_same_bar_close(spec: dict[str, object], text_fragments: list[str], rules: dict[str, object]) -> bool:
    execution_requirements = spec.get("execution_requirements")
    if isinstance(execution_requirements, dict):
        if execution_requirements.get("execution_mode") == "same_bar_close":
            return True

    execution = spec.get("execution")
    if isinstance(execution, dict) and execution.get("mode") == "same_bar_close":
        return True

    return _contains_any(text_fragments, list(rules.get("same_bar_close_terms", [])))


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

    if _contains_any(flattened, list(rules.get("full_sample_optimization_terms", []))) and not _has_holdout(spec):
        blocking.append("optimized_on_full_sample_without_holdout")
        rule_hits["optimized_on_full_sample_without_holdout"] = {
            "evidence": "full_sample_optimization_detected_without_holdout"
        }

    if _has_same_bar_close(spec, flattened, rules):
        warnings.append("same_bar_close_is_optimistic")
        rule_hits["same_bar_close_is_optimistic"] = {
            "suggested_execution_mode": "next_open"
        }

    blocking = _dedupe(blocking)
    warnings = _dedupe(warnings)

    if blocking:
        recommended_next_step = "先补齐模糊术语消歧、PIT/样本外验证口径，再决定是否进入 DATA_REQUIRED 或继续代码生成。"
        decision = "blocked"
        claim_level_ceiling = "demo_only"
    elif warnings:
        recommended_next_step = "保持当前 spec，但把执行假设改成 next_open 并在结果说明中标注乐观成交风险。"
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
        "source_prompt": "收盘买入，按 PE 和 ROE 选股，再在全样本上调到最好。",
        "translation_confidence": 0.52,
        "unresolved_terms": ["强势"],
    }
    print(_json.dumps(review_guardrails(demo_spec), ensure_ascii=False, indent=2))
