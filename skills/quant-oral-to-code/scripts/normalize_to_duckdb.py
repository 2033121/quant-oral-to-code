from __future__ import annotations

import csv
import json
import math
import sqlite3
from datetime import date, datetime
from pathlib import Path

import duckdb


CORE_COLUMNS = ["symbol", "trade_date", "open", "high", "low", "close", "volume"]
NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume"]
SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}
DUCKDB_SUFFIXES = {".duckdb", ".ddb"}
COLUMN_ALIASES = {
    "symbol": {"symbol", "ticker", "code", "ts_code"},
    "trade_date": {"trade_date", "date", "datetime", "day", "time"},
    "open": {"open", "open_price"},
    "high": {"high", "high_price"},
    "low": {"low", "low_price"},
    "close": {"close", "close_price"},
    "volume": {"volume", "vol", "amount_volume"},
}


def _normalize_name(name: str) -> str:
    return "".join(ch for ch in name.strip().lower() if ch.isalnum() or ch == "_")


def _build_alias_lookup() -> dict[str, str]:
    alias_lookup: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lookup[_normalize_name(alias)] = canonical
    return alias_lookup


ALIAS_LOOKUP = _build_alias_lookup()


def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".parquet":
        return "parquet"
    if suffix == ".json":
        return "json"
    if suffix in SQLITE_SUFFIXES:
        return "sqlite"
    if suffix in DUCKDB_SUFFIXES:
        return "duckdb"
    raise ValueError(f"Unsupported input format for {path}")


def _rows_from_csv(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _rows_from_json(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = []
        for key in ("bars", "data", "items", "rows", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                rows = value
                break
        if not rows:
            rows = [payload]
    else:
        raise ValueError("JSON input must be an object or array")
    if not rows:
        return []
    if not isinstance(rows[0], dict):
        raise ValueError("JSON rows must be objects")
    return rows


def _choose_sqlite_table(conn: sqlite3.Connection) -> str:
    table_names = [
        row[0]
        for row in conn.execute(
            "select name from sqlite_master where type = 'table' order by name"
        ).fetchall()
    ]
    if not table_names:
        raise ValueError("SQLite input has no tables")
    return "bars" if "bars" in table_names else table_names[0]


def _rows_from_sqlite(path: Path) -> list[dict[str, object]]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        table_name = _choose_sqlite_table(conn)
        rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _choose_duckdb_table(conn: duckdb.DuckDBPyConnection) -> str:
    table_names = [
        str(row[0])
        for row in conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema not in ('information_schema', 'pg_catalog')
            order by table_name
            """
        ).fetchall()
    ]
    if not table_names:
        raise ValueError("DuckDB input has no tables")
    return "bars" if "bars" in table_names else table_names[0]


def _rows_from_parquet(path: Path) -> list[dict[str, object]]:
    conn = duckdb.connect()
    try:
        rows = conn.execute("select * from read_parquet(?)", [str(path)]).fetchall()
        columns = [item[0] for item in conn.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def _rows_from_duckdb(path: Path) -> list[dict[str, object]]:
    conn = duckdb.connect(str(path), read_only=True)
    try:
        table_name = _choose_duckdb_table(conn)
        rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
        columns = [item[0] for item in conn.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def _load_rows(path: Path, raw_input_format: str | None) -> tuple[list[dict[str, object]], str]:
    format_name = raw_input_format or _detect_format(path)
    if format_name == "csv":
        return _rows_from_csv(path), format_name
    if format_name == "json":
        return _rows_from_json(path), format_name
    if format_name == "sqlite":
        return _rows_from_sqlite(path), format_name
    if format_name == "duckdb":
        return _rows_from_duckdb(path), format_name
    if format_name == "parquet":
        return _rows_from_parquet(path), format_name
    raise ValueError(f"Unsupported raw_input_format: {format_name}")


def _resolve_column_mapping(rows: list[dict[str, object]]) -> dict[str, str]:
    if not rows:
        raise ValueError("No rows found in input source")
    mapping: dict[str, str] = {}
    for source_name in rows[0].keys():
        canonical_name = ALIAS_LOOKUP.get(_normalize_name(str(source_name)))
        if canonical_name and canonical_name not in mapping:
            mapping[canonical_name] = str(source_name)
    missing_columns = [name for name in CORE_COLUMNS if name not in mapping]
    if missing_columns:
        raise ValueError(
            "Missing required core columns after mapping: " + ",".join(missing_columns)
        )
    return mapping


def _parse_symbol(value: object, row_index: int) -> str:
    if value is None:
        raise ValueError(f"Invalid symbol at row {row_index}: null")
    symbol = str(value).strip()
    if not symbol:
        raise ValueError(f"Invalid symbol at row {row_index}: blank")
    return symbol


def _parse_trade_date(value: object, row_index: int) -> str:
    if value is None:
        raise ValueError(f"Invalid trade_date at row {row_index}: null")
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        raise ValueError(f"Invalid trade_date at row {row_index}: blank")
    normalized = text.replace("/", "-")
    for parser in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(normalized, parser).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Invalid trade_date at row {row_index}: {text}")


def _parse_float(value: object, column_name: str, row_index: int) -> float:
    if value is None:
        raise ValueError(f"Invalid {column_name} at row {row_index}: null")
    text = str(value).strip()
    if not text:
        raise ValueError(f"Invalid {column_name} at row {row_index}: blank")
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"Invalid {column_name} at row {row_index}: {text}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Invalid {column_name} at row {row_index}: non-finite value {text}")
    return parsed


def _prepare_rows(rows: list[dict[str, object]]) -> list[tuple[object, ...]]:
    mapping = _resolve_column_mapping(rows)
    prepared: list[tuple[object, ...]] = []
    seen_keys: set[tuple[str, str]] = set()
    for row_index, row in enumerate(rows, start=1):
        symbol = _parse_symbol(row.get(mapping["symbol"]), row_index)
        trade_date = _parse_trade_date(row.get(mapping["trade_date"]), row_index)
        primary_key = (symbol, trade_date)
        if primary_key in seen_keys:
            raise ValueError(
                f"Duplicate (symbol, trade_date) key at row {row_index}: {symbol}, {trade_date}"
            )
        seen_keys.add(primary_key)
        prepared.append(
            (
                symbol,
                trade_date,
                _parse_float(row.get(mapping["open"]), "open", row_index),
                _parse_float(row.get(mapping["high"]), "high", row_index),
                _parse_float(row.get(mapping["low"]), "low", row_index),
                _parse_float(row.get(mapping["close"]), "close", row_index),
                _parse_float(row.get(mapping["volume"]), "volume", row_index),
            )
        )
    return prepared


def normalize_to_duckdb(
    input_path: str | Path,
    db_path: str | Path,
    raw_input_format: str | None = None,
    adjustment_mode: str = "none",
) -> dict[str, object]:
    source_path = Path(input_path)
    target_path = Path(db_path)
    rows, detected_format = _load_rows(source_path, raw_input_format=raw_input_format)
    prepared_rows = _prepare_rows(rows)

    if not prepared_rows:
        raise ValueError(f"No rows found in input source: {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(target_path))
    try:
        conn.execute('DROP TABLE IF EXISTS "bars"')
        conn.execute(
            """
            CREATE TABLE "bars" (
                symbol VARCHAR,
                trade_date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE
            )
            """
        )
        conn.executemany(
            'INSERT INTO "bars" VALUES (?, ?, ?, ?, ?, ?, ?)',
            prepared_rows,
        )
    finally:
        conn.close()

    return {
        "storage_format": "duckdb",
        "storage_target": str(target_path),
        "bars_table_name": "bars",
        "raw_input_format": detected_format,
        "adjustment_mode": adjustment_mode,
        "row_count": len(prepared_rows),
        "normalized_columns": list(CORE_COLUMNS),
    }


if __name__ == "__main__":
    import json as _json
    import sys

    if len(sys.argv) < 3:
        raise SystemExit("usage: normalize_to_duckdb.py INPUT_PATH OUTPUT_DUCKDB")
    result = normalize_to_duckdb(sys.argv[1], sys.argv[2])
    print(_json.dumps(result, ensure_ascii=False, indent=2))
