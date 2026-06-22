from __future__ import annotations

from pathlib import Path

import duckdb


REQUIRED_COLUMNS = ["symbol", "trade_date", "open", "high", "low", "close", "volume"]
NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume"]


def validate_fetched_dataset(db_path: str | Path) -> dict[str, object]:
    target = Path(db_path)
    errors: list[str] = []
    bars_table_name = "bars"

    if not target.exists():
        errors.append("duckdb_file_missing")
        return {"ok": False, "errors": errors, "storage_target": str(target)}

    conn = duckdb.connect(str(target), read_only=True)
    try:
        table_exists = conn.execute(
            "select count(*) from information_schema.tables where table_name = ?",
            [bars_table_name],
        ).fetchone()[0]
        if not table_exists:
            errors.append("bars_table_missing")
            return {"ok": False, "errors": errors, "storage_target": str(target)}

        table_info = conn.execute(f'pragma table_info("{bars_table_name}")').fetchall()
        existing_columns = [str(row[1]) for row in table_info]
        missing_columns = [name for name in REQUIRED_COLUMNS if name not in existing_columns]
        if missing_columns:
            errors.append("core_columns_missing:" + ",".join(missing_columns))
            return {"ok": False, "errors": errors, "storage_target": str(target)}

        row_count = conn.execute(f'SELECT COUNT(*) FROM "{bars_table_name}"').fetchone()[0]
        if row_count < 1:
            errors.append("bars_table_empty")
            return {"ok": False, "errors": errors, "storage_target": str(target)}

        for column_name in REQUIRED_COLUMNS:
            null_count = conn.execute(
                f'SELECT COUNT(*) FROM "{bars_table_name}" WHERE "{column_name}" IS NULL'
            ).fetchone()[0]
            if null_count > 0:
                errors.append(f"core_column_has_nulls:{column_name}:{int(null_count)}")

        for column_name in NUMERIC_COLUMNS:
            non_finite_count = conn.execute(
                f'SELECT COUNT(*) FROM "{bars_table_name}" WHERE NOT isfinite("{column_name}")'
            ).fetchone()[0]
            if non_finite_count > 0:
                errors.append(
                    f"numeric_column_has_non_finite_values:{column_name}:{int(non_finite_count)}"
                )

        duplicate_count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT symbol, trade_date
                FROM "{bars_table_name}"
                GROUP BY symbol, trade_date
                HAVING COUNT(*) > 1
            ) duplicate_rows
            """
        ).fetchone()[0]
        if duplicate_count > 0:
            errors.append(f"duplicate_symbol_trade_date_keys:{int(duplicate_count)}")

        if errors:
            return {"ok": False, "errors": errors, "storage_target": str(target)}
    finally:
        conn.close()

    return {
        "ok": True,
        "errors": [],
        "storage_target": str(target),
        "bars_table_name": bars_table_name,
        "core_columns": list(REQUIRED_COLUMNS),
        "row_count": int(row_count),
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("usage: validate_fetched_dataset.py OUTPUT_DUCKDB")
    print(json.dumps(validate_fetched_dataset(sys.argv[1]), ensure_ascii=False, indent=2))
