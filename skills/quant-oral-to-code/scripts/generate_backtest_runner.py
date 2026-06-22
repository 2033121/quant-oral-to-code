from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PROTOCOL = {
    "data": {
        "storage_format": "duckdb",
        "storage_path": "data/normalized/market.duckdb",
        "bars_table_name": "bars",
        "table_layout": "single_table",
    },
    "sample_split": {
        "train": {"start": "2018-01-01", "end": "2022-12-31"},
        "validation": {"start": "2023-01-01", "end": "2023-12-31"},
        "test": {"start": "2024-01-01", "end": "2024-12-31"},
    },
    "costs": {
        "commission_bps": 8,
        "slippage_bps": 10,
        "stamp_duty_bps": 10,
    },
    "execution": {
        "mode": "next_open",
        "price_field": "open",
        "allow_same_bar_fill": False,
    },
}


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_template(template_name: str) -> str:
    template_path = _skill_root() / "templates" / template_name
    return template_path.read_text(encoding="utf-8")


def _deep_copy(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _build_protocol(spec: dict) -> dict[str, object]:
    protocol = _deep_copy(DEFAULT_PROTOCOL)
    if not isinstance(protocol, dict):
        raise TypeError("default protocol must be a dict")

    spec_protocol = spec.get("experiment_protocol")
    if isinstance(spec_protocol, dict):
        for key in ("sample_split", "costs", "execution"):
            if isinstance(spec_protocol.get(key), dict):
                protocol[key].update(spec_protocol[key])

    spec_data = spec.get("data")
    if isinstance(spec_data, dict):
        if isinstance(spec_data.get("bars_table_name"), str) and spec_data["bars_table_name"].strip():
            protocol["data"]["bars_table_name"] = spec_data["bars_table_name"].strip()

    protocol["data"]["storage_path"] = "data/normalized/market.duckdb"
    protocol["data"]["storage_format"] = "duckdb"
    protocol["data"]["bars_table_name"] = "bars"
    protocol["execution"]["mode"] = "next_open"
    protocol["execution"]["allow_same_bar_fill"] = False
    return protocol


def generate_backtest_runner(spec: dict, output_dir: str | Path) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    protocol = _build_protocol(spec)
    runner_template = _load_template("run_backtest.py.tmpl")
    runner_text = runner_template.format(
        bars_table_name=str(protocol["data"]["bars_table_name"]),
    )

    runner_file = output_path / "run_backtest.py"
    runner_file.write_text(runner_text, encoding="utf-8")

    protocol_file = output_path / "experiment_protocol.json"
    protocol_file.write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "runner_file": str(runner_file),
        "protocol_file": str(protocol_file),
    }
