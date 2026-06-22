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
            {"symbol": "000001.SZ", "trade_date": "2024-01-01", "open": 9.9, "high": 10.1, "low": 9.8, "close": 10.0, "volume": 1000},
            {"symbol": "000001.SZ", "trade_date": "2024-01-02", "open": 10.1, "high": 10.3, "low": 10.0, "close": 10.2, "volume": 1050},
            {"symbol": "000001.SZ", "trade_date": "2024-01-03", "open": 10.2, "high": 10.5, "low": 10.1, "close": 10.4, "volume": 1100},
            {"symbol": "000001.SZ", "trade_date": "2024-01-04", "open": 10.0, "high": 10.2, "low": 9.9, "close": 10.1, "volume": 1150},
            {"symbol": "000001.SZ", "trade_date": "2024-01-05", "open": 10.3, "high": 10.8, "low": 10.2, "close": 10.7, "volume": 1200},
            {"symbol": "000001.SZ", "trade_date": "2024-01-08", "open": 10.8, "high": 11.1, "low": 10.7, "close": 11.0, "volume": 1250},
            {"symbol": "000001.SZ", "trade_date": "2024-01-09", "open": 11.0, "high": 11.5, "low": 10.9, "close": 11.4, "volume": 1300},
            {"symbol": "000001.SZ", "trade_date": "2024-01-10", "open": 11.5, "high": 11.9, "low": 11.4, "close": 11.8, "volume": 1350},
            {"symbol": "000001.SZ", "trade_date": "2024-01-11", "open": 11.6, "high": 11.7, "low": 11.3, "close": 11.6, "volume": 1280},
            {"symbol": "000001.SZ", "trade_date": "2024-01-12", "open": 11.8, "high": 12.2, "low": 11.7, "close": 12.1, "volume": 1380},
            {"symbol": "000001.SZ", "trade_date": "2024-01-15", "open": 12.2, "high": 12.7, "low": 12.1, "close": 12.6, "volume": 1450},
            {"symbol": "000001.SZ", "trade_date": "2024-01-16", "open": 12.6, "high": 13.1, "low": 12.5, "close": 13.0, "volume": 1500},
            {"symbol": "000001.SZ", "trade_date": "2024-01-17", "open": 13.0, "high": 13.5, "low": 12.9, "close": 13.4, "volume": 1550},
            {"symbol": "000001.SZ", "trade_date": "2024-01-18", "open": 13.3, "high": 13.8, "low": 13.2, "close": 13.7, "volume": 1600},
            {"symbol": "000001.SZ", "trade_date": "2024-01-19", "open": 13.8, "high": 14.2, "low": 13.7, "close": 14.1, "volume": 1650},
            {"symbol": "000001.SZ", "trade_date": "2024-01-22", "open": 14.2, "high": 14.7, "low": 14.1, "close": 14.6, "volume": 1700},
            {"symbol": "000001.SZ", "trade_date": "2024-01-23", "open": 14.6, "high": 15.1, "low": 14.5, "close": 15.0, "volume": 1750},
            {"symbol": "000001.SZ", "trade_date": "2024-01-24", "open": 15.0, "high": 15.5, "low": 14.9, "close": 15.4, "volume": 1800},
            {"symbol": "000001.SZ", "trade_date": "2024-01-25", "open": 15.4, "high": 15.9, "low": 15.3, "close": 15.8, "volume": 1850},
            {"symbol": "000001.SZ", "trade_date": "2024-01-26", "open": 15.8, "high": 16.4, "low": 15.7, "close": 16.3, "volume": 1900},
            {"symbol": "000001.SZ", "trade_date": "2024-01-29", "open": 16.3, "high": 16.8, "low": 16.2, "close": 16.7, "volume": 1950}
        ]
    )

    assert isinstance(signals, list)
    assert signals[-1]["fast_ma"] is not None
    assert strategy.decide(signals, current_position=0) in {"buy", "hold", "sell"}


def test_strategy_codegen_preserves_abstract_a_share_filters_in_description(tmp_path: Path):
    spec = {
        "strategy_name": "abstract_demo",
        "strategy_family": "mean_reversion_basic",
        "market": "A股",
        "timeframe": "daily",
        "selection_filters": [
            {"kind": "group_relative_strength", "lookback": 5, "min_excess_return": 0.02},
            {"kind": "rank_improvement_proxy", "lookback": 10},
            {"kind": "liquidity_quantile_filter", "metric": "turnover_or_amount", "quantile": 0.85},
        ],
    }
    mode = resolve_codegen_mode(spec)
    result = generate_strategy_code(spec, mode, tmp_path)
    strategy = load_generated_strategy(Path(result["strategy_file"]))()
    description = strategy.describe()

    assert description["use_group_relative_strength_filter"] is True
    assert description["group_relative_strength_lookback"] == 5
    assert description["use_rank_improvement_filter"] is True
    assert description["rank_improvement_lookback"] == 10
    assert description["use_liquidity_quantile_filter"] is True
