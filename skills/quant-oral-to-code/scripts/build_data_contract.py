from __future__ import annotations

import hashlib
import json
from pathlib import Path


REQUIRED_TABLES = ["bars"]
REQUIRED_COLUMNS = ["symbol", "trade_date", "open", "high", "low", "close", "volume"]
PRIMARY_KEY = ["symbol", "trade_date"]
ALLOWED_RAW_INPUT_FORMATS = {"csv", "json", "api", "sqlite", "duckdb", "parquet"}


def compute_data_hash(storage_target: Path, raw_input_format: str, provider_name: str, adjustment_mode: str) -> str:
    if not storage_target.exists():
        raise FileNotFoundError(f"DuckDB storage target does not exist: {storage_target}")
    hasher = hashlib.sha256()
    hasher.update(storage_target.read_bytes())
    return hasher.hexdigest()


def build_data_contract(
    storage_target: str | Path,
    raw_input_format: str,
    provider_name: str,
    adjustment_mode: str,
    write_disposition: str = "overwrite",
) -> dict[str, object]:
    target_path = Path(storage_target)
    if raw_input_format not in ALLOWED_RAW_INPUT_FORMATS:
        raise ValueError(f"Unsupported raw_input_format: {raw_input_format}")
    if not target_path.exists():
        raise FileNotFoundError(f"DuckDB storage target does not exist: {target_path}")
    return {
        "storage_format": "duckdb",
        "storage_target": str(target_path),
        "bars_table_name": "bars",
        "table_layout": "single_table",
        "primary_key": list(PRIMARY_KEY),
        "required_tables": list(REQUIRED_TABLES),
        "required_columns": list(REQUIRED_COLUMNS),
        "write_disposition": write_disposition,
        "raw_input_format": raw_input_format,
        "provider_name": provider_name,
        "adjustment_mode": adjustment_mode,
        "data_hash": compute_data_hash(
            target_path,
            raw_input_format=raw_input_format,
            provider_name=provider_name,
            adjustment_mode=adjustment_mode,
        ),
    }


if __name__ == "__main__":
    target = Path("generated_strategies/example/data/normalized/market.duckdb")
    if target.exists():
        example = build_data_contract(
            storage_target=target,
            raw_input_format="csv",
            provider_name="manual_csv",
            adjustment_mode="qfq",
        )
        print(json.dumps(example, ensure_ascii=False, indent=2))
    else:
        print(f"missing example duckdb: {target}")
