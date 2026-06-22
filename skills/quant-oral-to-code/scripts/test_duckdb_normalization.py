from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from normalize_to_duckdb import normalize_to_duckdb
from validate_fetched_dataset import validate_fetched_dataset


def test_normalize_to_duckdb_creates_bars_table(tmp_path: Path) -> None:
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "ticker,date,open_price,high_price,low_price,close_price,vol\n"
        "000001.SZ,2024-01-02,10,11,9,10.5,1000\n"
        "000001.SZ,2024-01-03,10.5,11.2,10.3,11.0,1200\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "market.duckdb"

    result = normalize_to_duckdb(
        csv_path,
        db_path,
        raw_input_format="csv",
        adjustment_mode="qfq",
    )

    assert result["bars_table_name"] == "bars"
    assert result["raw_input_format"] == "csv"
    assert db_path.exists()

    validation = validate_fetched_dataset(db_path)
    assert validation["ok"] is True
    assert validation["row_count"] == 2

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            "select symbol, trade_date, open, high, low, close, volume from bars order by trade_date"
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 2
    assert rows[0][0] == "000001.SZ"


def test_validate_fetched_dataset_reports_missing_database(tmp_path: Path) -> None:
    validation = validate_fetched_dataset(tmp_path / "missing.duckdb")
    assert validation["ok"] is False
    assert "duckdb_file_missing" in validation["errors"]


def test_normalize_to_duckdb_rejects_unparseable_core_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad_values.csv"
    csv_path.write_text(
        "symbol,trade_date,open,high,low,close,volume\n"
        "000001.SZ,not-a-date,foo,11,9,10.5,1000\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid trade_date|Invalid open"):
        normalize_to_duckdb(csv_path, tmp_path / "market.duckdb", raw_input_format="csv")


def test_normalize_to_duckdb_rejects_duplicate_symbol_trade_date(tmp_path: Path) -> None:
    csv_path = tmp_path / "duplicate_keys.csv"
    csv_path.write_text(
        "symbol,trade_date,open,high,low,close,volume\n"
        "000001.SZ,2024-01-02,10,11,9,10.5,1000\n"
        "000001.SZ,2024-01-02,10.1,11.1,9.1,10.6,1100\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate \\(symbol, trade_date\\) key"):
        normalize_to_duckdb(csv_path, tmp_path / "market.duckdb", raw_input_format="csv")


@pytest.mark.parametrize("bad_value", ["NaN", "inf", "-inf"])
def test_normalize_to_duckdb_rejects_non_finite_numeric_values(
    tmp_path: Path, bad_value: str
) -> None:
    csv_path = tmp_path / f"non_finite_{bad_value.replace('-', 'neg_')}.csv"
    csv_path.write_text(
        "symbol,trade_date,open,high,low,close,volume\n"
        f"000001.SZ,2024-01-02,{bad_value},11,9,10.5,1000\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-finite value"):
        normalize_to_duckdb(csv_path, tmp_path / "market.duckdb", raw_input_format="csv")


def test_validate_fetched_dataset_rejects_non_finite_numeric_values(tmp_path: Path) -> None:
    db_path = tmp_path / "non_finite.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            create table bars (
                symbol varchar,
                trade_date date,
                open double,
                high double,
                low double,
                close double,
                volume double
            )
            """
        )
        conn.execute(
            """
            insert into bars values
            ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5, 1000),
            ('000001.SZ', '2024-01-03', 'NaN'::double, 11, 9, 10.5, 1000)
            """
        )
    finally:
        conn.close()

    validation = validate_fetched_dataset(db_path)
    assert validation["ok"] is False
    assert "numeric_column_has_non_finite_values:open:1" in validation["errors"]
