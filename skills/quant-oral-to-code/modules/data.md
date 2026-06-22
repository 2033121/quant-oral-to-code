# data

## 目标

固化唯一标准数据契约，禁止在权威链路中漂移回 CSV/JSON/Parquet/SQLite 直跑模式。

## 唯一标准

- `storage_format` 固定为 `duckdb`
- `bars_table_name` 固定为 `bars`
- `primary_key` 固定为 `["symbol", "trade_date"]`
- `required_tables` 至少包含 `bars`
- `required_columns` 至少包含
  - `symbol`
  - `trade_date`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`

## data_contract 必备字段

- `storage_format`
- `storage_target`
- `bars_table_name`
- `table_layout`
- `primary_key`
- `required_tables`
- `required_columns`
- `write_disposition`
- `raw_input_format`
- `provider_name`
- `adjustment_mode`
- `data_hash`

## Claim Gate 约束

- 只有当数据满足 DuckDB 核心契约、且 guardrail 未阻断时，才允许进入 `artifact_policy == full_workspace`。
- 若仍缺少真实可运行数据，或契约未闭合，必须进入 `artifact_policy == data_required_cutoff`。
- `claim_level` 只允许三档：
  - `demo_only`
  - `portable_backtest`
  - `research_grade_local`

## 兼容说明

- `csv/json/parquet/sqlite/duckdb` 可以作为原始输入格式。
- 这些格式只允许作为导入源或交换格式，不能替代标准回测持久化格式。
