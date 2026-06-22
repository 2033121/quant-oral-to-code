from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from normalize_to_duckdb import normalize_to_duckdb


def test_duckdb_readonly_can_read_normalized_bars(tmp_path: Path) -> None:
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "symbol,trade_date,open,high,low,close,volume\n"
        "000001.SZ,2024-01-02,10,11,9,10.5,1000\n"
        "000001.SZ,2024-01-03,10.5,11.2,10.3,11.0,1200\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "market.duckdb"
    normalize_to_duckdb(csv_path, db_path, raw_input_format="csv", adjustment_mode="qfq")

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        row_count = conn.execute("select count(*) from bars").fetchone()[0]
        first_symbol = conn.execute("select symbol from bars order by trade_date limit 1").fetchone()[0]
    finally:
        conn.close()

    assert row_count == 2
    assert first_symbol == "000001.SZ"


def test_duckdb_readonly_rejects_write_operations(tmp_path: Path) -> None:
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "symbol,trade_date,open,high,low,close,volume\n"
        "000001.SZ,2024-01-02,10,11,9,10.5,1000\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "market.duckdb"
    normalize_to_duckdb(csv_path, db_path, raw_input_format="csv", adjustment_mode="qfq")

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        with pytest.raises(Exception):
            conn.execute("create table should_fail(id integer)")
    finally:
        conn.close()


def test_readonly_connection_targets_expected_normalized_market_path(tmp_path: Path) -> None:
    workspace = tmp_path / "generated_strategies" / "ma_demo"
    normalized_dir = workspace / "data" / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    db_path = normalized_dir / "market.duckdb"

    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "symbol,trade_date,open,high,low,close,volume\n"
        "000001.SZ,2024-01-02,10,11,9,10.5,1000\n",
        encoding="utf-8",
    )
    normalize_to_duckdb(csv_path, db_path, raw_input_format="csv", adjustment_mode="qfq")

    expected_path = workspace / "data" / "normalized" / "market.duckdb"
    conn = duckdb.connect(str(expected_path), read_only=True)
    try:
        table_names = conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'main'
            order by table_name
            """
        ).fetchall()
    finally:
        conn.close()

    assert expected_path.name == "market.duckdb"
    assert [row[0] for row in table_names] == ["bars"]
