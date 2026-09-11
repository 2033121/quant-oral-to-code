# A 股数据源说明

## 推荐顺序

按“零门槛到高完整度”大致可分为：

1. `akshare`
2. `efinance`
3. `adata`
4. `baostock`
5. `tushare`
6. `jqdatasdk`

## skill 对数据源的最低要求

不管上游 provider 是什么，进入主链前都必须满足：

- 能落到 `market.duckdb`
- 有 `bars` 主表
- 至少包含 `symbol / trade_date / open / high / low / close / volume`
- 能生成非空 `data_hash`

## 真实研究额外上下文

如果策略依赖 A 股常见抽象语义，还可能需要：

- `security_master`
- `st_status`
- `suspension_status`
- `group_membership`
- `benchmark_series`

这些上下文缺失时，不应假装已经可以完成正式研究或正式回测。
