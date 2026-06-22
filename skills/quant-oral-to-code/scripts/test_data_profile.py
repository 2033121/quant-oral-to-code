from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import duckdb
import pytest

from build_demo_dataset import build_demo_dataset
from detect_data_profile import detect_data_profile
from normalize_to_duckdb import normalize_to_duckdb


def _write_csv(path: Path) -> None:
    path.write_text(
        "symbol,trade_date,open,high,low,close,volume\n"
        "000001.SZ,2024-01-02,10,11,9,10.5,1000\n",
        encoding="utf-8",
    )


def _write_json(path: Path) -> None:
    payload = [
        {
            "symbol": "000001.SZ",
            "trade_date": "2024-01-02",
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10.5,
            "volume": 1000,
        }
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_sqlite(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            create table bars (
                symbol text,
                trade_date text,
                open real,
                high real,
                low real,
                close real,
                volume real
            )
            """
        )
        conn.execute(
            "insert into bars values (?, ?, ?, ?, ?, ?, ?)",
            ("000001.SZ", "2024-01-02", 10, 11, 9, 10.5, 1000),
        )
        conn.commit()
    finally:
        conn.close()


def _write_duckdb(path: Path) -> None:
    conn = duckdb.connect(str(path))
    try:
        conn.execute(
            """
            create table bars as
            select
                '000001.SZ'::varchar as symbol,
                date '2024-01-02' as trade_date,
                10.0::double as open,
                11.0::double as high,
                9.0::double as low,
                10.5::double as close,
                1000.0::double as volume
            """
        )
    finally:
        conn.close()


def _write_parquet(path: Path) -> None:
    conn = duckdb.connect()
    try:
        conn.execute(
            """
            copy (
                select
                    '000001.SZ'::varchar as symbol,
                    date '2024-01-02' as trade_date,
                    10.0::double as open,
                    11.0::double as high,
                    9.0::double as low,
                    10.5::double as close,
                    1000.0::double as volume
            ) to ? (format parquet)
            """,
            [str(path)],
        )
    finally:
        conn.close()


def test_data_profile_detects_csv_parquet_json_sqlite_and_duckdb(tmp_path: Path) -> None:
    writers = {
        "csv": _write_csv,
        "parquet": _write_parquet,
        "json": _write_json,
        "sqlite": _write_sqlite,
        "duckdb": _write_duckdb,
    }
    suffixes = {
        "csv": ".csv",
        "parquet": ".parquet",
        "json": ".json",
        "sqlite": ".sqlite",
        "duckdb": ".duckdb",
    }

    for format_name, writer in writers.items():
        target = tmp_path / f"bars_{format_name}{suffixes[format_name]}"
        writer(target)
        profile = detect_data_profile(target)
        assert profile["mode"] == "portable_csv_mode"
        assert profile["raw_input_format"] == format_name
        assert profile["data_readiness"] == "ready"


def test_data_profile_uses_demo_mode_when_no_data_exists(tmp_path: Path) -> None:
    profile = detect_data_profile(tmp_path)
    assert profile["mode"] == "demo_mode"
    assert profile["raw_input_format"] is None
    assert profile["data_readiness"] == "needs_data"


def test_data_profile_no_data_branch_matches_task2_contract_shape(tmp_path: Path) -> None:
    profile = detect_data_profile(tmp_path)
    assert profile["mode"] in {"demo_mode", "portable_csv_mode", "full_research_mode"}
    assert profile["data_readiness"] in {"demo_only", "needs_data", "ready"}
    assert profile["raw_input_format"] is None


def test_normalize_to_duckdb_rejects_missing_core_columns_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "missing_columns.csv"
    csv_path.write_text(
        "symbol,trade_date,open,high,low,close\n"
        "000001.SZ,2024-01-02,10,11,9,10.5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Missing required core columns"):
        normalize_to_duckdb(csv_path, tmp_path / "market.duckdb", raw_input_format="csv")


def test_normalize_to_duckdb_rejects_garbage_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "garbage.csv"
    csv_path.write_text(
        "foo,bar,baz\n"
        "a,b,c\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Missing required core columns"):
        normalize_to_duckdb(csv_path, tmp_path / "market.duckdb", raw_input_format="csv")


def test_build_demo_dataset_creates_demo_duckdb(tmp_path: Path) -> None:
    db_path = tmp_path / "market.duckdb"
    result = build_demo_dataset(db_path)
    assert db_path.exists()
    assert result["claim_level"] == "demo_only"
    assert result["validation"]["ok"] is True
