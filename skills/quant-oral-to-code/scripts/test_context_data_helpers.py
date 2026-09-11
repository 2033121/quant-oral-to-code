from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from context_data_helpers import persist_real_data_artifacts


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
            ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5, 1000),
            ('000002.SZ', '2024-01-02', 20, 21, 19, 20.5, 2000)
            """
        )
    finally:
        con.close()
    return db_path


def test_persist_real_data_artifacts_writes_context_tables_and_contract(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "market.duckdb")
    report_path = tmp_path / "context_fetch_report.json"
    contract_path = tmp_path / "data_contract.json"

    result = persist_real_data_artifacts(
        storage_target=db_path,
        raw_input_format="csv",
        provider_name="tushare",
        adjustment_mode="qfq",
        context_payload={
            "security_master": pd.DataFrame(
                [{"symbol": "000001.SZ", "security_name": "平安银行", "list_status": "L"}]
            ),
            "st_status": pd.DataFrame(
                [{"symbol": "000001.SZ", "trade_date": "2024-01-02", "is_st": False}]
            ),
            "suspension_status": pd.DataFrame(
                [{"symbol": "000001.SZ", "trade_date": "2024-01-02", "is_suspended": False}]
            ),
            "group_membership": pd.DataFrame(
                [{"symbol": "000001.SZ", "group_type": "industry", "group_code": "bank"}]
            ),
            "benchmark_series": pd.DataFrame(
                [{"benchmark_code": "000300.SH", "trade_date": "2024-01-02", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
            ),
        },
        provider_support={
            "security_master": True,
            "st_status": True,
            "suspension_status": True,
            "group_membership": True,
            "benchmark_series": True,
        },
        selection_method="multi_symbol_api",
        contract_output_path=contract_path,
        context_report_output_path=report_path,
        benchmark_code="000300.SH",
        universe_name="fixture_universe",
    )

    assert contract_path.exists()
    assert report_path.exists()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert contract["context_tables"]["security_master"]["available"] is True
    assert contract["sample_coverage"]["selection_method"] == "multi_symbol_api"
    assert report["context_tables"]["benchmark_series"]["benchmark_code"] == "000300.SH"
    assert result["context_tables"]["group_membership"]["row_count"] == 1
