# onboarding

## 目标

把结构化 claim/report 翻译成新手能直接执行的说明，明确当前可信度、缺什么、下一步做什么。

## 输入

- `claim_report.json`
- 可选 `data_contract.json`
- 可选 `preflight_report.json`

## 输出

- `README_beginner.md`

## 必须解释的内容

- 当前 `claim_level`
- 当前 `artifact_policy`
- 当前产物是否允许生成完整工作区
- 环境是否已满足 `duckdb` 硬依赖
- 数据是否已经落成 DuckDB 标准契约
- 下一步如何从 `demo_only` 升级到 `portable_backtest`
- 下一步如何从 `portable_backtest` 升级到 `research_grade_local`

## 文案原则

- 不伪装成“已经完成真实回测”。
- 遇到 `data_required_cutoff` 时，要直说被截断了，以及为什么。
- 遇到 `full_workspace` 时，也要说明当前结论的可信度档位，而不是泛化成“可直接实盘”。
