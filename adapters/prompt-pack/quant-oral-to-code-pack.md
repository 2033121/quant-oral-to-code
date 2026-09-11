<!-- GENERATED FILE — DO NOT EDIT BY HAND. 源：skills/quant-oral-to-code/*，重建：adapters/build_prompt_pack.py -->
# quant-oral-to-code — 单文件提示词包

> 用途：在无文件系统的聊天型智能体（WorkBuddy、网页版 LLM 等）里，把口述量化策略转写成**结构化策略规格（DSL）+ guardrails 审查结论**，可直接交给文件型智能体（Claude Code / Codex / ZCode / DSH）按包内链路落脚本。
> 边界：聊天型环境**不声称能执行回测**；所有脚本与 Schema 在来源仓库 `skills/quant-oral-to-code/scripts/ 与 schemas/`。

## 包内文件

| # | 文件 |
| --- | --- |
| 1 | `skills/quant-oral-to-code/SKILL.md（主协议）` |
| 2 | `modules/codegen.md` |
| 3 | `modules/data.md` |
| 4 | `modules/dsl.md` |
| 5 | `modules/guardrails.md` |
| 6 | `modules/intake.md` |
| 7 | `modules/onboarding.md` |
| 8 | `modules/preflight.md` |
| 9 | `modules/report.md` |

## 硬条款（防幻觉）

1. **数据门槛**：缺少真实数据、字段映射或关键定义时，必须进入 cutoff / `DATA_REQUIRED` 路径，禁止输出"回测完成"类结论。
2. **信念分级**：只能声明 `demo_only` / `portable_backtest` / `research_grade_local`，且必须给出支撑材料；聊天环境最多 `demo_only`，且需写明"仅流程转写，未执行"。
3. **guardrails 先行**：任何策略规格必须附前视/过拟合/样本外/成交假设的审查结论。
4. **DuckDB 固定口径**：生成的数据管道说明必须以"先落 DuckDB 再回测"为默认描述。
5. 条目缺失时明说，禁止编造字段名或数据源能力。

---

<!-- ===== 文件 1: skills/quant-oral-to-code/SKILL.md（主协议） ===== -->

## [1] skills/quant-oral-to-code/SKILL.md（主协议）

# quant-oral-to-code

这个 skill 的目标是把自然语言策略描述整理成一条清晰链路：

1. `intake` 收集策略口述、数据条件和输出预期。
2. `dsl` 把口述压缩成结构化策略规格。
3. `guardrails` 审查前视、过拟合、样本外缺失和乐观成交假设。
4. `codegen` 生成策略代码骨架与回测入口。
5. `report` 输出交付说明、限制和下一步建议。

当前阶段只提供最小可运行骨架，重点是把模块边界和验证入口搭起来，供后续任务继续填充脚本、模板、schema 和例子。

## 固定口径

- 标准数据归一化目标固定为 DuckDB；后续导入 CSV/Parquet/JSON/SQLite 时，也要先落到 DuckDB 再进入统一回测路径。
- claim level 的基础枚举至少包含 `demo_only`、`portable_backtest`、`research_grade_local`。
- 缺少真实数据、字段映射或关键定义时，必须进入 cutoff / `DATA_REQUIRED` 路径，而不是伪装成正式回测完成。

## 使用顺序

默认按以下顺序读取模块：

- `modules/preflight.md`
- `modules/intake.md`
- `modules/dsl.md`
- `modules/guardrails.md`
- `modules/data.md`
- `modules/codegen.md`
- `modules/onboarding.md`
- `modules/report.md`

## 当前交付约束

- 只承诺生成骨架，不承诺已经具备完整回测能力。
- 没有真实数据时，必须明确说明不能伪装成研究级回测结论。
- 输出中要显式标记假设、缺口和需要用户补充的数据。
- 当前默认链路已经接入 Task 2 的权威模块：preflight、DuckDB 数据契约、claim gate 和 onboarding 文案。

## 验证

结构验证脚本：

```powershell
python "skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
```

<!-- ===== 文件 2: modules/codegen.md ===== -->

## [2] modules/codegen.md

# codegen

`codegen` 负责把 DSL 和护栏结论转成代码交付骨架。

## 当前阶段范围

- 策略文件骨架
- 回测入口骨架
- 结果摘要骨架

## 输入

- `intake` 整理后的原始需求
- `dsl` 结构化结果
- `guardrails` 风险审查结果

## 输出目标

- 后续任务要生成 `strategy.py`
- 后续任务要生成 `run_backtest.py`
- 后续任务要生成结果与说明文件
- 后续统一数据入口的标准归一化目标固定为 DuckDB

## 生成原则

- 先保证文件职责清楚，再补复杂实现。
- 生成物必须与 `claim_level` 对齐。
- 缺少真实数据时，代码可以是 demo 或 dry-run 骨架，但说明必须诚实。
- 缺少真实数据或最小数据契约时，要走 cutoff / `DATA_REQUIRED`，而不是伪装成交付了正式回测。

<!-- ===== 文件 3: modules/data.md ===== -->

## [3] modules/data.md

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

<!-- ===== 文件 4: modules/dsl.md ===== -->

## [4] modules/dsl.md

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

<!-- ===== 文件 5: modules/guardrails.md ===== -->

## [5] modules/guardrails.md

# guardrails

`guardrails` 负责在生成代码前先拦截常见研究陷阱。

## 重点检查

- 是否存在前视或未来函数风险。
- 是否只有样本内描述，没有样本外或 holdout 思路。
- 是否把 `same_bar_close` 之类的乐观执行假设当成默认真实成交。
- 是否把模糊选股语言包装成已验证策略。
- 是否在缺数据时误导性地产出“完成回测”的口吻。

## 最小结论字段

- `blocking_issues`
- `warnings`
- `claim_level`
- `recommended_next_step`

## 审查原则

- 有硬伤就阻断，不为了“产出完整”而忽略风险。
- 没有数据时允许给代码骨架，但不能给研究级结论。
- claim level 的基础枚举至少是 `demo_only`、`portable_backtest`、`research_grade_local`。
- 缺数据、缺字段映射或缺最小定义时，要进入 cutoff / `DATA_REQUIRED` 路径。
- 结论要能解释给新手听，而不是只留内部标签。

<!-- ===== 文件 6: modules/intake.md ===== -->

## [6] modules/intake.md

# intake

`intake` 负责把用户的原始口述收成后续可处理的输入包。

## 必收信息

- 策略想做什么：选股、择时、单标的、组合、事件驱动或结构信号。
- 触发条件：入场、出场、过滤、风控、仓位、频率。
- 数据条件：已有 CSV/Parquet/JSON/SQLite/DuckDB，还是完全没有数据。
- 输出预期：只要代码骨架、要不要回测入口、要不要结果摘要。

## 提问原则

- 先收最少必需信息，不一次堆太多问题。
- 优先识别用户是否缺数据，避免后面误报“可回测”。
- 即使用户提供的是 CSV/Parquet/JSON/SQLite，后续标准归一化目标也固定为 DuckDB。
- 用户术语模糊时，要保留原话，交给 `dsl` 模块做归一化。
- 缺数据、缺字段映射或缺关键约束时，要显式标记会进入 cutoff / `DATA_REQUIRED` 路径。

## 产物

建议整理成一个最小 intake 包，至少包含：

```json
{
  "raw_prompt": "",
  "strategy_goal": "",
  "data_state": "unknown",
  "expected_outputs": [],
  "claim_level_target": "demo_only"
}
```

<!-- ===== 文件 7: modules/onboarding.md ===== -->

## [7] modules/onboarding.md

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

<!-- ===== 文件 8: modules/preflight.md ===== -->

## [8] modules/preflight.md

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

<!-- ===== 文件 9: modules/report.md ===== -->

## [9] modules/report.md

# report

`report` 负责把生成结果、限制和下一步动作说清楚。

## 报告至少要回答

- 当前交付到了哪一步。
- 这是 `demo_only`、`portable_backtest` 还是更高可信度结果。
- 缺什么数据、缺什么定义、缺什么验证。
- 用户下一步最应该做什么。

## 报告风格

- 先讲结论，再讲限制。
- 用新手能理解的话解释风险。
- 不把演示结果写成正式研究结论。
- 明确说明标准归一化目标是 DuckDB，缺数据时会进入 cutoff / `DATA_REQUIRED`。

## 最小产物

当前阶段可以只要求一个文本摘要模板思路，后续再扩展成 Markdown 和 JSON 双产物。
