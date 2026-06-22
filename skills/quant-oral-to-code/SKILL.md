---
name: "quant-oral-to-code"
description: "把口述或抽象策略想法转换成可回测代码骨架、回测入口和结果报告，并在生成前做 DSL 提炼与风险护栏审查。Invoke when 用户希望把量化思路直接写成策略代码。"
---

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
