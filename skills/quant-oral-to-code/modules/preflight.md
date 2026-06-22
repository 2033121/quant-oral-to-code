# preflight

## 目标

在任何数据接入、代码生成或回测执行前，先完成权威预检，固定仓库根路径解析方式，并生成结构化 `preflight_report`。

## 强制规则

- 只能通过 `resolve_repo_root()` 自底向上查找仓库哨兵目录来解析仓库根路径。
- 禁止写死 `parents[3]`、`../../..` 一类层级假设。
- `check_runtime_capabilities()` 必须把 `duckdb` 视为硬依赖。
- 预检结果必须结构化输出，可直接写入 `preflight_report.json`。

## 唯一执行栈入口约束

- 输入数据可以来自 `csv | parquet | json | sqlite | duckdb | provider api`。
- 标准化后的唯一持久化目标固定为 `generated_strategies/<slug>/data/normalized/market.duckdb`。
- 后续 `run_backtest.py` 只能消费 DuckDB 契约，不再反向依赖外部私有执行引擎。

## preflight_report 最低要求

- `repo_root`
- `python_ok`
- `overall_ready`
- `required_python_packages`
- `resolved_capabilities`
- `missing_dependencies`
- `notes`

## 失败口径

- 若仓库根路径无法解析：立即阻断。
- 若 `duckdb` 缺失：立即阻断，不允许伪装成可运行状态。
- 若 Python 运行时存在但能力不完整：输出结构化原因，交给后续 onboarding 文案解释。
