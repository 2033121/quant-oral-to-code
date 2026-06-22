# quant-oral-to-code

`quant-oral-to-code` 是一个面向量化初学者和通用智能体的 Agent Skill。

它的目标不是只输出“策略思路”，而是把抽象自然语言策略描述，尽可能翻译成一套可验证、可回测、带风险护栏的本地量化策略工作区。

主链如下：

`natural language -> strategy_spec -> translation_trace -> guardrails -> data profile/provider route -> DuckDB normalization -> data_contract -> claim_report -> strategy.py -> run_backtest.py -> result_summary`

## 适用场景

- 用户不会写量化代码，只会口述策略
- 希望自动生成可回测的策略代码，而不是只得到解释
- 希望尽量规避常见量化坑
  - 过拟合
  - 前视偏差
  - 没有样本外验证
  - 过度乐观的成交假设
  - 数据不完整却误判为“可回测”
- 希望输出常见量化结果
  - 收益曲线
  - 回撤
  - 收益汇总
  - 产物清单

## 仓库结构

```text
skills/
  quant-oral-to-code/
docs/
```

`skills/quant-oral-to-code/` 是 GitHub Agent Skills 兼容结构，可配合 `gh skill` 使用。

## 安装与使用

如果你使用 GitHub CLI 的 Agent Skills 预览能力：

```bash
gh skill install 2033121/quant-oral-to-code quant-oral-to-code
```

也可以直接克隆仓库后手动读取：

1. `skills/quant-oral-to-code/SKILL.md`
2. 按 `SKILL.md` 指定顺序读取 `modules/`
3. 使用 `schemas/` 校验结构化产物
4. 使用 `scripts/` 和 `templates/` 生成策略代码与回测入口

## 最小验证

```bash
python "skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
python "skills/quant-oral-to-code/scripts/run_full_validation.py"
```

## 数据标准

当前统一标准化为 DuckDB：

- 输出：`generated_strategies/<slug>/data/normalized/market.duckdb`
- 表名：`bars`
- 主键：`["symbol", "trade_date"]`

如果原始数据来自 CSV / Parquet / JSON / SQLite，也必须先标准化到 DuckDB，再进入统一回测链路。

## 数据不足时的行为

如果没有真实数据、字段映射不完整、关键列缺失或数据质量校验失败，skill 必须进入 `data_required_cutoff`，而不是伪装成完整回测已完成。

## 参考文档

- [实现计划](docs/2026-06-22-quant-oral-to-code.md)
- [A 股数据源研究](docs/2026-06-22-a-share-data-sources.md)

## License

MIT
