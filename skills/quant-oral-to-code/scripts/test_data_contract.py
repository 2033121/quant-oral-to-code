from __future__ import annotations

import json
from pathlib import Path

import duckdb
import jsonschema

from build_data_contract import build_data_contract


def _create_market_duckdb(db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
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
        con.execute(
            """
            insert into bars values
            ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5, 1000)
            """
        )
    finally:
        con.close()
    return db_path


def test_data_contract_is_fixed_to_duckdb_core_contract(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "market.duckdb")
    contract = build_data_contract(
        storage_target=db_path,
        raw_input_format="parquet",
        provider_name="akshare",
        adjustment_mode="hfq",
    )

    assert contract["storage_format"] == "duckdb"
    assert contract["bars_table_name"] == "bars"
    assert contract["primary_key"] == ["symbol", "trade_date"]
    assert contract["required_tables"] == ["bars"]
    assert contract["required_columns"] == [
        "symbol",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert contract["data_hash"]


def test_data_contract_schema_rejects_non_single_table_layout(tmp_path: Path):
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "data_contract.schema.json").read_text(encoding="utf-8")
    )
    db_path = _create_market_duckdb(tmp_path / "market.duckdb")
    contract = build_data_contract(
        storage_target=db_path,
        raw_input_format="csv",
        provider_name="manual_csv",
        adjustment_mode="qfq",
    )
    contract["table_layout"] = "partitioned"
    try:
        jsonschema.validate(contract, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema should reject table_layout != single_table")


def test_build_data_contract_fails_when_duckdb_does_not_exist(tmp_path: Path):
    missing_path = tmp_path / "missing.duckdb"
    try:
        build_data_contract(
            storage_target=missing_path,
            raw_input_format="csv",
            provider_name="manual_csv",
            adjustment_mode="qfq",
        )
    except FileNotFoundError:
        return
    raise AssertionError("build_data_contract should fail when duckdb does not exist")
