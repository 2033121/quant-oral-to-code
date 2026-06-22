# quant-oral-to-code 开源版口径与边界说明

更新时间：2026-06-22

## 文档目的

这份文档用于说明当前开源版的维护口径与边界，不再复用旧 `.trae` 私有路径、历史任务草稿或不存在文件作为当前实施依据。
若下游模块或参考文档与当前高层口径冲突，以本文件与 `README.md` 为准。

## 项目定位

- 本仓库提供的是面向自然语言量化策略描述的开源工作区骨架
- 当前重点是统一数据标准、验证方式和结果口径
- 文档应服务于规格审查与维护一致性，不展开超出本任务边界的执行链细节

## 最小依赖口径

当前根仓库没有 `pyproject.toml`，根目录保留 `requirements.txt` 作为最小依赖入口。

当前最小验证链路的硬依赖只有：

- `duckdb`
- `jsonschema`

`pandas` 不属于最小前提。它只属于部分可选取数模板或数据整理场景，应保持为可选依赖口径。

## 数据存储标准

- DuckDB 是唯一标准持久化格式
- 标准路径是 `generated_strategies/<slug>/data/normalized/market.duckdb`
- 标准表名是 `bars`
- 标准主键是 `["symbol", "trade_date"]`
- `csv / parquet / json / sqlite / provider api` 只能作为外部输入形态，进入统一链路前必须归一化到 DuckDB

## 数据不足时的口径

以下任一情况成立时，必须进入 `data_required_cutoff` 截断：

- 没有真实可用数据
- 字段映射无法闭合
- 关键列缺失
- 最小数据契约不满足

在这些情况下，不应把结果写成“已完成正式回测”。

## 验证方式与副作用边界

只读结构验证：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" "skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
```

全链路验证：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" "skills/quant-oral-to-code/scripts/run_full_validation.py"
```

维护口径必须继续明确：

- `run_full_validation.py` 不是“最小验证”
- `run_full_validation.py` 具有工作区副作用
- 它只处理 `CASES` 中固定示例 slug 的工作区
- 对进入 `data_required_cutoff` 截断的示例，只清理该工作区内预定义产物

## 结果口径边界

当前默认摘要只应保守表达以下内容：

- claim level
- decision
- guardrail 提示
- 动作计数
- 样本规模

当前默认摘要不应宣称以下内容为真实有效结论：

- 总收益
- 最大回撤
- Sharpe
- 真实权益曲线

只有在未来明确补齐真实 PnL / equity curve 证据链后，才允许升级这些表述。

## 维护注意事项

- 不要把旧 `.trae` 私有路径写成当前实施路径
- 不要把未明确接线的模板写成“当前主链组成部分”
- 不要在维护文档中展开 fetch_data、runner、自包含实现、claim gate、测试链路或长 pipeline 说明
- 更新 README、SKILL 和本文件时，优先保持项目定位、最小依赖、DuckDB 标准、验证边界和结果边界的一致口径
