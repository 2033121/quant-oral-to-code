from pathlib import Path

from generate_strategy_code import generate_strategy_code
from load_generated_strategy import load_generated_strategy
from resolve_codegen_mode import resolve_codegen_mode


def test_strategy_codegen_emits_self_contained_generated_strategy(tmp_path: Path):
    spec = {
        "strategy_name": "ma_demo",
        "strategy_family": "trend_basic",
        "market": "A股",
        "timeframe": "daily",
        "entry_rules": [{"kind": "moving_average_cross", "fast": 5, "slow": 20}],
        "exit_rules": [{"kind": "price_below_ma", "ma": 10}],
    }
    mode = resolve_codegen_mode(spec)

    assert mode["mode"] == "standalone_generated"

    result = generate_strategy_code(spec, mode, tmp_path)
    strategy_file = Path(result["strategy_file"])

    assert strategy_file.exists()
    text = strategy_file.read_text(encoding="utf-8")
    assert "class GeneratedStrategy" in text
    assert "engine.strategy_base" not in text

    strategy_class = load_generated_strategy(strategy_file)
    strategy = strategy_class()
    signals = strategy.generate_signals(
        [
            {"trade_date": "2024-01-01", "close": 10.0},
            {"trade_date": "2024-01-02", "close": 10.2},
            {"trade_date": "2024-01-03", "close": 10.4},
            {"trade_date": "2024-01-04", "close": 10.1},
            {"trade_date": "2024-01-05", "close": 10.7},
            {"trade_date": "2024-01-08", "close": 11.0},
            {"trade_date": "2024-01-09", "close": 11.4},
            {"trade_date": "2024-01-10", "close": 11.8},
            {"trade_date": "2024-01-11", "close": 11.6},
            {"trade_date": "2024-01-12", "close": 12.1},
            {"trade_date": "2024-01-15", "close": 12.6},
            {"trade_date": "2024-01-16", "close": 13.0},
            {"trade_date": "2024-01-17", "close": 13.4},
            {"trade_date": "2024-01-18", "close": 13.7},
            {"trade_date": "2024-01-19", "close": 14.1},
            {"trade_date": "2024-01-22", "close": 14.6},
            {"trade_date": "2024-01-23", "close": 15.0},
            {"trade_date": "2024-01-24", "close": 15.4},
            {"trade_date": "2024-01-25", "close": 15.8},
            {"trade_date": "2024-01-26", "close": 16.3},
            {"trade_date": "2024-01-29", "close": 16.7}
        ]
    )

    assert isinstance(signals, list)
    assert signals[-1]["fast_ma"] is not None
    assert strategy.decide(signals, current_position=0) in {"buy", "hold", "sell"}
