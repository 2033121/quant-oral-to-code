from __future__ import annotations

from pathlib import Path

import duckdb

from build_data_contract import build_data_contract
from check_runtime_capabilities import check_runtime_capabilities
from resolve_repo_root import resolve_repo_root


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


def test_preflight_resolves_repo_root_and_duckdb_contract(tmp_path: Path):
    repo_root = resolve_repo_root(Path(__file__).resolve())
    assert (repo_root / "skills").exists()

    preflight = check_runtime_capabilities(repo_root)
    assert preflight["python_ok"] is True
    assert "duckdb" in preflight["required_python_packages"]
    assert preflight["resolved_capabilities"]["duckdb"]["hard_required"] is True

    db_path = _create_market_duckdb(tmp_path / "data" / "normalized" / "market.duckdb")
    contract = build_data_contract(
        storage_target=db_path,
        raw_input_format="csv",
        provider_name="manual_csv",
        adjustment_mode="qfq",
    )
    assert contract["storage_format"] == "duckdb"
    assert contract["bars_table_name"] == "bars"
    assert contract["primary_key"] == ["symbol", "trade_date"]


def test_resolve_repo_root_walks_up_from_deep_non_root_entry():
    repo_root = resolve_repo_root(Path(__file__).resolve())
    deep_entry = (
        repo_root
        / "skills"
        / "quant-oral-to-code"
        / "scripts"
        / "nested"
        / "deeper"
        / "entry.py"
    )
    assert resolve_repo_root(deep_entry) == repo_root
