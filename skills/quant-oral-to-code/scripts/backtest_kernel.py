from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass(slots=True)
class BacktestSnapshot:
    symbol: str
    row_count: int
    action_count: int
    trade_count: int
    winning_trade_count: int
    ending_equity: float


def _records_from_dataframe(bars_df: Any) -> list[dict[str, object]]:
    if hasattr(bars_df, "to_dict"):
        records = bars_df.to_dict(orient="records")
        if isinstance(records, list):
            return [dict(item) for item in records]
    raise TypeError("bars_df must provide to_dict(orient='records')")


def _split_records_by_symbol(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in records:
        symbol = str(row["symbol"])
        grouped.setdefault(symbol, []).append(row)
    return grouped


def _to_float(value: object) -> float:
    return float(value)


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _annualized_return(total_return: float, periods: int, annual_periods: int = 252) -> float | None:
    if periods <= 0 or total_return <= -1.0:
        return None
    total_multiplier = 1.0 + total_return
    return total_multiplier ** (annual_periods / float(periods)) - 1.0


def _standard_deviation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / float(len(values))
    variance = sum((value - mean) ** 2 for value in values) / float(len(values) - 1)
    return math.sqrt(variance)


def _sharpe_ratio(values: list[float], annual_periods: int = 252) -> float | None:
    std = _standard_deviation(values)
    if std is None or std == 0:
        return None
    mean = sum(values) / float(len(values))
    return (mean / std) * math.sqrt(float(annual_periods))


def _sortino_ratio(values: list[float], annual_periods: int = 252) -> float | None:
    downside = [value for value in values if value < 0]
    if not downside:
        return None
    downside_std = _standard_deviation(downside)
    if downside_std is None or downside_std == 0:
        return None
    mean = sum(values) / float(len(values))
    return (mean / downside_std) * math.sqrt(float(annual_periods))


def _max_drawdown(equity_curve: list[float]) -> float | None:
    if not equity_curve:
        return None
    peak = equity_curve[0]
    worst_drawdown = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak <= 0:
            continue
        drawdown = (value / peak) - 1.0
        if drawdown < worst_drawdown:
            worst_drawdown = drawdown
    return worst_drawdown


def _round_metric(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, 6)


def _extract_lookbacks(strategy: Any) -> set[int]:
    description = strategy.describe() if hasattr(strategy, "describe") else {}
    if not isinstance(description, dict):
        return set()
    lookbacks: set[int] = set()
    if description.get("use_group_relative_strength_filter"):
        lookback = description.get("group_relative_strength_lookback")
        if isinstance(lookback, int) and lookback > 0:
            lookbacks.add(lookback)
    if description.get("use_rank_improvement_filter"):
        lookback = description.get("rank_improvement_lookback")
        if isinstance(lookback, int) and lookback > 0:
            lookbacks.add(lookback)
    return lookbacks


def _compute_rolling_returns(grouped: dict[str, list[dict[str, object]]], lookbacks: set[int]) -> None:
    if not lookbacks:
        return
    for rows in grouped.values():
        closes = [_to_float(row["close"]) for row in rows]
        for index, row in enumerate(rows):
            for lookback in lookbacks:
                key = f"__rolling_return_{lookback}"
                if index < lookback:
                    row[key] = None
                    continue
                previous_close = closes[index - lookback]
                ratio = _safe_div(closes[index], previous_close)
                row[key] = None if ratio is None else ratio - 1.0


def _enrich_cross_sectional_context(grouped: dict[str, list[dict[str, object]]], lookbacks: set[int]) -> None:
    if not lookbacks:
        return

    _compute_rolling_returns(grouped, lookbacks)

    rows_by_date: dict[str, list[dict[str, object]]] = {}
    for rows in grouped.values():
        for row in rows:
            trade_date = str(row["trade_date"])
            rows_by_date.setdefault(trade_date, []).append(row)

    for trade_date_rows in rows_by_date.values():
        for lookback in lookbacks:
            key = f"__rolling_return_{lookback}"
            valid_returns = [
                _to_float(row[key])
                for row in trade_date_rows
                if isinstance(row.get(key), (int, float))
            ]
            if not valid_returns:
                continue
            mean_return = sum(valid_returns) / float(len(valid_returns))
            sorted_returns = sorted(valid_returns)
            count = len(sorted_returns)
            for row in trade_date_rows:
                row_value = row.get(key)
                if not isinstance(row_value, (int, float)):
                    row[f"__cross_sectional_excess_return_{lookback}"] = None
                    row[f"__cross_sectional_rank_pct_{lookback}"] = None
                    continue
                row_float = _to_float(row_value)
                rank_position = sum(1 for value in sorted_returns if value <= row_float)
                rank_pct = _safe_div(float(rank_position), float(count))
                row[f"__cross_sectional_excess_return_{lookback}"] = row_float - mean_return
                row[f"__cross_sectional_rank_pct_{lookback}"] = rank_pct

    for rows in grouped.values():
        previous_rank_by_lookback: dict[int, float] = {}
        for row in rows:
            for lookback in lookbacks:
                rank_key = f"__cross_sectional_rank_pct_{lookback}"
                delta_key = f"__cross_sectional_rank_delta_{lookback}"
                rank_value = row.get(rank_key)
                if not isinstance(rank_value, (int, float)):
                    row[delta_key] = None
                    continue
                previous_rank = previous_rank_by_lookback.get(lookback)
                rank_float = _to_float(rank_value)
                row[delta_key] = None if previous_rank is None else rank_float - previous_rank
                previous_rank_by_lookback[lookback] = rank_float


def _simulate_symbol(
    strategy: Any,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    signals = strategy.generate_signals(rows)
    symbol = str(rows[0]["symbol"]) if rows else "UNKNOWN"
    position = 0
    pending_action: str | None = None
    last_close: float | None = None
    entry_price: float | None = None
    entry_date: str | None = None
    equity = 1.0
    action_counts = {"buy": 0, "sell": 0, "hold": 0}
    action_count = 0
    trade_count = 0
    winning_trade_count = 0
    daily_records: list[dict[str, object]] = []
    trades: list[dict[str, object]] = []

    for index, row in enumerate(rows):
        trade_date = str(row["trade_date"])
        open_price = _to_float(row["open"])
        close_price = _to_float(row["close"])
        day_return = 0.0

        if position > 0 and last_close is not None:
            overnight_ratio = _safe_div(open_price, last_close)
            if pending_action == "sell":
                if overnight_ratio is not None:
                    day_return = overnight_ratio - 1.0
                    equity *= 1.0 + day_return
                if entry_price is not None:
                    trade_return_ratio = _safe_div(open_price, entry_price)
                    trade_return = None if trade_return_ratio is None else trade_return_ratio - 1.0
                    trade_count += 1
                    if isinstance(trade_return, float) and trade_return > 0:
                        winning_trade_count += 1
                    trades.append(
                        {
                            "symbol": symbol,
                            "entry_date": entry_date,
                            "exit_date": trade_date,
                            "entry_price": entry_price,
                            "exit_price": open_price,
                            "return": _round_metric(trade_return),
                        }
                    )
                position = 0
                pending_action = None
                entry_price = None
                entry_date = None
            else:
                if last_close != 0:
                    day_return = (close_price / last_close) - 1.0
                    equity *= 1.0 + day_return
        elif position == 0 and pending_action == "buy":
            intraday_ratio = _safe_div(close_price, open_price)
            if intraday_ratio is not None:
                day_return = intraday_ratio - 1.0
                equity *= 1.0 + day_return
            position = 1
            pending_action = None
            entry_price = open_price
            entry_date = trade_date

        daily_records.append(
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "equity": _round_metric(equity),
                "daily_return": _round_metric(day_return),
                "position": position,
            }
        )

        action = str(strategy.decide([signals[index]], current_position=position))
        if action not in action_counts:
            action = "hold"
        action_counts[action] += 1
        action_count += 1

        if action == "buy" and position <= 0:
            pending_action = "buy"
        elif action == "sell" and position > 0:
            pending_action = "sell"

        last_close = close_price

    if position > 0 and last_close is not None and entry_price is not None:
        trade_return_ratio = _safe_div(last_close, entry_price)
        trade_return = None if trade_return_ratio is None else trade_return_ratio - 1.0
        trade_count += 1
        if isinstance(trade_return, float) and trade_return > 0:
            winning_trade_count += 1
        trades.append(
            {
                "symbol": symbol,
                "entry_date": entry_date,
                "exit_date": str(rows[-1]["trade_date"]),
                "entry_price": entry_price,
                "exit_price": last_close,
                "return": _round_metric(trade_return),
                "forced_exit": True,
            }
        )

    snapshot = BacktestSnapshot(
        symbol=symbol,
        row_count=len(rows),
        action_count=action_count,
        trade_count=trade_count,
        winning_trade_count=winning_trade_count,
        ending_equity=equity,
    )
    return {
        "snapshot": snapshot,
        "action_counts": action_counts,
        "daily_records": daily_records,
        "trades": trades,
    }


def _merge_action_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value)


def _build_portfolio_curve(symbol_runs: list[dict[str, object]]) -> list[dict[str, object]]:
    if not symbol_runs:
        return []

    symbol_dates: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()
    for run in symbol_runs:
        daily_records = run["daily_records"]
        if not isinstance(daily_records, list):
            continue
        if not daily_records:
            continue
        symbol = str(daily_records[0]["symbol"])
        symbol_dates[symbol] = {}
        for record in daily_records:
            trade_date = str(record["trade_date"])
            all_dates.add(trade_date)
            symbol_dates[symbol][trade_date] = _to_float(record["equity"])

    ordered_dates = sorted(all_dates)
    symbols = sorted(symbol_dates)
    if not ordered_dates or not symbols:
        return []

    latest_equity = {symbol: 1.0 for symbol in symbols}
    curve: list[dict[str, object]] = []
    previous_portfolio_equity: float | None = None

    for trade_date in ordered_dates:
        for symbol in symbols:
            current_value = symbol_dates[symbol].get(trade_date)
            if isinstance(current_value, (int, float)):
                latest_equity[symbol] = _to_float(current_value)
        portfolio_equity = sum(latest_equity.values()) / float(len(symbols))
        portfolio_daily_return = 0.0
        if previous_portfolio_equity not in (None, 0):
            portfolio_daily_return = (portfolio_equity / previous_portfolio_equity) - 1.0
        curve.append(
            {
                "trade_date": trade_date,
                "equity": _round_metric(portfolio_equity),
                "daily_return": _round_metric(portfolio_daily_return),
            }
        )
        previous_portfolio_equity = portfolio_equity

    return curve


def _build_summary(portfolio_curve: list[dict[str, object]], symbol_summaries: list[dict[str, object]]) -> dict[str, object]:
    if not portfolio_curve:
        return {
            "metrics_availability": "unavailable",
            "metrics_unavailable_reason": "portfolio_equity_curve_empty",
            "total_return": None,
            "annualized_return": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "trade_count": 0,
            "win_rate": None,
        }

    equity_values = [_to_float(item["equity"]) for item in portfolio_curve]
    daily_returns = [
        _to_float(item["daily_return"])
        for item in portfolio_curve[1:]
        if isinstance(item.get("daily_return"), (int, float))
    ]
    total_return = equity_values[-1] - 1.0
    trade_count = sum(int(item.get("trade_count", 0) or 0) for item in symbol_summaries)
    winning_trade_count = sum(
        int(item.get("winning_trade_count", 0) or 0) for item in symbol_summaries
    )

    return {
        "metrics_availability": "available",
        "metrics_unavailable_reason": None,
        "total_return": _round_metric(total_return),
        "annualized_return": _round_metric(_annualized_return(total_return, len(portfolio_curve))),
        "max_drawdown": _round_metric(_max_drawdown(equity_values)),
        "sharpe_ratio": _round_metric(_sharpe_ratio(daily_returns)),
        "sortino_ratio": _round_metric(_sortino_ratio(daily_returns)),
        "trade_count": trade_count,
        "win_rate": _round_metric(
            None if trade_count <= 0 else winning_trade_count / float(trade_count)
        ),
    }


def run_backtest(strategy: Any, bars_df: Any, protocol: dict[str, object]) -> dict[str, object]:
    records = _records_from_dataframe(bars_df)
    grouped = _split_records_by_symbol(records)
    _enrich_cross_sectional_context(grouped, _extract_lookbacks(strategy))

    symbol_summaries: list[dict[str, object]] = []
    action_counts = {"buy": 0, "sell": 0, "hold": 0}
    total_rows = 0
    symbol_runs: list[dict[str, object]] = []
    all_trades: list[dict[str, object]] = []

    for symbol, rows in grouped.items():
        symbol_run = _simulate_symbol(strategy, rows)
        symbol_runs.append(symbol_run)
        _merge_action_counts(action_counts, symbol_run["action_counts"])
        trades = symbol_run["trades"]
        if isinstance(trades, list):
            all_trades.extend(trades)
        total_rows += len(rows)
        snapshot = symbol_run["snapshot"]
        symbol_summaries.append(
            {
                "symbol": snapshot.symbol,
                "row_count": snapshot.row_count,
                "action_count": snapshot.action_count,
                "trade_count": snapshot.trade_count,
                "winning_trade_count": snapshot.winning_trade_count,
                "ending_equity": _round_metric(snapshot.ending_equity),
            }
        )

    portfolio_curve = _build_portfolio_curve(symbol_runs)
    summary = _build_summary(portfolio_curve, symbol_summaries)

    return {
        "status": "ok",
        "execution_mode": protocol.get("execution", {}).get("mode"),
        "bars_table_name": protocol.get("data", {}).get("bars_table_name"),
        "total_rows": total_rows,
        "symbol_count": len(grouped),
        "action_counts": action_counts,
        "symbol_summaries": symbol_summaries,
        "summary": summary,
        "equity_curve": portfolio_curve,
        "trades": all_trades,
    }
