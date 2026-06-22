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

    exit_ma: str | int | None = "None"
    stop_loss_pct: str | float | None = "None"
    if exit_rule:
        if exit_rule.get("kind") == "price_below_ma":
            exit_ma = int(exit_rule["ma"])
        elif exit_rule.get("kind") == "stop_loss_pct":
            stop_loss_pct = float(exit_rule["pct"])

    return {
        "strategy_name": str(spec.get("strategy_name", "generated_strategy")),
        "strategy_family": str(spec.get("strategy_family", "trend_basic")),
        "market": str(spec.get("market", "unknown")),
        "timeframe": str(spec.get("timeframe", "unknown")),
        "fast_ma": int(entry_rule.get("fast", 5)),
        "slow_ma": int(entry_rule.get("slow", 20)),
        "exit_ma": exit_ma,
        "stop_loss_pct": stop_loss_pct,
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
