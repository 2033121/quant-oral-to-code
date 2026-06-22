from __future__ import annotations

import re

from build_strategy_spec import build_strategy_spec


def _pick_source(prompt: str, candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate and candidate in prompt:
            return candidate
    return ""


def _extract_match(prompt: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def _output_source_text(prompt: str, output_name: str) -> str:
    source_map = {
        "equity_curve": ["收益曲线", "资金曲线", "净值曲线"],
        "max_drawdown": ["最大回撤", "回撤曲线", "回撤"],
        "annual_return": ["年化收益", "年化"],
        "win_rate": ["胜率"],
        "sharpe_ratio": ["夏普", "Sharpe"],
    }
    return _pick_source(prompt, source_map.get(output_name, []))


def emit_translation_trace(prompt: str, spec: dict) -> dict:
    if not spec:
        spec = build_strategy_spec(prompt)

    mappings: list[dict] = []

    mappings.append(
        {
            "source_text": _pick_source(prompt, ["A股", "A股市场", "沪深", "A股日线"]),
            "field_path": "market",
            "mapped_value": spec.get("market", "unknown"),
            "assumption": "按市场关键词直接映射为 canonical market",
            "confidence": 0.98 if spec.get("market") != "unknown" else 0.4,
        }
    )
    mappings.append(
        {
            "source_text": _pick_source(prompt, ["日线", "日K", "日频", "daily"]),
            "field_path": "timeframe",
            "mapped_value": spec.get("timeframe", "unknown"),
            "assumption": "按日线/日K语义直接归一化",
            "confidence": 0.95 if spec.get("timeframe") != "unknown" else 0.4,
        }
    )

    if spec.get("entry_rules"):
        mappings.append(
            {
                "source_text": _extract_match(
                    prompt,
                    [
                        r"\d+\s*[日天]?[均ma线]*[^\d]{0,6}(?:上穿|金叉|交叉|突破)[^\d]{0,6}\d+\s*[日天]?[均ma线]*",
                        r"ma\d+[^\d]{0,6}(?:cross|over|above)[^\d]{0,6}ma\d+",
                    ],
                ),
                "field_path": "entry_rules[0]",
                "mapped_value": spec["entry_rules"][0],
                "assumption": "把均线上穿/金叉抽象为 moving_average_cross",
                "confidence": 0.9,
            }
        )

    if spec.get("exit_rules"):
        mappings.append(
            {
                "source_text": _extract_match(
                    prompt,
                    [
                        r"跌破\s*\d+\s*[日天]?[均ma线]*\s*止损",
                        r"\d+(?:\.\d+)?\s*%\s*止损",
                    ],
                ),
                "field_path": "exit_rules[0]",
                "mapped_value": spec["exit_rules"][0],
                "assumption": "把止损/跌破均线抽象为退出规则",
                "confidence": 0.88,
            }
        )

    for output_name in spec.get("outputs_requested", []):
        mappings.append(
            {
                "source_text": _output_source_text(prompt, output_name),
                "field_path": "outputs_requested",
                "mapped_value": output_name,
                "assumption": "把收益曲线、最大回撤等显式需求归入输出请求",
                "confidence": 0.9,
            }
        )

    for term in spec.get("unresolved_terms", []):
        mappings.append(
            {
                "source_text": term,
                "field_path": "unresolved_terms[]",
                "mapped_value": term,
                "assumption": "该表达缺少可直接执行的量化阈值或定义",
                "confidence": 0.5,
            }
        )

    return {
        "prompt": prompt,
        "mappings": mappings,
        "assumptions": list(spec.get("assumptions", [])),
        "unresolved_terms": list(spec.get("unresolved_terms", [])),
        "translation_confidence": spec.get("translation_confidence", 0.0),
    }
