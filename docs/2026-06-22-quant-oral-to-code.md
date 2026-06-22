# 抽象语言直出可回测策略代码 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户用抽象自然语言描述策略后，系统直接生成可回测的策略代码、回测入口、测试、结果摘要与收益曲线/回撤等常用观察数据，并自动规避前视、过拟合、幸存者偏差和不真实执行假设。

**Architecture:** 这份计划现在采用**单一主执行栈**：`自然语言 -> strategy_spec -> translation_trace -> guardrail_review -> claim_gate -> data_profile/data_contract -> DuckDB 标准化 -> 自包含 strategy.py -> 自包含 run_backtest.py -> result_summary/artifact_manifest`。`quant-strategy`、缠论项目和量学脚本只作为规则来源、模板来源和研究对照，不再作为主执行入口。这样 `demo_mode`、`portable_backtest`、`research_grade_local` 三档都跑同一条执行链，只是数据来源、校验强度和 claim level 不同。

**Tech Stack:** Python 3.12、DuckDB、pandas、pytest、JSON Schema、PowerShell、Markdown、现有缠论项目 `D:\tool\novel\_projects\projects\缠解天机`、现有量学/量化参考脚本、可选本地 `quant-strategy` 结果对照

---

## Success Criteria

用户说一句抽象策略描述后，系统最终至少要能交付这些文件：

- `strategy_spec.json`：内部中间规格，供审查和复现
- `translation_trace.json`：原话片段到 DSL 字段、代码位置、假设来源与置信度的映射
- `strategy.py`：可回测策略代码
- `run_backtest.py`
- `experiment_protocol.json`
- `test_strategy_smoke.py`
- `data_contract.json`
- `claim_report.json`
- `result_summary.md`
- `metrics_snapshot.json`
- `equity_curve.png` 或等价曲线数据
- `drawdown_summary.json`

并且这套 skill 至少要支持三种运行画像：

- `full_research_mode`：本地已有 `quant-strategy` / 缠论项目 / 可用研究数据，输出研究级回测结果
- `portable_csv_mode`：用户没有你的本地数据栈，但能提供自己的 CSV/Parquet/JSON 行情数据；skill 负责导入并统一落为 DuckDB 后生成并运行策略代码
- `demo_mode`：用户既没有量化数据也没有现成项目，只能先生成代码、跑 bundled sample/synthetic smoke，并明确标记“仅演示，不代表研究结论”
- 任何真实或合成行情数据一旦进入这套 skill，最终都统一归一化保存为 `DuckDB`；`CSV/JSON/Parquet/SQLite` 只允许作为导入格式、外部来源或临时交换格式，不作为标准回测持久化格式

并且在生成阶段自动处理这些坑：

- 财务/估值因子前视
- 全样本参数最优化
- 没有样本外/holdout
- 当前股票池回填历史
- `same_bar_close` 这类乐观成交假设
- 未考虑停牌、涨跌停、成交容量

并且对没有本地数据的用户，必须满足以下至少一条：

- 自动生成 `data/fetch_data.py`、`data/provider_setup.md` 和 `data/provider_choice.json`，让用户可以去拉取所需 A 股数据
- 或者明确进入 `DATA_REQUIRED` 截断路径，只交付 `strategy_spec.json`、`translation_trace.json`、`data_contract.json`、`README_beginner.md` 与下一步数据准备说明

并且对于 `demo_mode` / `dry_run` / `synthetic smoke`：

- 不允许把演示结果伪装成研究级回测
- 必须在 `claim_report.json` 与 `result_summary.md` 中显式写出 `claim_level=demo_only`

## Scope Boundaries

- 本计划**不包含音频/STT**。
- 本计划**包含直接策略代码生成**，这是主线，不是二期扩展。
- 本计划必须对外行用户提供“最低可用路径”：
  - 没有任何数据时，至少能拿到 `DATA_REQUIRED` 截断产物、失败原因解释与数据获取指引
  - 只有 CSV/Parquet/JSON/SQLite/DuckDB 时，至少能先标准化到 DuckDB，再跑单标的或简单双标的回测
  - 只有本地 `quant-strategy` 时，不强依赖它作为主执行器；最多把它作为研究对照或未来适配层

- 本计划优先支持三类代码生成模式：
  - `standalone_generated`：生成不依赖外部私有 engine 的自包含策略代码与回测脚本
  - `standalone_mapped`：若抽象语言本质上就是现有策略变体，则生成薄包装代码并映射到统一模板参数
  - `chanlun_or_liangxue_generated`：若语义明显属于缠论/量学 DSL，则生成桥接到对应规则库的自包含 wrapper，而不是假装它只是普通均线策略

## Trust Gate And Data Acquisition Strategy

- `claim_level` 必须是机器可判定字段，而不是只写在说明文字里：
  - `demo_only`：只有样例数据或 synthetic smoke，只证明链路和代码能跑
  - `portable_backtest`：用户自带 CSV/Parquet/JSON，完成了基础数据校验，但没有本地研究级量化栈
  - `research_grade_local`：具备本地量化内核、明确协议、可审计数据与研究护栏后，才允许输出研究级结论
- 本计划的**唯一主执行器**是生成工作区里的 `run_backtest.py`；任何本地 `quant-strategy`、缠论脚本或量学脚本都只能作为：
  - 规则翻译参考
  - 研究对照/交叉验证来源
  - 可选适配目标
  但不能再反向决定主协议、主数据契约或主回测接口
- 若缺少真实可用数据，skill 的默认顺序必须是：
  - 先尝试生成 A 股数据获取代码
  - 再给出 provider setup 指南
  - 如果仍无法满足最低数据契约，则进入 `DATA_REQUIRED` 截断路径，而不是假装已完成真实回测
- A 股数据源按接入优先级分层：
  - `tier_a_no_auth`：`AKShare`、`efinance`、`AData`、`baostock`，适合新手快速拉历史行情
  - `tier_b_auth_or_trial`：`TuShare Pro`、`JQData SDK`，适合愿意注册账号、配置 token 或申请试用的用户
  - `tier_c_snapshot_only`：`easyquotation`、`Ashare`，适合实时快照或轻量补数，不默认作为研究级历史回测主源
  - `tier_d_manual_csv`：用户从券商、通达信、同花顺、东方财富或已有数据库导出 CSV/Parquet，再走 `portable_csv_mode`
- 任何数据源接入都必须记录：
  - 来源名称、认证方式、复权口径、时间粒度、字段映射、抓取时间、失败重试建议
- 数据落盘统一规范：
  - 标准持久化格式固定为 `DuckDB`
  - 推荐输出路径固定为 `generated_strategies/<strategy_slug>/data/normalized/market.duckdb`
  - `CSV/JSON/Parquet/SQLite` 可以作为用户输入、手工导出、外部数据库或调试快照，但回测入口默认只读取规范化后的 `DuckDB`
- `data_contract.json` 必须显式声明：
  - `storage_format`：固定为 `duckdb`
  - `storage_target`：固定指向 DuckDB 数据库文件路径
  - `bars_table_name`：默认 `bars`
  - `table_layout`：单表、多表或按 `symbol/date` 分区
  - `primary_key`：默认 `["symbol", "trade_date"]`
  - `required_tables`：至少包含 `bars`
  - `required_columns`：至少包含 `symbol, trade_date, open, high, low, close, volume`
  - `write_disposition`：`overwrite | append | upsert`
  - `raw_input_format`：原始来源是 `csv/json/api/sqlite/duckdb/parquet` 中哪一种
  - `data_hash`：标准化后 DuckDB 的内容指纹
  - `provider_name`：数据来源名
  - `adjustment_mode`：`none | qfq | hfq`

---

## Planned File Structure

### New generator skill

- `.trae/skills/quant-oral-to-code/SKILL.md`
- `.trae/skills/quant-oral-to-code/modules/intake.md`
- `.trae/skills/quant-oral-to-code/modules/dsl.md`
- `.trae/skills/quant-oral-to-code/modules/guardrails.md`
- `.trae/skills/quant-oral-to-code/modules/codegen.md`
- `.trae/skills/quant-oral-to-code/modules/preflight.md`
- `.trae/skills/quant-oral-to-code/modules/data.md`
- `.trae/skills/quant-oral-to-code/modules/onboarding.md`
- `.trae/skills/quant-oral-to-code/modules/report.md`
- `.trae/skills/quant-oral-to-code/references/domain_ontology.json`
- `.trae/skills/quant-oral-to-code/references/example_registry.json`
- `.trae/skills/quant-oral-to-code/references/guardrail_rules.json`
- `.trae/skills/quant-oral-to-code/references/codegen_templates.json`
- `.trae/skills/quant-oral-to-code/references/data_access_matrix.json`
- `.trae/skills/quant-oral-to-code/references/a_share_provider_notes.md`
- `.trae/skills/quant-oral-to-code/references/data_provider_matrix.json`
- `.trae/skills/quant-oral-to-code/references/novice_glossary.json`
- `.trae/skills/quant-oral-to-code/schemas/strategy_spec.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/translation_trace.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/guardrail_review.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/preflight_report.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/data_profile.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/data_contract.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/claim_report.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/generated_artifact_manifest.schema.json`
- `.trae/skills/quant-oral-to-code/schemas/experiment_protocol.schema.json`
- `.trae/skills/quant-oral-to-code/templates/single_asset_strategy.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/portfolio_strategy.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/run_backtest.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/test_strategy_smoke.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/result_summary.md.tmpl`
- `.trae/skills/quant-oral-to-code/templates/portable_csv_loader.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_akshare.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_efinance.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_adata.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_baostock.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_tushare.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_jqdatasdk.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_easyquotation.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/fetch_with_ashare.py.tmpl`
- `.trae/skills/quant-oral-to-code/templates/sample_ohlcv.csv`
- `.trae/skills/quant-oral-to-code/examples/ma_beginner_prompt.md`
- `.trae/skills/quant-oral-to-code/examples/chanlun_third_buy_prompt.md`
- `.trae/skills/quant-oral-to-code/examples/liangxue_breakout_prompt.md`
- `.trae/skills/quant-oral-to-code/examples/no_data_beginner_prompt.md`
- `.trae/skills/quant-oral-to-code/examples/bad_csv_prompt.md`
- `.trae/skills/quant-oral-to-code/examples/unsupported_terms_prompt.md`
- `.trae/skills/quant-oral-to-code/scripts/build_strategy_spec.py`
- `.trae/skills/quant-oral-to-code/scripts/check_runtime_capabilities.py`
- `.trae/skills/quant-oral-to-code/scripts/resolve_repo_root.py`
- `.trae/skills/quant-oral-to-code/scripts/detect_data_profile.py`
- `.trae/skills/quant-oral-to-code/scripts/build_data_contract.py`
- `.trae/skills/quant-oral-to-code/scripts/normalize_to_duckdb.py`
- `.trae/skills/quant-oral-to-code/scripts/select_data_provider.py`
- `.trae/skills/quant-oral-to-code/scripts/generate_data_fetcher.py`
- `.trae/skills/quant-oral-to-code/scripts/validate_fetched_dataset.py`
- `.trae/skills/quant-oral-to-code/scripts/emit_translation_trace.py`
- `.trae/skills/quant-oral-to-code/scripts/review_guardrails.py`
- `.trae/skills/quant-oral-to-code/scripts/build_claim_report.py`
- `.trae/skills/quant-oral-to-code/scripts/resolve_codegen_mode.py`
- `.trae/skills/quant-oral-to-code/scripts/generate_strategy_code.py`
- `.trae/skills/quant-oral-to-code/scripts/load_generated_strategy.py`
- `.trae/skills/quant-oral-to-code/scripts/backtest_kernel.py`
- `.trae/skills/quant-oral-to-code/scripts/generate_backtest_runner.py`
- `.trae/skills/quant-oral-to-code/scripts/generate_strategy_tests.py`
- `.trae/skills/quant-oral-to-code/scripts/build_demo_dataset.py`
- `.trae/skills/quant-oral-to-code/scripts/render_beginner_readme.py`
- `.trae/skills/quant-oral-to-code/scripts/emit_artifact_manifest.py`
- `.trae/skills/quant-oral-to-code/scripts/summarize_quant_result.py`
- `.trae/skills/quant-oral-to-code/scripts/run_generated_strategy_smoke.py`
- `.trae/skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py`
- `.trae/skills/quant-oral-to-code/scripts/test_skill_layout.py`
- `.trae/skills/quant-oral-to-code/scripts/test_spec_builder.py`
- `.trae/skills/quant-oral-to-code/scripts/test_preflight.py`
- `.trae/skills/quant-oral-to-code/scripts/test_data_profile.py`
- `.trae/skills/quant-oral-to-code/scripts/test_data_contract.py`
- `.trae/skills/quant-oral-to-code/scripts/test_data_provider_selection.py`
- `.trae/skills/quant-oral-to-code/scripts/test_data_fetcher_codegen.py`
- `.trae/skills/quant-oral-to-code/scripts/test_duckdb_normalization.py`
- `.trae/skills/quant-oral-to-code/scripts/test_guardrails.py`
- `.trae/skills/quant-oral-to-code/scripts/test_claim_gate.py`
- `.trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py`
- `.trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py`
- `.trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py`
- `.trae/skills/quant-oral-to-code/scripts/test_protocol_replay.py`
- `.trae/skills/quant-oral-to-code/scripts/test_duckdb_readonly.py`
- `.trae/skills/quant-oral-to-code/scripts/test_data_required_cutoff.py`
- `.trae/skills/quant-oral-to-code/scripts/test_result_summary.py`
- `.trae/skills/quant-oral-to-code/scripts/test_artifact_manifest.py`
- `.trae/skills/quant-oral-to-code/scripts/run_full_validation.py`

### Generated output workspace

- `generated_strategies/<strategy_slug>/strategy_spec.json`
- `generated_strategies/<strategy_slug>/translation_trace.json`
- `generated_strategies/<strategy_slug>/guardrail_review.json`
- `generated_strategies/<strategy_slug>/data_contract.json`
- `generated_strategies/<strategy_slug>/claim_report.json`
- `generated_strategies/<strategy_slug>/strategy.py`
- `generated_strategies/<strategy_slug>/run_backtest.py`
- `generated_strategies/<strategy_slug>/experiment_protocol.json`
- `generated_strategies/<strategy_slug>/test_strategy_smoke.py`
- `generated_strategies/<strategy_slug>/artifact_manifest.json`
- `generated_strategies/<strategy_slug>/preflight_report.json`
- `generated_strategies/<strategy_slug>/data_profile.json`
- `generated_strategies/<strategy_slug>/README_beginner.md`
- `generated_strategies/<strategy_slug>/data/provider_choice.json`
- `generated_strategies/<strategy_slug>/data/provider_setup.md`
- `generated_strategies/<strategy_slug>/data/fetch_data.py`
- `generated_strategies/<strategy_slug>/data/raw/`
- `generated_strategies/<strategy_slug>/data/normalized/`
- `generated_strategies/<strategy_slug>/data/normalized/market.duckdb`
- `generated_strategies/<strategy_slug>/results/result_summary.md`
- `generated_strategies/<strategy_slug>/results/metrics_snapshot.json`
- `generated_strategies/<strategy_slug>/results/report_card.json`
- `generated_strategies/<strategy_slug>/results/failure_report.md`
- `generated_strategies/<strategy_slug>/results/equity_curve.png`
- `generated_strategies/<strategy_slug>/results/drawdown_summary.json`

### Existing local references that codegen must learn from

- `D:\tool\novel\_projects\projects\缠解天机\scripts\chanlun_compute.py`
- `D:\tool\novel\_projects\projects\缠解天机\scripts\candidate_picker.py`
- `D:\tool\novel\_projects\projects\缠解天机\scripts\risk_agent.py`
- `D:\tool\novel\_projects\projects\缠解天机\data\workflow_d_20260620.json`
- `D:\tool\novel\_projects\projects\缠解天机\data\signals_daily_20260622.json`
- `D:\tool\novel\_projects\projects\缠解天机\data\protocols\signal_accuracy_baseline_v2.json`
- `D:\tool\novel\.trae\skills\quant-strategy\scripts\liangxue_core.py`
- `D:\tool\novel\.trae\skills\quant-strategy\scripts\liangzhu_liangxian_quant.py`
- `D:\tool\novel\.trae\skills\quant-strategy\scripts\liangzhu_liangxian_5y_study.py`
- `D:\tool\novel\.trae\skills\quant-strategy\scripts\liangxue_holdout_signal_validate.py`
- `D:\tool\novel\.trae\skills\quant-strategy\scripts\liangxue_layered_portfolio_validate.py`

---

## Authoritative Rewrite

> **This section is authoritative and supersedes the older draft tasks later in this file.**
> 自本段开始，实施时只执行这里的任务序列。后面的旧 Task 2-9 保留仅供对照，不再作为执行依据。
> 下方原有的 `Task 1` 骨架任务仍然有效，应先执行；本段从 `Authoritative Task 2` 开始接续。

### Architecture Reset

- **唯一主执行栈**
  - 输入侧：`csv | parquet | json | sqlite | duckdb | provider api`
  - 规范化侧：统一写入 `generated_strategies/<slug>/data/normalized/market.duckdb`
  - 策略侧：生成**自包含** `strategy.py`，不得依赖 `engine.strategy_base` 或私有外部 loader
  - 回测侧：生成**自包含** `run_backtest.py`，只读 DuckDB，只消费本计划定义的 `experiment_protocol.json`
  - 结果侧：生成 `claim_report.json`、`artifact_manifest.json`、`result_summary.md`
- **本地参考项目的角色**
  - `quant-strategy`：仅作研究方法与未来适配对照，不再作为 MVP 主执行器
  - 缠论项目：仅作规则翻译、模板来源与研究反例来源
  - 量学脚本：仅作规则翻译、模板来源与研究反例来源
- **硬分支**
  - `claim_report.artifact_policy == full_workspace`：才允许生成 `strategy.py`、`run_backtest.py`、`results/`
  - `claim_report.artifact_policy == data_required_cutoff`：只允许交付 `strategy_spec.json`、`translation_trace.json`、`data_contract.json`、`claim_report.json`、`README_beginner.md`、`data/provider_choice.json`

### Authoritative Task 2: 固化根路径解析、唯一执行栈和核心契约

**Files:**
- Create: `.trae/skills/quant-oral-to-code/modules/preflight.md`
- Create: `.trae/skills/quant-oral-to-code/modules/data.md`
- Create: `.trae/skills/quant-oral-to-code/modules/onboarding.md`
- Create: `.trae/skills/quant-oral-to-code/schemas/preflight_report.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/data_profile.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/data_contract.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/claim_report.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/generated_artifact_manifest.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/experiment_protocol.schema.json`
- Create: `.trae/skills/quant-oral-to-code/scripts/resolve_repo_root.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/check_runtime_capabilities.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/build_data_contract.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/build_claim_report.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/emit_artifact_manifest.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/render_beginner_readme.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_preflight.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_contract.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_claim_gate.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from resolve_repo_root import resolve_repo_root
from check_runtime_capabilities import check_runtime_capabilities
from build_data_contract import build_data_contract


def test_preflight_resolves_repo_root_and_duckdb_contract(tmp_path: Path):
    repo_root = resolve_repo_root(Path(__file__).resolve())
    assert (repo_root / ".trae").exists()

    preflight = check_runtime_capabilities(repo_root)
    assert preflight["python_ok"] is True
    assert "duckdb" in preflight["required_python_packages"]

    contract = build_data_contract(
        storage_target=tmp_path / "data" / "normalized" / "market.duckdb",
        raw_input_format="csv",
        provider_name="manual_csv",
        adjustment_mode="qfq",
    )
    assert contract["storage_format"] == "duckdb"
    assert contract["bars_table_name"] == "bars"
    assert contract["primary_key"] == ["symbol", "trade_date"]
```

```python
from build_claim_report import build_claim_report


def test_claim_gate_distinguishes_cutoff_and_full_workspace():
    blocked = build_claim_report(
        review={"blocking": ["low_translation_confidence"], "warnings": []},
        data_profile={"mode": "demo_mode", "data_readiness": "demo_only"},
        data_contract=None,
    )
    assert blocked["artifact_policy"] == "data_required_cutoff"
    assert blocked["claim_level"] == "demo_only"

    runnable = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract={"storage_format": "duckdb", "data_hash": "abc"},
    )
    assert runnable["artifact_policy"] == "full_workspace"
    assert runnable["claim_level"] == "portable_backtest"
```

### Authoritative Task 3: 实现多输入源识别、DuckDB 标准化与数据体检

**Files:**
- Create: `.trae/skills/quant-oral-to-code/templates/portable_csv_loader.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/sample_ohlcv.csv`
- Create: `.trae/skills/quant-oral-to-code/scripts/detect_data_profile.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/normalize_to_duckdb.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/validate_fetched_dataset.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/build_demo_dataset.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_profile.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_duckdb_normalization.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_duckdb_readonly.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from detect_data_profile import detect_data_profile
from normalize_to_duckdb import normalize_to_duckdb


def test_data_profile_detects_csv_parquet_json_sqlite_and_duckdb(tmp_path: Path):
    (tmp_path / "bars.csv").write_text("symbol,trade_date,open,high,low,close,volume\n000001.SZ,2024-01-02,10,11,9,10.5,1000\n", encoding="utf-8")
    profile = detect_data_profile(tmp_path)
    assert profile["mode"] == "portable_csv_mode"
    assert profile["raw_input_format"] == "csv"


def test_normalize_to_duckdb_creates_bars_table(tmp_path: Path):
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text("symbol,trade_date,open,high,low,close,volume\n000001.SZ,2024-01-02,10,11,9,10.5,1000\n000001.SZ,2024-01-03,10.5,11.2,10.3,11.0,1200\n", encoding="utf-8")
    db_path = tmp_path / "market.duckdb"
    result = normalize_to_duckdb(csv_path, db_path, raw_input_format="csv", adjustment_mode="qfq")
    assert result["bars_table_name"] == "bars"
    assert db_path.exists()
```

### Authoritative Task 4: 实现 provider 路由、真实 fetcher 生成与 cutoff 分流

**Files:**
- Create: `.trae/skills/quant-oral-to-code/references/data_access_matrix.json`
- Create: `.trae/skills/quant-oral-to-code/references/a_share_provider_notes.md`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_akshare.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_efinance.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_adata.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_baostock.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_tushare.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_jqdatasdk.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/select_data_provider.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_data_fetcher.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_provider_selection.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_fetcher_codegen.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from select_data_provider import select_data_provider
from generate_data_fetcher import generate_data_fetcher


def test_provider_selection_and_cutoff_artifacts_are_different(tmp_path: Path):
    provider = select_data_provider({"needs_history_bars": True, "user_prefers_zero_setup": True, "user_can_register_account": False})
    assert provider["provider"] == "akshare"
    assert provider["decision"] == "generated_fetcher"

    generated = generate_data_fetcher(provider, tmp_path, symbol="000001.SZ")
    assert (tmp_path / "data" / "fetch_data.py").exists()
    assert (tmp_path / "data" / "provider_choice.json").exists()

    cutoff = generate_data_fetcher({"provider": "manual_csv", "tier": "tier_d_manual_csv", "decision": "data_required_cutoff"}, tmp_path / "cutoff_case", symbol="000001.SZ")
    assert cutoff["decision"] == "data_required_cutoff"
    assert (tmp_path / "cutoff_case" / "data" / "fetch_data.py").exists() is False
```

### Authoritative Task 5: 生成 strategy_spec 与 translation_trace

**Files:**
- Create: `.trae/skills/quant-oral-to-code/schemas/strategy_spec.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/translation_trace.schema.json`
- Create: `.trae/skills/quant-oral-to-code/references/domain_ontology.json`
- Create: `.trae/skills/quant-oral-to-code/scripts/build_strategy_spec.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/emit_translation_trace.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_spec_builder.py`

- [ ] **Step 1: Write the failing test**

```python
from build_strategy_spec import build_strategy_spec
from emit_translation_trace import emit_translation_trace


def test_strategy_spec_and_trace_capture_rules_assumptions_and_confidence():
    prompt = "把 5 日均线上穿 20 日均线、跌破 10 日均线止损、只做日线 A 股、输出收益曲线和最大回撤，直接写成可回测策略代码。"
    spec = build_strategy_spec(prompt)
    trace = emit_translation_trace(prompt, spec)
    assert spec["strategy_family"] == "trend_basic"
    assert spec["entry_rules"][0]["kind"] == "moving_average_cross"
    assert trace["translation_confidence"] >= 0.6
```

### Authoritative Task 6: 生成 guardrail_review、claim gate 与 DATA_REQUIRED 行为

**Files:**
- Create: `.trae/skills/quant-oral-to-code/schemas/guardrail_review.schema.json`
- Create: `.trae/skills/quant-oral-to-code/references/guardrail_rules.json`
- Create: `.trae/skills/quant-oral-to-code/scripts/review_guardrails.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_guardrails.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_required_cutoff.py`

- [ ] **Step 1: Write the failing tests**

```python
from review_guardrails import review_guardrails
from build_claim_report import build_claim_report


def test_guardrails_block_lookahead_and_same_bar_close():
    spec = {
        "factor_requirements": {"uses_financial_data": True, "pit_checked": False},
        "validation_requirements": {"optimized_on_full_sample": True, "has_holdout": False},
        "execution_requirements": {"execution_mode": "same_bar_close"},
        "translation_confidence": 0.45,
        "unresolved_terms": ["强势", "放量确认"],
    }
    review = review_guardrails(spec)
    claim = build_claim_report(review, {"mode": "portable_csv_mode", "data_readiness": "ready"}, {"storage_format": "duckdb"})
    assert "financial_factor_without_pit_visibility" in review["blocking"]
    assert "same_bar_close_is_optimistic" in review["warnings"]
    assert claim["artifact_policy"] == "data_required_cutoff"
```

### Authoritative Task 7: 生成自包含策略代码

**Files:**
- Create: `.trae/skills/quant-oral-to-code/references/example_registry.json`
- Create: `.trae/skills/quant-oral-to-code/templates/single_asset_strategy.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/portfolio_strategy.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/resolve_codegen_mode.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_strategy_code.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/load_generated_strategy.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from resolve_codegen_mode import resolve_codegen_mode
from generate_strategy_code import generate_strategy_code


def test_codegen_mode_and_strategy_code_are_self_contained(tmp_path: Path):
    spec = {
        "strategy_name": "ma_demo",
        "strategy_family": "trend_basic",
        "market": "A股",
        "timeframe": "日线",
        "entry_rules": [{"kind": "moving_average_cross", "fast": 5, "slow": 20}],
        "exit_rules": [{"kind": "price_below_ma", "ma": 10}],
    }
    mode = resolve_codegen_mode(spec)
    out = generate_strategy_code(spec, mode, tmp_path)
    text = Path(out["strategy_file"]).read_text(encoding="utf-8")
    assert mode["mode"] == "standalone_generated"
    assert "class GeneratedStrategy" in text
    assert "engine.strategy_base" not in text
```

### Authoritative Task 8: 生成只读 DuckDB runner 与协议回放

**Files:**
- Create: `.trae/skills/quant-oral-to-code/templates/run_backtest.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/test_strategy_smoke.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/backtest_kernel.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_backtest_runner.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_strategy_tests.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_protocol_replay.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_duckdb_readonly.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
import json

from generate_backtest_runner import generate_backtest_runner


def test_runner_reads_duckdb_readonly_and_writes_protocol(tmp_path: Path):
    out = generate_backtest_runner({"strategy_name": "ma_demo", "market": "A股", "timeframe": "日线"}, tmp_path)
    runner_text = Path(out["runner_file"]).read_text(encoding="utf-8")
    protocol = json.loads(Path(out["protocol_file"]).read_text(encoding="utf-8"))
    assert "read_only=True" in runner_text
    assert protocol["data"]["bars_table_name"] == "bars"
    assert protocol["execution"]["mode"] == "next_open"
```

### Authoritative Task 9: 生成结果摘要、artifact manifest 与 README

**Files:**
- Create: `.trae/skills/quant-oral-to-code/templates/result_summary.md.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/summarize_quant_result.py`
- Modify: `.trae/skills/quant-oral-to-code/scripts/emit_artifact_manifest.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_result_summary.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_artifact_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
from summarize_quant_result import summarize_quant_result
from emit_artifact_manifest import emit_artifact_manifest


def test_result_summary_and_manifest_capture_claim_and_outputs():
    result = {
        "main_backtest": {"summary": {"total_return": 0.21, "max_drawdown": -0.12, "sharpe_ratio": 1.1}},
        "claim_report": {"claim_level": "portable_backtest", "decision": "runnable"},
        "guardrail_review": {"blocking": [], "warnings": ["same_bar_close_is_optimistic"]},
    }
    text = summarize_quant_result(result)
    manifest = emit_artifact_manifest({"strategy.py": "abc"}, claim_level="portable_backtest")
    assert "portable_backtest" in text
    assert "strategy.py" in manifest["artifacts"]
```

### Authoritative Task 10: 跑端到端正例/负例验证并更新 handoff

**Files:**
- Create: `.trae/skills/quant-oral-to-code/examples/ma_beginner_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/chanlun_third_buy_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/liangxue_breakout_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/no_data_beginner_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/bad_csv_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/unsupported_terms_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/scripts/run_generated_strategy_smoke.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/run_full_validation.py`
- Modify: `.trae/sync/CURRENT.md`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from run_full_validation import run_prompt


def test_full_validation_covers_positive_and_cutoff_paths(tmp_path: Path):
    ma_root = run_prompt("把 5 日均线上穿 20 日均线这件事直接写成可回测策略代码，还要有收益曲线和最大回撤。", "ma_demo", tmp_path)
    ambiguous_root = run_prompt("找最近看起来很强、放量确认、最好别回撤太大的票。你先别假装回测，告诉我缺什么数据和定义。", "ambiguous_demo", tmp_path)
    assert (ma_root / "run_backtest.py").exists()
    assert (ma_root / "data" / "normalized" / "market.duckdb").exists()
    assert (ambiguous_root / "strategy_spec.json").exists()
    assert (ambiguous_root / "run_backtest.py").exists() is False
```

**Execution rule:** 实施时必须严格执行这条链路：

1. `resolve_repo_root -> check_runtime_capabilities`
2. `build_strategy_spec -> emit_translation_trace -> review_guardrails`
3. `detect_data_profile`
4. 若无数据：`select_data_provider -> generate_data_fetcher` 或 `build_demo_dataset`
5. `normalize_to_duckdb -> validate_fetched_dataset -> build_data_contract`
6. `build_claim_report`
7. 若 `artifact_policy == data_required_cutoff`：立即停止，只落 cutoff 产物
8. 若 `artifact_policy == full_workspace`：继续 `resolve_codegen_mode -> generate_strategy_code -> generate_backtest_runner -> generate_strategy_tests`
9. 运行 `run_backtest.py`
10. 生成 `result_summary.md`、`artifact_manifest.json`、`README_beginner.md`

**Full verification command:**

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_skill_layout.py" ".trae/skills/quant-oral-to-code/scripts/test_preflight.py" ".trae/skills/quant-oral-to-code/scripts/test_data_contract.py" ".trae/skills/quant-oral-to-code/scripts/test_claim_gate.py" ".trae/skills/quant-oral-to-code/scripts/test_data_profile.py" ".trae/skills/quant-oral-to-code/scripts/test_duckdb_normalization.py" ".trae/skills/quant-oral-to-code/scripts/test_data_provider_selection.py" ".trae/skills/quant-oral-to-code/scripts/test_spec_builder.py" ".trae/skills/quant-oral-to-code/scripts/test_guardrails.py" ".trae/skills/quant-oral-to-code/scripts/test_data_required_cutoff.py" ".trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py" ".trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py" ".trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py" ".trae/skills/quant-oral-to-code/scripts/test_protocol_replay.py" ".trae/skills/quant-oral-to-code/scripts/test_result_summary.py" ".trae/skills/quant-oral-to-code/scripts/test_artifact_manifest.py" -q
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" ".trae/skills/quant-oral-to-code/scripts/run_full_validation.py"
```

Expected: PASS；`ma_demo`、`chanlun_demo`、`liangxue_demo` 生成完整工作区；`ambiguous_demo`、`bad_csv_demo` 只生成 cutoff 产物；所有可运行工作区都使用只读 DuckDB 与统一协议。

### Override Matrix

执行时如果需要参考后面的旧细化草稿，必须先应用以下覆盖规则：

- 对旧 `Task 2`：
  - `resolve_repo_root()` 必须使用向上查找仓库哨兵目录的方法，不能再用 `parents[3]`
  - `check_runtime_capabilities()` 必须把 `duckdb` 放入硬依赖
  - `data_contract.json` 必须包含 `bars_table_name`、`required_tables`、`required_columns`、`primary_key`、`data_hash`
- 对旧 `Task 2.5`：
  - `generate_data_fetcher()` 不允许在 `data_required_cutoff` 分支下生成 runnable fetcher
  - 所有 fetcher 都必须真正调用 `normalize_to_duckdb()` 写入 `market.duckdb`
- 对旧 `Task 3`：
  - 必须同时生成 `translation_trace.json`，不能只生成 `strategy_spec.json`
- 对旧 `Task 4`：
  - `build_claim_report()` 必须消费 `guardrail_review`，且 blocking 触发后只能产出 cutoff 产物
- 对旧 `Task 5` 与 `Task 6`：
  - `resolve_codegen_mode()` 的输出必须真正影响 `generate_strategy_code()`
  - 生成的 `strategy.py` 必须是自包含实现，禁止 `engine.strategy_base`
- 对旧 `Task 7` 与 `Task 7.5`：
  - `run_backtest.py` 必须使用 `duckdb.connect(..., read_only=True)`
  - `experiment_protocol.json` 必须使用本计划定义的统一 schema，不再复用旧 draft 的 `sample_split` 形状
  - 必须存在真实 replay 测试，而不是只断言字段存在
- 对旧 `Task 8`：
  - `result_summary.md` 与 `artifact_manifest.json` 必须同时落盘，并带 `claim_level`
- 对旧 `Task 9`：
  - `run_full_validation.py` 必须是唯一端到端入口
  - 必须覆盖 `demo_only`、`portable_backtest`、`data_required_cutoff` 三条路径
  - `ambiguous_demo` / `bad_csv_demo` 严禁生成 runnable runner

### Task 1: 建立代码生成型 skill 骨架

**Files:**
- Create: `.trae/skills/quant-oral-to-code/SKILL.md`
- Create: `.trae/skills/quant-oral-to-code/modules/intake.md`
- Create: `.trae/skills/quant-oral-to-code/modules/dsl.md`
- Create: `.trae/skills/quant-oral-to-code/modules/guardrails.md`
- Create: `.trae/skills/quant-oral-to-code/modules/codegen.md`
- Create: `.trae/skills/quant-oral-to-code/modules/report.md`
- Create: `.trae/skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_skill_layout.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_codegen_skill_layout_has_required_modules():
    required = [
        ROOT / "SKILL.md",
        ROOT / "modules" / "dsl.md",
        ROOT / "modules" / "guardrails.md",
        ROOT / "modules" / "codegen.md",
        ROOT / "modules" / "report.md",
        ROOT / "scripts" / "validate_quant_oral_to_code.py",
    ]
    missing = [str(path) for path in required if not path.exists()]
    assert not missing, f"missing files: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_skill_layout.py::test_codegen_skill_layout_has_required_modules" -q
```

Expected: FAIL with missing file errors.

- [ ] **Step 3: Write minimal implementation**

```markdown
---
name: "quant-oral-to-code"
description: "把抽象语言直接转换成可回测策略代码、回测入口和结果报告，并自动规避前视、过拟合、样本外缺失、乐观成交等坑。Invoke when 用户说‘把这个想法直接写成可回测策略代码’、‘我不懂量化但想要完整策略代码’、‘帮我自动避开量化常见坑’。"
---

# quant-oral-to-code

先抽取 DSL，再做坑位审查，再直接生成策略代码与回测脚本。
```

```python
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    required = [
        ROOT / "SKILL.md",
        ROOT / "modules" / "dsl.md",
        ROOT / "modules" / "guardrails.md",
        ROOT / "modules" / "codegen.md",
        ROOT / "modules" / "report.md",
    ]
    missing = [str(path) for path in required if not path.exists()]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_skill_layout.py::test_codegen_skill_layout_has_required_modules" -q
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" ".trae/skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code
git commit -m "feat: scaffold direct strategy codegen skill"
```

## Legacy Draft Tasks (Deprecated)

以下旧 Task 2-9 草稿保留仅供历史对照，**不要执行**。真正可实施的任务序列在前面的 `Authoritative Rewrite`。

### Task 2: 实现环境能力检查、数据画像识别、数据契约与 demo 降级路径

**Files:**
- Create: `.trae/skills/quant-oral-to-code/modules/preflight.md`
- Create: `.trae/skills/quant-oral-to-code/modules/data.md`
- Create: `.trae/skills/quant-oral-to-code/modules/onboarding.md`
- Create: `.trae/skills/quant-oral-to-code/references/data_provider_matrix.json`
- Create: `.trae/skills/quant-oral-to-code/references/novice_glossary.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/preflight_report.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/data_profile.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/data_contract.schema.json`
- Create: `.trae/skills/quant-oral-to-code/templates/portable_csv_loader.py.tmpl`（负责把 CSV/Parquet/JSON 导入 `market.duckdb`）
- Create: `.trae/skills/quant-oral-to-code/templates/sample_ohlcv.csv`
- Create: `.trae/skills/quant-oral-to-code/scripts/check_runtime_capabilities.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/detect_data_profile.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/validate_fetched_dataset.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/build_demo_dataset.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/render_beginner_readme.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_preflight.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_profile.py`

- [ ] **Step 1: Write the failing test**

```python
from check_runtime_capabilities import check_runtime_capabilities
from detect_data_profile import detect_data_profile


def test_preflight_and_data_profile_support_demo_and_csv_modes(tmp_path):
    preflight = check_runtime_capabilities()
    profile = detect_data_profile(tmp_path)
    assert "python_ok" in preflight
    assert profile["mode"] in {"demo_mode", "portable_csv_mode", "full_research_mode"}
    assert "data_readiness" in profile
    assert "required_columns" in profile
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_preflight.py::test_preflight_and_data_profile_support_demo_and_csv_modes" -q
```

Expected: FAIL because preflight/data-profile scripts do not exist.

- [ ] **Step 3: Write minimal implementation**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "preflight_report",
  "type": "object",
  "required": ["python_ok", "quant_strategy_available", "chanlun_project_available", "recommended_mode"]
}
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "data_profile",
  "type": "object",
  "required": ["mode", "inputs", "is_research_grade", "data_readiness", "required_columns", "issues"]
}
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "data_contract",
  "type": "object",
  "required": [
    "required_columns",
    "supported_frequencies",
    "adjustment_mode",
    "minimum_rows",
    "storage_format",
    "storage_target",
    "table_layout",
    "write_disposition",
    "raw_input_format"
  ],
  "properties": {
    "storage_format": {"const": "duckdb"},
    "storage_target": {"type": "string", "pattern": ".*\\.duckdb$"}
  }
}
```

```python
from pathlib import Path


def check_runtime_capabilities() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    quant_runner = repo_root / ".trae" / "skills" / "quant-strategy" / "scripts" / "quant_runner.py"
    chanlun_root = repo_root / "_projects" / "projects" / "缠解天机" / "scripts" / "chanlun_compute.py"
    quant_ok = quant_runner.exists()
    chanlun_ok = chanlun_root.exists()
    recommended = "full_research_mode" if quant_ok or chanlun_ok else "demo_mode"
    return {
        "python_ok": True,
        "quant_strategy_available": quant_ok,
        "chanlun_project_available": chanlun_ok,
        "recommended_mode": recommended,
        "repair_commands": [
            "pip install -U pytest jsonschema pandas",
            "检查 generated_strategies 目录是否可写"
        ],
    }
```

```python
from pathlib import Path


def detect_data_profile(workspace: Path) -> dict:
    csv_files = list(workspace.glob("*.csv"))
    if csv_files:
        return {
            "mode": "portable_csv_mode",
            "inputs": [str(path) for path in csv_files],
            "is_research_grade": False,
            "data_readiness": "needs_column_validation",
            "required_columns": ["trade_date", "open", "high", "low", "close", "vol"],
            "issues": [],
        }
    return {
        "mode": "demo_mode",
        "inputs": [],
        "is_research_grade": False,
        "data_readiness": "demo_only",
        "required_columns": ["trade_date", "open", "high", "low", "close", "vol"],
        "issues": ["no_real_market_data"],
    }
```

```python
from pathlib import Path
import csv


def build_demo_dataset(output_path: Path) -> None:
    rows = [
        ["trade_date", "open", "high", "low", "close", "vol"],
        ["2024-01-02", 10.0, 10.3, 9.9, 10.2, 100000],
        ["2024-01-03", 10.2, 10.4, 10.1, 10.3, 105000],
        ["2024-01-04", 10.3, 10.6, 10.2, 10.5, 120000],
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
```

```python
def validate_fetched_dataset(profile: dict) -> dict:
    issues = list(profile.get("issues", []))
    readiness = profile.get("data_readiness", "unknown")
    return {
        "ok": readiness in {"portable_ready", "research_ready"},
        "readiness": readiness,
        "issues": issues,
        "next_action": "补齐列映射和数据质量后再进入真实回测" if readiness != "portable_ready" else "可以继续生成回测入口",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_preflight.py::test_preflight_and_data_profile_support_demo_and_csv_modes" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/modules/preflight.md .trae/skills/quant-oral-to-code/modules/data.md .trae/skills/quant-oral-to-code/modules/onboarding.md .trae/skills/quant-oral-to-code/references/data_provider_matrix.json .trae/skills/quant-oral-to-code/references/novice_glossary.json .trae/skills/quant-oral-to-code/schemas/preflight_report.schema.json .trae/skills/quant-oral-to-code/schemas/data_profile.schema.json .trae/skills/quant-oral-to-code/schemas/data_contract.schema.json .trae/skills/quant-oral-to-code/templates/portable_csv_loader.py.tmpl .trae/skills/quant-oral-to-code/templates/sample_ohlcv.csv .trae/skills/quant-oral-to-code/scripts/check_runtime_capabilities.py .trae/skills/quant-oral-to-code/scripts/detect_data_profile.py .trae/skills/quant-oral-to-code/scripts/validate_fetched_dataset.py .trae/skills/quant-oral-to-code/scripts/build_demo_dataset.py .trae/skills/quant-oral-to-code/scripts/render_beginner_readme.py .trae/skills/quant-oral-to-code/scripts/test_preflight.py .trae/skills/quant-oral-to-code/scripts/test_data_profile.py
git commit -m "feat: add runtime preflight and portable data profiles"
```

### Task 2.5: 实现 A 股数据源选择、获取代码生成与 `DATA_REQUIRED` 截断策略

**Files:**
- Create: `.trae/skills/quant-oral-to-code/references/data_access_matrix.json`
- Create: `.trae/skills/quant-oral-to-code/references/a_share_provider_notes.md`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_akshare.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_efinance.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_adata.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_baostock.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_tushare.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_jqdatasdk.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_easyquotation.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/fetch_with_ashare.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/select_data_provider.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_data_fetcher.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_provider_selection.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_data_fetcher_codegen.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from select_data_provider import select_data_provider
from generate_data_fetcher import generate_data_fetcher


def test_provider_selection_prefers_no_auth_then_auth_then_manual(tmp_path: Path):
    no_data_context = {
        "mode": "demo_mode",
        "needs_history_bars": True,
        "user_can_register_account": False,
        "user_prefers_zero_setup": True,
    }
    provider = select_data_provider(no_data_context)
    assert provider["provider"] == "akshare"
    assert provider["tier"] == "tier_a_no_auth"

    token_context = {
        "mode": "demo_mode",
        "needs_history_bars": True,
        "user_can_register_account": True,
        "user_prefers_zero_setup": False,
    }
    provider2 = select_data_provider(token_context)
    assert provider2["provider"] in {"tushare", "jqdatasdk", "akshare"}

    out = generate_data_fetcher(provider, tmp_path, symbol="000001")
    assert (tmp_path / "data" / "fetch_data.py").exists()
    assert (tmp_path / "data" / "provider_setup.md").exists()
    assert out["storage_format"] == "duckdb"
    assert out["storage_target"].endswith("data/normalized/market.duckdb")
    assert out["decision"] in {"generated_fetcher", "data_required_cutoff"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_data_provider_selection.py::test_provider_selection_prefers_no_auth_then_auth_then_manual" -q
```

Expected: FAIL because provider selector and fetcher generator do not exist.

- [ ] **Step 3: Write minimal implementation**

```json
{
  "providers": [
    {"name": "akshare", "tier": "tier_a_no_auth", "auth": "none", "supports_history": true, "supports_intraday": true, "supports_research_claim": false, "notes": "优先新手快速拉取 A 股历史行情"},
    {"name": "efinance", "tier": "tier_a_no_auth", "auth": "none", "supports_history": true, "supports_intraday": true, "supports_research_claim": false, "notes": "适合股票/ETF/资金流等东财系数据"},
    {"name": "adata", "tier": "tier_a_no_auth", "auth": "none", "supports_history": true, "supports_intraday": true, "supports_research_claim": false, "notes": "多数据源融合，支持代理设置"},
    {"name": "baostock", "tier": "tier_a_no_auth", "auth": "anonymous", "supports_history": true, "supports_intraday": false, "supports_research_claim": false, "notes": "匿名登录，适合日周月线和基础财务补充"},
    {"name": "tushare", "tier": "tier_b_auth_or_trial", "auth": "token", "supports_history": true, "supports_intraday": true, "supports_research_claim": true, "notes": "需注册 token，部分能力依赖 Pro"},
    {"name": "jqdatasdk", "tier": "tier_b_auth_or_trial", "auth": "username_password", "supports_history": true, "supports_intraday": true, "supports_research_claim": true, "notes": "需登录认证或申请试用"},
    {"name": "easyquotation", "tier": "tier_c_snapshot_only", "auth": "none", "supports_history": false, "supports_intraday": true, "supports_research_claim": false, "notes": "适合实时快照，不默认做研究级历史回测主源"},
    {"name": "ashare", "tier": "tier_c_snapshot_only", "auth": "none", "supports_history": true, "supports_intraday": true, "supports_research_claim": false, "notes": "极简单文件接口，适合作为轻量补数备选"}
  ]
}
```

```python
def select_data_provider(context: dict) -> dict:
    if context.get("needs_history_bars") and context.get("user_prefers_zero_setup"):
        return {"provider": "akshare", "tier": "tier_a_no_auth", "decision": "generated_fetcher"}
    if context.get("needs_history_bars") and context.get("user_can_register_account"):
        return {"provider": "tushare", "tier": "tier_b_auth_or_trial", "decision": "generated_fetcher"}
    return {"provider": "manual_csv", "tier": "tier_d_manual_csv", "decision": "data_required_cutoff"}
```

```python
from pathlib import Path


def generate_data_fetcher(provider: dict, output_dir: Path, symbol: str) -> dict:
    data_dir = output_dir / "data"
    normalized_dir = data_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    decision = provider.get("decision", "generated_fetcher")
    fetch_file = data_dir / "fetch_data.py"
    setup_file = data_dir / "provider_setup.md"
    storage_target = normalized_dir / "market.duckdb"
    fetch_file.write_text(
        f"""# generated data fetcher
PROVIDER = '{provider['provider']}'
SYMBOL = '{symbol}'
STORAGE_FORMAT = 'duckdb'
DUCKDB_PATH = 'data/normalized/market.duckdb'

# TODO: fetch raw market data, normalize columns, then write into DUCKDB_PATH
""",
        encoding="utf-8",
    )
    setup_file.write_text(
        f"""# Provider Setup

- provider: {provider['provider']}
- tier: {provider['tier']}
- decision: {decision}
- storage_format: duckdb
- storage_target: data/normalized/market.duckdb
""",
        encoding="utf-8",
    )
    return {
        "decision": decision,
        "fetch_file": str(fetch_file),
        "setup_file": str(setup_file),
        "storage_format": "duckdb",
        "storage_target": str(storage_target).replace("\\\\", "/"),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_data_provider_selection.py::test_provider_selection_prefers_no_auth_then_auth_then_manual" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/references/data_access_matrix.json .trae/skills/quant-oral-to-code/references/a_share_provider_notes.md .trae/skills/quant-oral-to-code/templates/fetch_with_akshare.py.tmpl .trae/skills/quant-oral-to-code/templates/fetch_with_efinance.py.tmpl .trae/skills/quant-oral-to-code/templates/fetch_with_adata.py.tmpl .trae/skills/quant-oral-to-code/templates/fetch_with_baostock.py.tmpl .trae/skills/quant-oral-to-code/templates/fetch_with_tushare.py.tmpl .trae/skills/quant-oral-to-code/templates/fetch_with_jqdatasdk.py.tmpl .trae/skills/quant-oral-to-code/templates/fetch_with_easyquotation.py.tmpl .trae/skills/quant-oral-to-code/templates/fetch_with_ashare.py.tmpl .trae/skills/quant-oral-to-code/scripts/select_data_provider.py .trae/skills/quant-oral-to-code/scripts/generate_data_fetcher.py .trae/skills/quant-oral-to-code/scripts/test_data_provider_selection.py .trae/skills/quant-oral-to-code/scripts/test_data_fetcher_codegen.py
git commit -m "feat: add ashare data provider routing and fetcher generation"
```

### Task 3: 实现策略 DSL/AST 生成器

**Files:**
- Create: `.trae/skills/quant-oral-to-code/schemas/strategy_spec.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/translation_trace.schema.json`
- Create: `.trae/skills/quant-oral-to-code/references/domain_ontology.json`
- Create: `.trae/skills/quant-oral-to-code/scripts/build_strategy_spec.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_spec_builder.py`

- [ ] **Step 1: Write the failing test**

```python
from build_strategy_spec import build_strategy_spec


def test_strategy_spec_extracts_entry_exit_risk_and_output_requirements():
    prompt = "A股日线，5日均线上穿20日均线买入，跌破20日均线卖出，单票回测，帮我输出收益曲线和最大回撤。"
    spec = build_strategy_spec(prompt)
    assert spec["strategy_family"] == "trend_basic"
    assert spec["entry_rules"]
    assert spec["exit_rules"]
    assert spec["output_requirements"]["equity_curve"] is True
    assert spec["output_requirements"]["drawdown"] is True
    assert spec["translation_trace"]
    assert "translation_confidence" in spec
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_spec_builder.py::test_strategy_spec_extracts_entry_exit_risk_and_output_requirements" -q
```

Expected: FAIL because spec builder does not exist.

- [ ] **Step 3: Write minimal implementation**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "strategy_spec",
  "type": "object",
  "required": [
    "strategy_family",
    "market",
    "timeframe",
    "entry_rules",
    "exit_rules",
    "risk_rules",
    "output_requirements",
    "translation_trace",
    "translation_confidence",
    "unresolved_terms",
    "implicit_defaults"
  ]
}
```

```python
KNOWN_FAMILIES = {
    "chanlun": ["三买", "三卖", "背驰", "中枢", "级别"],
    "liangxue": ["倍量过左峰", "精准线", "黄金线", "倍量柱"],
    "trend_basic": ["均线", "金叉", "死叉"],
}


def build_strategy_spec(prompt: str) -> dict:
    text = prompt.strip()
    family = "unknown"
    for name, terms in KNOWN_FAMILIES.items():
        if any(term in text for term in terms):
            family = name
            break
    return {
        "strategy_family": family,
        "market": "A股" if "A股" in text else "unknown",
        "timeframe": "日线" if "日线" in text else ("多级别" if "级别" in text else "unknown"),
        "entry_rules": ["5日均线上穿20日均线"] if "上穿20日均线" in text or "金叉" in text else [],
        "exit_rules": ["跌破20日均线卖出"] if "跌破20日均线" in text or "死叉" in text else [],
        "risk_rules": [],
        "output_requirements": {
            "equity_curve": "收益曲线" in text,
            "drawdown": "回撤" in text,
        },
        "translation_trace": [
            {"source_text": text, "target_field": "strategy_family", "confidence": 0.8, "reason": "关键词命中"}
        ],
        "translation_confidence": 0.8,
        "unresolved_terms": [],
        "implicit_defaults": ["execution_mode=next_open", "claim_level_ceiling=portable_backtest"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_spec_builder.py::test_strategy_spec_extracts_entry_exit_risk_and_output_requirements" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/schemas/strategy_spec.schema.json .trae/skills/quant-oral-to-code/schemas/translation_trace.schema.json .trae/skills/quant-oral-to-code/references/domain_ontology.json .trae/skills/quant-oral-to-code/scripts/build_strategy_spec.py .trae/skills/quant-oral-to-code/scripts/test_spec_builder.py
git commit -m "feat: build strategy dsl from abstract language"
```

### Task 4: 实现量化坑位审查器

**Files:**
- Create: `.trae/skills/quant-oral-to-code/schemas/guardrail_review.schema.json`
- Create: `.trae/skills/quant-oral-to-code/references/guardrail_rules.json`
- Create: `.trae/skills/quant-oral-to-code/scripts/review_guardrails.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_guardrails.py`

- [ ] **Step 1: Write the failing test**

```python
from review_guardrails import review_guardrails


def test_guardrails_flag_lookahead_overfit_and_optimistic_execution():
    spec = {
        "strategy_family": "trend_basic",
        "factor_requirements": {"uses_financial_data": True, "pit_checked": False},
        "validation_requirements": {"optimized_on_full_sample": True, "has_holdout": False},
        "execution_requirements": {"execution_mode": "same_bar_close"},
        "universe_requirements": {"dynamic_pool": True, "historical_pool_method": None},
        "translation_confidence": 0.45,
        "unresolved_terms": ["强势", "放量确认"],
    }
    review = review_guardrails(spec)
    assert "financial_factor_without_pit_visibility" in review["blocking"]
    assert "full_sample_optimization_without_holdout" in review["blocking"]
    assert "dynamic_stock_pool_without_historical_pool_method" in review["blocking"]
    assert "low_translation_confidence" in review["blocking"]
    assert "same_bar_close_is_optimistic" in review["warnings"]
    assert review["decision"] in {"blocked", "downgraded"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_guardrails.py::test_guardrails_flag_lookahead_overfit_and_optimistic_execution" -q
```

Expected: FAIL because guardrail review does not exist.

- [ ] **Step 3: Write minimal implementation**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "guardrail_review",
  "type": "object",
  "required": ["blocking", "warnings", "novice_explanation", "decision", "claim_level_ceiling"]
}
```

```python
def review_guardrails(spec: dict) -> dict:
    blocking = []
    warnings = []
    if spec.get("factor_requirements", {}).get("uses_financial_data") and not spec.get("factor_requirements", {}).get("pit_checked"):
        blocking.append("financial_factor_without_pit_visibility")
    if spec.get("validation_requirements", {}).get("optimized_on_full_sample") and not spec.get("validation_requirements", {}).get("has_holdout"):
        blocking.append("full_sample_optimization_without_holdout")
    if spec.get("universe_requirements", {}).get("dynamic_pool") and not spec.get("universe_requirements", {}).get("historical_pool_method"):
        blocking.append("dynamic_stock_pool_without_historical_pool_method")
    if spec.get("execution_requirements", {}).get("execution_mode") == "same_bar_close":
        warnings.append("same_bar_close_is_optimistic")
    if spec.get("translation_confidence", 1.0) < 0.6:
        blocking.append("low_translation_confidence")
    return {
        "blocking": blocking,
        "warnings": warnings,
        "novice_explanation": "若存在 blocking，这套代码不能直接交付为可信回测策略。",
        "decision": "blocked" if blocking else ("downgraded" if warnings else "pass"),
        "claim_level_ceiling": "demo_only" if blocking else "portable_backtest",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_guardrails.py::test_guardrails_flag_lookahead_overfit_and_optimistic_execution" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/schemas/guardrail_review.schema.json .trae/skills/quant-oral-to-code/references/guardrail_rules.json .trae/skills/quant-oral-to-code/scripts/review_guardrails.py .trae/skills/quant-oral-to-code/scripts/test_guardrails.py
git commit -m "feat: add quant codegen guardrails"
```

### Task 5: 实现代码生成模式解析器

**Files:**
- Create: `.trae/skills/quant-oral-to-code/references/example_registry.json`
- Create: `.trae/skills/quant-oral-to-code/scripts/resolve_codegen_mode.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py`

- [ ] **Step 1: Write the failing test**

```python
from resolve_codegen_mode import resolve_codegen_mode


def test_codegen_mode_distinguishes_builtin_and_chanlun_generation():
    ma_spec = {"strategy_family": "trend_basic"}
    chanlun_spec = {"strategy_family": "chanlun"}
    liangxue_spec = {"strategy_family": "liangxue"}
    assert resolve_codegen_mode(ma_spec)["mode"] == "quant_builtin_generated"
    assert resolve_codegen_mode(chanlun_spec)["mode"] == "chanlun_project_generated"
    assert resolve_codegen_mode(liangxue_spec)["mode"] == "quant_builtin_generated"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py::test_codegen_mode_distinguishes_builtin_and_chanlun_generation" -q
```

Expected: FAIL because mode resolver does not exist.

- [ ] **Step 3: Write minimal implementation**

```json
{
  "examples": [
    {"family": "chanlun", "role": "dsl_and_rule_translation"},
    {"family": "liangxue", "role": "rule_translation_and_guardrail_counterexample"},
    {"family": "trend_basic", "role": "simple_builtin_codegen"}
  ]
}
```

```python
def resolve_codegen_mode(spec: dict) -> dict:
    family = spec.get("strategy_family")
    if family == "chanlun":
        return {"mode": "chanlun_project_generated"}
    if family in {"liangxue", "trend_basic"}:
        return {"mode": "quant_builtin_generated"}
    return {"mode": "blocked"}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py::test_codegen_mode_distinguishes_builtin_and_chanlun_generation" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/references/example_registry.json .trae/skills/quant-oral-to-code/scripts/resolve_codegen_mode.py .trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py
git commit -m "feat: resolve strategy codegen modes"
```

### Task 6: 直接生成策略代码文件

**Files:**
- Create: `.trae/skills/quant-oral-to-code/templates/single_asset_strategy.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/portfolio_strategy.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_strategy_code.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from generate_strategy_code import generate_strategy_code


def test_generate_strategy_code_writes_python_strategy(tmp_path: Path):
    spec = {
        "strategy_family": "trend_basic",
        "strategy_name": "ma_demo",
        "entry_rules": ["5日均线上穿20日均线"],
        "exit_rules": ["跌破20日均线卖出"],
    }
    mode = {"mode": "quant_builtin_generated"}
    out = generate_strategy_code(spec, mode, tmp_path)
    path = Path(out["strategy_file"])
    assert path.exists()
    assert path.read_text(encoding="utf-8").find("class MaDemoStrategy") >= 0
    assert "D:\\tool\\novel" not in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py::test_generate_strategy_code_writes_python_strategy" -q
```

Expected: FAIL because generator does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path


def _class_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_")) + "Strategy"


def generate_strategy_code(spec: dict, mode: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    strategy_name = spec.get("strategy_name", "generated_strategy")
    class_name = _class_name(strategy_name)
    strategy_file = output_dir / "strategy.py"
    strategy_file.write_text(
        f"""from engine.strategy_base import StrategyBase
import pandas as pd


class {class_name}(StrategyBase):
    version = "0.1.0"

    def __init__(self, **params):
        super().__init__()
        self.params = params

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 0
        return df
""",
        encoding="utf-8",
    )
    return {"strategy_file": str(strategy_file), "class_name": class_name}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py::test_generate_strategy_code_writes_python_strategy" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/templates/single_asset_strategy.py.tmpl .trae/skills/quant-oral-to-code/templates/portfolio_strategy.py.tmpl .trae/skills/quant-oral-to-code/scripts/generate_strategy_code.py .trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py
git commit -m "feat: generate backtestable strategy code"
```

### Task 7: 生成回测入口脚本、实验协议与 smoke test

**Files:**
- Create: `.trae/skills/quant-oral-to-code/templates/run_backtest.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/templates/test_strategy_smoke.py.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_backtest_runner.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/generate_strategy_tests.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from generate_backtest_runner import generate_backtest_runner
from generate_strategy_tests import generate_strategy_tests


def test_backtest_runner_and_smoke_test_are_generated(tmp_path: Path):
    spec = {"market": "A股", "timeframe": "日线", "strategy_name": "ma_demo"}
    runner = generate_backtest_runner(spec, tmp_path)
    tests = generate_strategy_tests(spec, tmp_path)
    assert Path(runner["runner_file"]).exists()
    assert Path(runner["protocol_file"]).exists()
    assert Path(tests["test_file"]).exists()
    runner_text = Path(runner["runner_file"]).read_text(encoding="utf-8")
    assert "D:\\tool\\novel" not in runner_text
    assert "market.duckdb" in runner_text
    assert "read_csv" not in runner_text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py::test_backtest_runner_and_smoke_test_are_generated" -q
```

Expected: FAIL because generators do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path


def generate_backtest_runner(spec: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    runner_file = output_dir / "run_backtest.py"
    protocol_file = output_dir / "experiment_protocol.json"
    runner_file.write_text(
        """import json
from pathlib import Path
import duckdb


def main():
    db_path = Path("data/normalized/market.duckdb")
    if not db_path.exists():
        raise FileNotFoundError(f"missing normalized DuckDB dataset: {db_path}")
    con = duckdb.connect(str(db_path))
    bars = con.execute("select * from bars limit 10").fetchdf()
    result = {"status": "dry_run", "note": "replace with real backtest invocation"}
    Path("results").mkdir(exist_ok=True)
    Path("results/metrics_snapshot.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
""",
        encoding="utf-8",
    )
    protocol_file.write_text(
        "{\"sample_split\": {\"train\": \"2018-01-01/2022-12-31\", \"test\": \"2023-01-01/2024-12-31\"}, \"execution\": {\"mode\": \"next_open\"}}",
        encoding="utf-8",
    )
    return {"runner_file": str(runner_file), "protocol_file": str(protocol_file)}
```

```python
from pathlib import Path


def generate_strategy_tests(spec: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    test_file = output_dir / "test_strategy_smoke.py"
    test_file.write_text(
        """from pathlib import Path


def test_generated_strategy_files_exist():
    assert Path("strategy.py").exists()
    assert Path("run_backtest.py").exists()
""",
        encoding="utf-8",
    )
    return {"test_file": str(test_file)}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py::test_backtest_runner_and_smoke_test_are_generated" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/templates/run_backtest.py.tmpl .trae/skills/quant-oral-to-code/templates/test_strategy_smoke.py.tmpl .trae/skills/quant-oral-to-code/scripts/generate_backtest_runner.py .trae/skills/quant-oral-to-code/scripts/generate_strategy_tests.py .trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py
git commit -m "feat: generate backtest runners and smoke tests"
```

### Task 7.5: 接线研究级验证、协议回放与 provenance

**Files:**
- Modify: `.trae/skills/quant-oral-to-code/scripts/generate_backtest_runner.py`
- Modify: `.trae/skills/quant-oral-to-code/scripts/run_full_validation.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_protocol_roundtrip.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import json


def test_experiment_protocol_roundtrip_contains_sample_split_costs_and_execution(tmp_path: Path):
    protocol_path = tmp_path / "experiment_protocol.json"
    protocol_path.write_text(
        json.dumps(
            {
                "sample_split": {"train": "2018-01-01/2022-12-31", "test": "2023-01-01/2024-12-31"},
                "costs": {"commission_bps": 8, "slippage_bps": 10},
                "execution": {"mode": "next_open"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    assert "sample_split" in protocol
    assert "costs" in protocol
    assert "execution" in protocol
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_protocol_roundtrip.py::test_experiment_protocol_roundtrip_contains_sample_split_costs_and_execution" -q
```

Expected: FAIL somewhere in the main chain before protocol and归档逻辑被正式接入。

- [ ] **Step 3: Write minimal implementation**

```python
# run_full_validation.py 至少要校验这些协议级字段：
REQUIRED_PROTOCOL_KEYS = [
    "sample_split",
    "costs",
    "execution",
]
```

```text
研究级验证接线要求：
- 非 demo_mode 必须生成 experiment_protocol.json
- research_grade_local 必须归档 sample_split、cost_sensitivity、parameter_stability、guardrail_report
- 所有结果必须带 prompt/spec/code/data hash 与模板版本
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_protocol_roundtrip.py::test_experiment_protocol_roundtrip_contains_sample_split_costs_and_execution" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/scripts/generate_backtest_runner.py .trae/skills/quant-oral-to-code/scripts/run_full_validation.py .trae/skills/quant-oral-to-code/scripts/test_protocol_roundtrip.py
git commit -m "feat: wire protocol roundtrip and research validation gates"
```

### Task 8: 生成收益曲线/回撤摘要与产物清单

**Files:**
- Create: `.trae/skills/quant-oral-to-code/schemas/claim_report.schema.json`
- Create: `.trae/skills/quant-oral-to-code/schemas/generated_artifact_manifest.schema.json`
- Create: `.trae/skills/quant-oral-to-code/templates/result_summary.md.tmpl`
- Create: `.trae/skills/quant-oral-to-code/scripts/summarize_quant_result.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/test_result_summary.py`

- [ ] **Step 1: Write the failing test**

```python
from summarize_quant_result import summarize_quant_result


def test_result_summary_mentions_equity_curve_drawdown_and_plain_language_warning():
    result = {
        "main_backtest": {"summary": {"total_return": 0.21, "max_drawdown": -0.12, "sharpe_ratio": 1.1}},
        "equity_curve_path": "generated_strategies/ma_demo/results/equity_curve.png",
        "guardrail_review": {"blocking": [], "warnings": ["same_bar_close_is_optimistic"]},
        "claim_report": {"claim_level": "portable_backtest", "decision": "downgraded"},
    }
    text = summarize_quant_result(result)
    assert "收益曲线" in text
    assert "最大回撤" in text
    assert "Sharpe" in text
    assert "可信度" in text
    assert "portable_backtest" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_result_summary.py::test_result_summary_mentions_equity_curve_drawdown_and_plain_language_warning" -q
```

Expected: FAIL because summarizer does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def summarize_quant_result(result: dict) -> str:
    summary = result.get("main_backtest", {}).get("summary", {})
    warnings = result.get("guardrail_review", {}).get("warnings", [])
    claim = result.get("claim_report", {})
    return f"""# 结果摘要

- 收益曲线：{result.get('equity_curve_path', '未提供')}
- 总收益：{summary.get('total_return', 'N/A')}
- 最大回撤：{summary.get('max_drawdown', 'N/A')}
- Sharpe：{summary.get('sharpe_ratio', 'N/A')}
- 可信度：{claim.get('claim_level', 'unknown')}
- 决策：{claim.get('decision', 'unknown')}
- 告警：{', '.join(warnings)}

注意：这些结果需要结合 claim level、数据来源和护栏审查一起理解，不等于可以直接实盘。
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_result_summary.py::test_result_summary_mentions_equity_curve_drawdown_and_plain_language_warning" -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code/schemas/claim_report.schema.json .trae/skills/quant-oral-to-code/schemas/generated_artifact_manifest.schema.json .trae/skills/quant-oral-to-code/templates/result_summary.md.tmpl .trae/skills/quant-oral-to-code/scripts/summarize_quant_result.py .trae/skills/quant-oral-to-code/scripts/test_result_summary.py
git commit -m "feat: summarize generated strategy outputs"
```

### Task 9: 用缠论/量学做 grounded eval，并跑全链路 dry-run

**Files:**
- Create: `.trae/skills/quant-oral-to-code/examples/ma_beginner_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/chanlun_third_buy_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/liangxue_breakout_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/no_data_beginner_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/bad_csv_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/examples/unsupported_terms_prompt.md`
- Create: `.trae/skills/quant-oral-to-code/scripts/run_generated_strategy_smoke.py`
- Create: `.trae/skills/quant-oral-to-code/scripts/run_full_validation.py`
- Modify: `.trae/sync/CURRENT.md`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_generated_strategy_smoke_workspace_is_created(tmp_path: Path):
    workspace = tmp_path / "generated_strategies" / "ma_demo"
    workspace.mkdir(parents=True, exist_ok=True)
    assert workspace.exists()
    assert (workspace / "results").exists() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_skill_layout.py" -q
```

Expected: FAIL somewhere in the full chain before all files are wired together.

- [ ] **Step 3: Write minimal implementation**

```text
我不懂量化，但想把 5 日均线上穿 20 日均线这件事直接写成可回测策略代码，还要有收益曲线和最大回撤。
```

```text
高级别定方向，次级别找三买，低级别背驰确认，给我一套可跑的研究代码，不要前视。
```

```text
找倍量过左峰后回踩精准线再上去的票，直接帮我写成回测策略代码，但要避免过拟合。
```

```text
我只有一句很模糊的话：找最近看起来很强、放量确认、最好别回撤太大的票。你先别假装回测，告诉我缺什么数据和定义。
```

```text
我有一个列名乱掉的 CSV，但是想回测 A 股日线突破策略。你先帮我识别列映射，不行就告诉我怎么补数据，不要直接报完成。
```

```python
from pathlib import Path
import json

from build_strategy_spec import build_strategy_spec
from review_guardrails import review_guardrails
from resolve_codegen_mode import resolve_codegen_mode
from generate_strategy_code import generate_strategy_code
from generate_backtest_runner import generate_backtest_runner
from generate_strategy_tests import generate_strategy_tests


def run_prompt(prompt: str, slug: str) -> None:
    root = Path("generated_strategies") / slug
    root.mkdir(parents=True, exist_ok=True)
    spec = build_strategy_spec(prompt)
    spec["strategy_name"] = slug
    review = review_guardrails(spec)
    mode = resolve_codegen_mode(spec)
    (root / "strategy_spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "guardrail_review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    generate_strategy_code(spec, mode, root)
    generate_backtest_runner(spec, root)
    generate_strategy_tests(spec, root)


def main():
    run_prompt("我不懂量化，但想把 5 日均线上穿 20 日均线这件事直接写成可回测策略代码，还要有收益曲线和最大回撤。", "ma_demo")
    run_prompt("高级别定方向，次级别找三买，低级别背驰确认，给我一套可跑的研究代码，不要前视。", "chanlun_demo")
    run_prompt("找倍量过左峰后回踩精准线再上去的票，直接帮我写成回测策略代码，但要避免过拟合。", "liangxue_demo")
    run_prompt("我只有一句很模糊的话：找最近看起来很强、放量确认、最好别回撤太大的票。你先别假装回测，告诉我缺什么数据和定义。", "ambiguous_demo")
    run_prompt("我有一个列名乱掉的 CSV，但是想回测 A 股日线突破策略。你先帮我识别列映射，不行就告诉我怎么补数据，不要直接报完成。", "bad_csv_demo")


if __name__ == "__main__":
    main()
```

```text
Task: quant-oral-to-code direct codegen plan
Summary: 计划已改成“抽象语言直接生成可回测策略代码”的主线，含 DSL、guardrail、codegen、runner、summary。缠论和量学作为模板与反例库接入。
Next: 先执行 Task 1-5，打通从抽象语言到 strategy.py 的主链；再执行 Task 6-8，补回测脚本、结果摘要和 grounded eval。
Blockers: 无音频范围；任何存在前视/过拟合/历史股票池不清楚的策略都必须阻断或降级说明。
Focus Files:
- D:\tool\novel\docs\superpowers\plans\2026-06-22-quant-oral-to-code.md
- D:\tool\novel\_projects\projects\缠解天机\scripts\chanlun_compute.py
- D:\tool\novel\.trae\skills\quant-strategy\scripts\liangxue_core.py
```

- [ ] **Step 4: Run full verification**

Run:

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pytest ".trae/skills/quant-oral-to-code/scripts/test_skill_layout.py" ".trae/skills/quant-oral-to-code/scripts/test_spec_builder.py" ".trae/skills/quant-oral-to-code/scripts/test_guardrails.py" ".trae/skills/quant-oral-to-code/scripts/test_codegen_mode.py" ".trae/skills/quant-oral-to-code/scripts/test_strategy_codegen.py" ".trae/skills/quant-oral-to-code/scripts/test_runner_codegen.py" ".trae/skills/quant-oral-to-code/scripts/test_result_summary.py" -q
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" ".trae/skills/quant-oral-to-code/scripts/run_full_validation.py"
```

Expected: PASS；并在 `generated_strategies/ma_demo`、`generated_strategies/chanlun_demo`、`generated_strategies/liangxue_demo` 下看到生成代码与回测入口；并且 `ambiguous_demo` / `bad_csv_demo` 必须进入澄清或 `DATA_REQUIRED` 路径，而不是产出伪研究结果。

- [ ] **Step 5: Commit**

```bash
git add .trae/skills/quant-oral-to-code .trae/sync/CURRENT.md
git commit -m "feat: plan direct strategy code generation from abstract language"
```

## Post-Plan Notes

- 缠论更适合作为 `结构化 DSL + 规则翻译 + 风控表达` 的代码生成模板来源。
- 量学更适合作为 `规则翻译 + 模式识别` 的模板来源，同时必须保留 `liangzhu_liangxian_5y_study.py`、`liangxue_holdout_signal_validate.py`、`liangxue_layered_portfolio_validate.py` 作为过拟合/前视/过度外推反例。
- 对不懂量化的用户，系统默认使用保守执行：`next_open`、基础成本、holdout、样本外、成交约束。
- “能生成代码”不等于“代码可直接实盘”，所以结果摘要里必须带 plain-language 风险提醒。
- 本计划的主执行器已经固定为生成工作区内的自包含 runner；`quant-strategy`、缠论项目和量学脚本只作参考与研究对照，不再决定主协议与主数据面。
- 为了让 skill 能给陌生用户安装即用，必须把输出分成三档：
  - `demo_only`：无数据或仅 sample 数据，只证明代码可运行
  - `portable_backtest`：用户自带 CSV/Parquet，可得非研究级回测
  - `research_grade_local`：接入本地量化栈与数据后，才允许输出研究级结论
- 每个生成工作区都要附带 `README_beginner.md`，告诉用户：
  - 还缺什么环境或数据
  - 当前结果可信度属于哪一档
  - 下一步如何把 demo 升级到真实研究
- 生成器要优先使用“少依赖、少路径假设”的模板，避免默认绑死在你这台机器的目录结构上。
- A 股数据获取路线在实现时按这轮 GitHub 调研固化：
  - 默认优先：`AKShare`、`efinance`、`AData`、`baostock`
  - 注册或试用后可升级：`TuShare Pro`、`JQData SDK`
  - 只做快照或轻量兜底：`easyquotation`、`Ashare`
  - 再不行就退到 `manual_csv`，要求用户导出 CSV/Parquet，再走 `portable_csv_mode`
- skill 必须把“获取数据”当成主链的一部分，而不是失败后的随手建议：
  - 有条件就生成 `fetch_data.py`
  - 没条件就进入 `DATA_REQUIRED` 截断
  - 不能一边缺真实数据，一边给出看起来像正式回测的结果摘要
- 文档中存在一段 `Legacy Draft Tasks (Deprecated)` 历史草稿；实施、审阅和验收时都只认 `Authoritative Rewrite`。

## Self-Review Checklist

- Spec coverage:
  - 已覆盖“抽象语言 -> 代码 -> DuckDB 规范化 -> 自包含回测 -> 收益曲线/回撤摘要”的完整主链。
  - 已覆盖前视、过拟合、幸存者偏差和乐观执行假设这四类核心坑。
  - 已覆盖无数据用户、仅 CSV 用户、完整本地量化栈用户这三类画像。
  - 已覆盖 A 股数据获取、取数失败截断、坏 CSV 识别、模糊术语阻断这四类外部输入问题。
- Placeholder scan:
  - `Authoritative Rewrite` 中无 `TODO`、`TBD`、`implement later`。
  - 历史草稿里的占位内容已通过 `Legacy Draft Tasks (Deprecated)` 明确降级，不再作为执行依据。
  - 权威任务段都包含具体路径、测试命令和最小实现代码。
- Type consistency:
  - `strategy_spec -> translation_trace -> guardrail_review -> claim_report -> data_contract -> strategy.py -> run_backtest.py -> result_summary` 命名一致。
  - 计划的第一交付物已经从“规格包优先”纠正为“策略代码优先”。
  - `claim_level`、`DATA_REQUIRED`、`experiment_protocol.json`、`translation_trace.json` 在各任务中的语义一致。
