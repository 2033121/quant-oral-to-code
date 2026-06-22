from __future__ import annotations

from pathlib import Path

from normalize_to_duckdb import normalize_to_duckdb
from validate_fetched_dataset import validate_fetched_dataset


def build_demo_dataset(output_path: str | Path) -> dict[str, object]:
    target = Path(output_path)
    sample_csv = Path(__file__).resolve().parent.parent / "templates" / "sample_ohlcv.csv"
    result = normalize_to_duckdb(
        sample_csv,
        target,
        raw_input_format="csv",
        adjustment_mode="none",
    )
    validation = validate_fetched_dataset(target)
    return {
        "storage_target": str(target),
        "claim_level": "demo_only",
        "seed_source": str(sample_csv),
        "normalization": result,
        "validation": validation,
    }


if __name__ == "__main__":
    import json
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("market.duckdb")
    print(json.dumps(build_demo_dataset(target), ensure_ascii=False, indent=2))
