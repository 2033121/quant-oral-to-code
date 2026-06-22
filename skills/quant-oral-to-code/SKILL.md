---
name: "quant-oral-to-code"
description: "把口述或抽象量化策略想法整理成可检查的开源工作区骨架。适用于需要统一口径、数据边界和验证入口的场景。"
---

# quant-oral-to-code

这个 skill 适用于以下场景：

- 用户希望把自然语言量化想法整理成统一工作区骨架
- 用户需要先明确数据标准、验证入口和结果边界
- 用户当前更关心开源版口径是否一致，而不是内部实现细节
- 若下游模块或参考文档与当前高层口径冲突，以 `README.md` 与 `docs/2026-06-22-quant-oral-to-code.md` 为准；若这两者彼此冲突，以 `docs/2026-06-22-quant-oral-to-code.md` 为最高优先级

## 固定口径

- DuckDB 是唯一标准持久化格式
- 标准路径是 `generated_strategies/<slug>/data/normalized/market.duckdb`
- 标准表名是 `bars`
- 标准主键是 `["symbol", "trade_date"]`
- 缺少真实数据、字段映射、关键列或最小数据契约时，必须进入 `data_required_cutoff` 截断
- 默认摘要不宣称真实收益、最大回撤或 Sharpe
- `research_grade_local` 只应在未来具备额外研究证据时使用，当前默认口径应保持保守

## 模块顺序

- `modules/preflight.md`
- `modules/intake.md`
- `modules/dsl.md`
- `modules/guardrails.md`
- `modules/data.md`
- `modules/codegen.md`
- `modules/onboarding.md`
- `modules/report.md`

## 验证入口

只读结构验证：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" "skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
```

全链路验证：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" "skills/quant-oral-to-code/scripts/run_full_validation.py"
```

注意：`run_full_validation.py` 不是最小验证，并且具有工作区副作用，但范围只限 `CASES` 中固定示例 slug 的工作区；不会修改手写源码或手写文档，只会触碰验证生成物或预定义产物；对进入 `data_required_cutoff` 截断的示例，也只清理预定义产物。
