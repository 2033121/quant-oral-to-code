from __future__ import annotations

from pathlib import Path

import duckdb

from build_data_contract import build_data_contract
from build_claim_report import build_claim_report


def _create_market_duckdb(
    db_path: Path,
    columns_sql: str = "symbol varchar, trade_date date, open double, high double, low double, close double, volume double",
) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(f"create table bars ({columns_sql})")
        if "volume" in columns_sql:
            con.execute(
                """
                insert into bars values
                ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5, 1000)
                """
            )
        else:
            con.execute(
                """
                insert into bars values
                ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5)
                """
            )
    finally:
        con.close()
    return db_path


def _create_invalid_market_duckdb(db_path: Path, inserts_sql: str) -> Path:
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
        con.execute(inserts_sql)
    finally:
        con.close()
    return db_path


def _build_complete_contract(db_path: Path) -> dict[str, object]:
    return build_data_contract(
        storage_target=db_path,
        raw_input_format="csv",
        provider_name="manual_csv",
        adjustment_mode="qfq",
        write_disposition="overwrite",
    )


def _build_manual_contract(storage_target: Path) -> dict[str, object]:
    return {
        "storage_format": "duckdb",
        "storage_target": str(storage_target),
        "bars_table_name": "bars",
        "table_layout": "single_table",
        "primary_key": ["symbol", "trade_date"],
        "required_tables": ["bars"],
        "required_columns": [
            "symbol",
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
        "write_disposition": "overwrite",
        "raw_input_format": "csv",
        "provider_name": "manual_csv",
        "adjustment_mode": "qfq",
        "data_hash": "forged",
    }


def test_claim_gate_distinguishes_cutoff_and_full_workspace(tmp_path: Path):
    blocked = build_claim_report(
        review={"blocking": ["low_translation_confidence"], "warnings": []},
        data_profile={"mode": "demo_mode", "data_readiness": "demo_only"},
        data_contract=None,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"

    db_path = _create_market_duckdb(tmp_path / "portable_case.duckdb")
    runnable = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=_build_complete_contract(db_path),
    )
    assert runnable["artifact_policy"] == "full_workspace"
    assert runnable["claim_level"] == "portable_backtest"


def test_claim_gate_maps_research_grade_local_when_full_research_ready(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "research_case.duckdb")
    runnable = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "full_research_mode", "data_readiness": "ready"},
        data_contract=_build_complete_contract(db_path),
    )
    assert runnable["artifact_policy"] == "full_workspace"
    assert runnable["claim_level"] == "research_grade_local"


def test_claim_gate_rejects_ready_data_when_contract_is_not_duckdb():
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract={
            **_build_manual_contract(Path("D:/tool/novel/nonexistent.parquet")),
            "storage_format": "parquet",
        },
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_contract_fields_are_incomplete():
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract={"storage_format": "duckdb", "storage_target": "D:/tool/novel/nonexistent.duckdb"},
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_duckdb_file_does_not_exist():
    missing_path = Path("Z:/definitely-missing/claim-gate/missing.duckdb")
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=_build_manual_contract(missing_path),
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_bars_table_is_missing(tmp_path: Path):
    db_path = tmp_path / "missing_table.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute("create table prices(symbol varchar)")
    finally:
        con.close()

    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=_build_complete_contract(db_path),
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_bars_columns_are_incomplete(tmp_path: Path):
    db_path = _create_market_duckdb(
        tmp_path / "missing_column.duckdb",
        columns_sql="symbol varchar, trade_date date, open double, high double, low double, close double",
    )
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=_build_complete_contract(db_path),
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_required_tables_are_incomplete(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "missing_required_tables.duckdb")
    contract = _build_complete_contract(db_path)
    contract["required_tables"] = []
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=contract,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_required_columns_are_incomplete(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "missing_required_columns.duckdb")
    contract = _build_complete_contract(db_path)
    contract["required_columns"] = ["symbol", "trade_date", "open", "high", "low", "close"]
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=contract,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_contract_metadata_is_missing(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "missing_provider_name.duckdb")
    contract = _build_complete_contract(db_path)
    del contract["provider_name"]
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=contract,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_raw_input_format_is_invalid(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "invalid_raw_format.duckdb")
    contract = _build_complete_contract(db_path)
    contract["raw_input_format"] = "totally_fake_format"
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=contract,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_data_hash_is_forged(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "forged_hash.duckdb")
    contract = _build_complete_contract(db_path)
    contract["data_hash"] = "forged"
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=contract,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_ready_data_when_db_content_changes_after_contract_build(tmp_path: Path):
    db_path = _create_market_duckdb(tmp_path / "changed_after_contract.duckdb")
    contract = _build_complete_contract(db_path)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            insert into bars values
            ('000002.SZ', '2024-01-03', 20, 21, 19, 20.5, 2000)
            """
        )
    finally:
        con.close()
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=contract,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"


def test_claim_gate_rejects_duplicate_symbol_trade_date_duckdb(tmp_path: Path):
    db_path = _create_invalid_market_duckdb(
        tmp_path / "duplicate_keys.duckdb",
        """
        insert into bars values
        ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5, 1000),
        ('000001.SZ', '2024-01-02', 10.1, 11.1, 9.1, 10.6, 1100)
        """,
    )
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=_build_complete_contract(db_path),
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["decision"] == "cutoff"
    assert "duplicate_symbol_trade_date_keys:1" in blocked["reasons"]


def test_claim_gate_rejects_non_finite_numeric_duckdb(tmp_path: Path):
    db_path = _create_invalid_market_duckdb(
        tmp_path / "non_finite.duckdb",
        """
        insert into bars values
        ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5, 1000),
        ('000001.SZ', '2024-01-03', 'NaN'::double, 11, 9, 10.5, 1000),
        ('000001.SZ', '2024-01-04', 10, 'inf'::double, 9, 10.5, 1000)
        """,
    )
    blocked = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=_build_complete_contract(db_path),
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["decision"] == "cutoff"
    assert "numeric_column_has_non_finite_values:open:1" in blocked["reasons"]
    assert "numeric_column_has_non_finite_values:high:1" in blocked["reasons"]
