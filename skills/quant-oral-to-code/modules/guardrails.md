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
