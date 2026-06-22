# dsl

`dsl` 负责把口述策略翻译成结构化规格，方便后续护栏审查和代码生成。

## 目标

- 保留用户原意。
- 把模糊语言压缩成字段化约束。
- 为每个关键字段保留来源说明，方便后续追溯。

## 最小 DSL 字段

- `strategy_name`
- `universe`
- `signal_family`
- `entry_rules`
- `exit_rules`
- `risk_rules`
- `data_requirements`
- `outputs_requested`
- `claim_level_target`

## 翻译原则

- 能明确写字段就写字段，不能明确就标记 `unknown` 或 `needs_clarification`。
- 不凭空补交易规则。
- 中文术语可以保留，但字段名保持稳定，便于脚本消费。
- claim level 的基础枚举先固定为 `demo_only`、`portable_backtest`、`research_grade_local`。
- 如果数据要求无法满足，DSL 结果要允许后续进入 cutoff / `DATA_REQUIRED`，而不是强行补成“可正式回测”。

## 结果要求

最小阶段可以只产出一个轻量 `strategy_spec` 概念对象，供后续脚本落盘为 JSON；其中数据归一化目标口径固定为 DuckDB。
