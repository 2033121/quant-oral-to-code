from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

from generate_backtest_runner import generate_backtest_runner
from generate_strategy_code import generate_strategy_code
from resolve_codegen_mode import resolve_codegen_mode


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
            ('000001.SZ', '2024-01-03', 10.5, 11.2, 10.3, 11.0, 1200)
            """
        )
    finally:
        conn.close()


def test_experiment_protocol_contains_key_fields_and_runner_can_replay_it(tmp_path: Path) -> None:
    spec = {
        "strategy_name": "ma_demo",
        "strategy_family": "trend_basic",
        "market": "A股",
        "timeframe": "daily",
        "entry_rules": [{"kind": "moving_average_cross", "fast": 5, "slow": 20}],
        "experiment_protocol": {
            "sample_split": {
                "train": {"start": "2020-01-01", "end": "2022-12-31"},
                "test": {"start": "2023-01-01", "end": "2024-12-31"},
            }
        },
    }

    mode = resolve_codegen_mode(spec)
    generate_strategy_code(spec, mode, tmp_path)
    result = generate_backtest_runner(spec, tmp_path)
    protocol_file = Path(result["protocol_file"])
    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))

    assert protocol["data"]["bars_table_name"] == "bars"
    assert protocol["execution"]["mode"] == "next_open"
    assert set(["sample_split", "costs", "execution"]).issubset(protocol.keys())

    _seed_normalized_duckdb(tmp_path / "data" / "normalized" / "market.duckdb")

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    runner_path = tmp_path / "run_backtest.py"
    namespace: dict[str, object] = {"__file__": str(runner_path), "__name__": "generated_runner_test"}
    exec(compile(runner_path.read_text(encoding="utf-8"), str(runner_path), "exec"), namespace)

    load_protocol = namespace["load_protocol"]
    load_bars_dataframe = namespace["load_bars_dataframe"]
    main = namespace["main"]

    replay_protocol = load_protocol(protocol_file)
    bars_df = load_bars_dataframe(tmp_path / "data" / "normalized" / "market.duckdb", "bars")
    results = main()

    assert replay_protocol["data"]["bars_table_name"] == "bars"
    assert list(bars_df["symbol"]) == ["000001.SZ", "000001.SZ"]
    assert results["status"] == "ok"
    assert results["execution_mode"] == "next_open"
