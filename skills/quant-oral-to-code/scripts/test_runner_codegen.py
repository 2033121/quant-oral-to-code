from __future__ import annotations

import json
from pathlib import Path

from generate_backtest_runner import generate_backtest_runner
from generate_strategy_tests import generate_strategy_tests


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

    assert runner_file.exists()
    assert protocol_file.exists()
    assert smoke_test_file.exists()

    runner_text = runner_file.read_text(encoding="utf-8")
    assert "duckdb.connect(str(db_path), read_only=True)" in runner_text
    assert "data/normalized/market.duckdb" in runner_text
    assert "read_csv" not in runner_text

    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    assert protocol["data"]["bars_table_name"] == "bars"
    assert protocol["data"]["storage_path"] == "data/normalized/market.duckdb"
    assert protocol["execution"]["mode"] == "next_open"
    assert "sample_split" in protocol
    assert "costs" in protocol

    smoke_test_text = smoke_test_file.read_text(encoding="utf-8")
    assert "experiment_protocol.json" in smoke_test_text
    assert "next_open" in smoke_test_text
