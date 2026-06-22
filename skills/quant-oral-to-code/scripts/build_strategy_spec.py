from __future__ import annotations

import json
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def _load_ontology() -> dict:
    ontology_path = SKILL_ROOT / "references" / "domain_ontology.json"
    if ontology_path.exists():
        return json.loads(ontology_path.read_text(encoding="utf-8"))
    return {
        "strategy_families": {},
        "markets": {},
        "timeframes": {},
        "output_requests": {},
        "ambiguous_terms": [],
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            items.append(value)
    return items


def _detect_market(prompt: str, ontology: dict) -> str:
    for canonical, aliases in ontology.get("markets", {}).items():
        if any(alias.lower() in prompt.lower() for alias in aliases):
            return canonical
    if "a股" in prompt.lower() or "沪深" in prompt or "股票" in prompt:
        return "A股"
    return "unknown"


def _detect_timeframe(prompt: str, ontology: dict) -> str:
    for canonical, aliases in ontology.get("timeframes", {}).items():
        if any(alias.lower() in prompt.lower() for alias in aliases):
            return canonical
    if any(token in prompt for token in ("日线", "日K", "日频")):
        return "daily"
    return "unknown"


def _detect_family(prompt: str, ontology: dict) -> str:
    lowered = prompt.lower()
    for canonical, entry in ontology.get("strategy_families", {}).items():
        if any(keyword.lower() in lowered or keyword in prompt for keyword in entry.get("keywords", [])):
            return canonical
    return "unknown"


def _find_output_requests(prompt: str, ontology: dict) -> list[str]:
    lowered = prompt.lower()
    requested: list[str] = []
    for canonical, aliases in ontology.get("output_requests", {}).items():
        if any(alias.lower() in lowered or alias in prompt for alias in aliases):
            requested.append(canonical)
    return _dedupe(requested)


def _find_unresolved_terms(prompt: str, ontology: dict) -> list[str]:
    terms = []
    for term in ontology.get("ambiguous_terms", []):
        if term and term in prompt:
            terms.append(term)
    if "放量" in prompt and "放量确认" not in terms:
        terms.append("放量确认")
    return _dedupe(terms)


def _append_unresolved(unresolved_terms: list[str], term: str) -> None:
    if term and term not in unresolved_terms:
        unresolved_terms.append(term)


def _find_ma_cross(prompt: str) -> dict | None:
    patterns = [
        r"(?P<fast>\d+)\s*[日天]?[均ma线]*[^\d]{0,6}(?:上穿|金叉|交叉|突破)[^\d]{0,6}(?P<slow>\d+)\s*[日天]?[均ma线]*",
        r"ma(?P<fast>\d+)[^\d]{0,6}(?:cross|over|above)[^\d]{0,6}ma(?P<slow>\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            fast = int(match.group("fast"))
            slow = int(match.group("slow"))
            if fast > slow:
                fast, slow = slow, fast
            return {"kind": "moving_average_cross", "fast": fast, "slow": slow}
    return None


def _find_exit_rule(prompt: str) -> dict | None:
    ma_stop = re.search(r"跌破\s*(?P<ma>\d+)\s*[日天]?[均ma线]*\s*止损", prompt)
    if ma_stop:
        return {"kind": "price_below_ma", "ma": int(ma_stop.group("ma"))}
    pct_stop = re.search(r"(?P<pct>\d+(?:\.\d+)?)\s*%\s*止损", prompt)
    if pct_stop:
        return {"kind": "stop_loss_pct", "pct": float(pct_stop.group("pct")) / 100.0}
    return None


def _estimate_confidence(entry_rules: list[dict], unresolved_terms: list[str], outputs: list[str]) -> float:
    score = 0.55
    if entry_rules:
        score += 0.2
    if outputs:
        score += 0.08
    if unresolved_terms:
        score -= min(0.18, 0.04 * len(unresolved_terms))
    return max(0.1, min(0.98, round(score, 2)))


def build_strategy_spec(prompt: str) -> dict:
    ontology = _load_ontology()
    family = _detect_family(prompt, ontology)
    market = _detect_market(prompt, ontology)
    timeframe = _detect_timeframe(prompt, ontology)
    outputs = _find_output_requests(prompt, ontology)
    unresolved_terms = _find_unresolved_terms(prompt, ontology)
    entry_rule = _find_ma_cross(prompt)
    entry_rules = [entry_rule] if entry_rule else []
    exit_rules = []
    exit_rule = _find_exit_rule(prompt)
    if exit_rule:
        exit_rules.append(exit_rule)

    assumptions = []
    if market == "A股":
        assumptions.append("默认按A股现货日频语境理解")
    if timeframe == "daily":
        assumptions.append("默认按日线频率理解")
    if family == "trend_basic" and not entry_rules:
        assumptions.append("识别为趋势策略，但原文未给出可执行入场条件，因此未补 entry_rules")
        _append_unresolved(unresolved_terms, "缺少明确入场规则")
    if ("均线" in prompt or "ma" in prompt.lower()) and not exit_rules:
        assumptions.append("原文提到均线，但未给出明确退出条件，因此未补 exit_rules")
        _append_unresolved(unresolved_terms, "缺少明确退出规则")
    if entry_rules and entry_rules[0].get("kind") == "moving_average_cross":
        assumptions.append("把均线上穿/金叉视为趋势跟随入场")
    if any(term in unresolved_terms for term in ("强势", "放量确认", "放量", "企稳", "站稳")):
        assumptions.append("口语化强弱与量能描述不直接量化，先保留为未消歧项")

    confidence = _estimate_confidence(entry_rules, unresolved_terms, outputs)

    spec = {
        "source_prompt": prompt,
        "strategy_family": family,
        "market": market,
        "timeframe": timeframe,
        "entry_rules": entry_rules,
        "exit_rules": exit_rules,
        "outputs_requested": outputs,
        "translation_confidence": confidence,
        "unresolved_terms": unresolved_terms,
        "assumptions": assumptions,
    }
    return spec
