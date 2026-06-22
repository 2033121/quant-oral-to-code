from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class BacktestSnapshot:
    symbol: str
    row_count: int
    action_count: int


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


def run_backtest(strategy: Any, bars_df: Any, protocol: dict[str, object]) -> dict[str, object]:
    records = _records_from_dataframe(bars_df)
    grouped = _split_records_by_symbol(records)

    symbol_summaries: list[dict[str, object]] = []
    action_counts = {"buy": 0, "sell": 0, "hold": 0}
    total_rows = 0

    for symbol, rows in grouped.items():
        signals = strategy.generate_signals(rows)
        position = 0
        actions_for_symbol = 0
        for signal in signals:
            action = str(strategy.decide([signal], current_position=position))
            if action not in action_counts:
                action = "hold"
            action_counts[action] += 1
            if action == "buy":
                position = 1
            elif action == "sell":
                position = 0
            actions_for_symbol += 1
        total_rows += len(rows)
        snapshot = BacktestSnapshot(
            symbol=symbol,
            row_count=len(rows),
            action_count=actions_for_symbol,
        )
        symbol_summaries.append(
            {
                "symbol": snapshot.symbol,
                "row_count": snapshot.row_count,
                "action_count": snapshot.action_count,
            }
        )

    return {
        "status": "ok",
        "execution_mode": protocol.get("execution", {}).get("mode"),
        "bars_table_name": protocol.get("data", {}).get("bars_table_name"),
        "total_rows": total_rows,
        "symbol_count": len(grouped),
        "action_counts": action_counts,
        "symbol_summaries": symbol_summaries,
    }
