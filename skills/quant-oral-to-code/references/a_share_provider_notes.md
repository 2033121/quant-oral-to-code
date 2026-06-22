# A 股 Provider 路由说明

本文件对应 `Authoritative Task 4` 的权威实现约束，只描述 provider 路由与 fetcher 生成，不执行真实联网抓取。

## 默认分流

- 默认先走零门槛路径。
- 当 `user_prefers_zero_setup=True` 且 `needs_history_bars=True` 且 `user_can_register_account=False` 时，优先选择 `akshare`。
- 零门槛历史行情的优先顺序为：`akshare -> efinance -> adata -> baostock`。
- 用户已经具备认证条件，或明确接受注册配置时，才允许升级到 `tushare` 或 `jqdatasdk`。
- 若只能依赖人工导出文件，则进入 `manual_csv`，默认决策为 `data_required_cutoff`。

## 生成物约束

- `decision == generated_fetcher`：
  - 必须生成 `data/fetch_data.py`
  - 必须生成 `data/provider_choice.json`
  - 必须生成 `data/provider_setup.md`
- `decision == data_required_cutoff`：
  - 不得生成 runnable `data/fetch_data.py`
  - 仍需生成 `data/provider_choice.json`
  - 仍需生成 `data/provider_setup.md`

## 统一数据落地

- 所有真实 provider fetcher 模板都要把原始结果先落到 `data/raw/market_<provider>.csv`。
- 随后统一调用 `normalize_to_duckdb()`。
- 规范化目标固定为 `data/normalized/market.duckdb`。

## Provider 备注

- `akshare`：默认首选，零门槛，适合新手快速拉 A 股日线历史。
- `efinance`：东财系公开接口，零门槛备选。
- `adata`：多源聚合，适合数据落地备选。
- `baostock`：匿名登录兜底，但不作为唯一长期主源。
- `tushare`：需要 token，适合愿意注册并配置凭证的用户。
- `jqdatasdk`：需要账号认证，适合已有聚宽数据条件的用户。
- `manual_csv`：表示当前仍需用户准备数据文件，不假装已经具备可回测行情。
