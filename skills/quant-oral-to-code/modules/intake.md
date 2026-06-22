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
