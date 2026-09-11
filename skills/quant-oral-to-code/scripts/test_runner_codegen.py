from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import duckdb

from generate_backtest_runner import generate_backtest_runner
from generate_strategy_code import generate_strategy_code
from generate_strategy_tests import generate_strategy_tests
from resolve_codegen_mode import resolve_codegen_mode
from run_generated_strategy_smoke import run_generated_strategy_smoke


def _seed_normalized_duckdb(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
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
            ('000001.SZ', '2024-01-03', 10.5, 11.2, 10.3, 11.0, 1200),
            ('000001.SZ', '2024-01-04', 11.0, 11.6, 10.8, 11.4, 1250),
            ('000001.SZ', '2024-01-05', 11.4, 11.8, 11.0, 11.1, 1400),
            ('000001.SZ', '2024-01-08', 11.1, 12.0, 11.0, 11.9, 1500),
            ('000001.SZ', '2024-01-09', 11.9, 12.1, 11.4, 11.5, 1550),
            ('000001.SZ', '2024-01-10', 11.5, 12.4, 11.5, 12.2, 1600),
            ('000001.SZ', '2024-01-11', 12.2, 12.3, 11.7, 11.8, 1450),
            ('000001.SZ', '2024-01-12', 11.8, 12.7, 11.8, 12.5, 1700)
            """
        )
    finally:
        conn.close()


def test_backtest_runner_and_smoke_test_are_generated(tmp_path: Path) -> None:
    spec = {
        "strategy_name": "ma_demo",
        "experiment_protocol": {
            "sample_split": {
                "train": {"start": "2019-01-01", "end": "2022-12-31"},
            },
            "costs": {"commission_bps": 6},
            "execution": {"mode": "same_bar_close"},
        }
    }

    runner_result = generate_backtest_runner(spec, tmp_path)
    tests_result = generate_strategy_tests(spec, tmp_path)

    runner_file = Path(runner_result["runner_file"])
    protocol_file = Path(runner_result["protocol_file"])
    smoke_test_file = Path(tests_result["test_file"])
    kernel_file = tmp_path / "backtest_kernel.py"
    loader_file = tmp_path / "load_generated_strategy.py"

    assert runner_file.exists()
    assert protocol_file.exists()
    assert smoke_test_file.exists()
    assert kernel_file.exists()
    assert loader_file.exists()

    runner_text = runner_file.read_text(encoding="utf-8")
    assert "duckdb.connect(str(db_path), read_only=True)" in runner_text
    assert "data/normalized/market.duckdb" in runner_text
    assert "read_csv" not in runner_text
    assert "from backtest_kernel import run_backtest" in runner_text
    assert "from load_generated_strategy import load_generated_strategy" in runner_text

    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    assert protocol["data"]["bars_table_name"] == "bars"
    assert protocol["data"]["storage_path"] == "data/normalized/market.duckdb"
    assert protocol["execution"]["mode"] == "next_open"
    assert "sample_split" in protocol
    assert "costs" in protocol

    smoke_test_text = smoke_test_file.read_text(encoding="utf-8")
    assert "experiment_protocol.json" in smoke_test_text
    assert "next_open" in smoke_test_text


def test_generated_workspace_runner_is_self_contained_without_skill_script_injection(
    tmp_path: Path,
) -> None:
    spec = {
        "strategy_name": "ma_demo",
        "strategy_family": "trend_basic",
        "market": "A股",
        "timeframe": "daily",
        "entry_rules": [{"kind": "moving_average_cross", "fast": 5, "slow": 20}],
        "exit_rules": [{"kind": "price_below_ma", "ma": 10}],
    }

    mode = resolve_codegen_mode(spec)
    generate_strategy_code(spec, mode, tmp_path)
    generate_backtest_runner(spec, tmp_path)
    _seed_normalized_duckdb(tmp_path / "data" / "normalized" / "market.duckdb")

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, str(tmp_path / "run_backtest.py")],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = run_generated_strategy_smoke(tmp_path)

    assert result["status"] == "ok"
    assert result["execution_mode"] == "next_open"
    assert result["bars_table_name"] == "bars"
    assert result["total_rows"] == 9
    assert result["summary"]["metrics_availability"] == "available"
    assert "equity_curve" in result
    assert (tmp_path / "results" / "equity_curve.json").exists()
    assert (tmp_path / "results" / "trades.json").exists()
