from __future__ import annotations

from pathlib import Path
import json


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_registry() -> dict:
    registry_path = _skill_root() / "references" / "example_registry.json"
    return json.loads(registry_path.read_text(encoding="utf-8"))


def resolve_codegen_mode(spec: dict) -> dict[str, object]:
    registry = _load_registry()
    symbols = spec.get("symbols")
    asset_count = len(symbols) if isinstance(symbols, list) else 1
    if asset_count > 1:
        template_key = "portfolio_trend_basic"
    else:
        template_key = "single_asset_trend_basic"

    template_entry = registry["templates"][template_key]
    return {
        "mode": str(template_entry["mode"]),
        "template": str(template_entry["template"]),
        "template_key": template_key,
        "asset_count": asset_count,
        "supports_future_modes": [
            "standalone_generated",
            "standalone_mapped",
            "chanlun_or_liangxue_generated",
        ],
    }


if __name__ == "__main__":
    demo_spec = {"strategy_family": "trend_basic"}
    print(json.dumps(resolve_codegen_mode(demo_spec), ensure_ascii=False, indent=2))
