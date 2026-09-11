# AGENTS.md（仓库级智能体指令 / Repo-level agent instructions）

> 面向读取 `AGENTS.md` 约定的 AI 编码智能体（**Codex CLI、ZCode、OpenClaw、Cursor** 等）。
> 工作语言：中文回复，代码与标识符用英文。

## 项目是什么

`skills/quant-oral-to-code/`：把**口述/抽象量化策略想法**转化为可回测代码的 Claude Code / Agent-Skills 技能。链路为 intake → DSL 提炼 → guardrails 审查 → codegen → report。仓库特征：

- 大量**确定性 Python 脚本**（`scripts/`）与 JSON Schema（`schemas/`）——行为验证靠真实运行，不靠口头声明
- 数据目标固定 **DuckDB**；外部数据源按 `templates/*.tmpl` 生成 fetcher
- 信念分级：`demo_only` / `portable_backtest` / `research_grade_local`；缺数据/字段映射时**必须走 `data_required_cutoff`**，不得假装完成回测

## 重要命令

```bash
# skill 全量校验（改任何模块/schema/脚本后必须跑）
python3 skills/quant-oral-to-code/scripts/run_full_validation.py

# 单项脚套（无需真实数据依赖）
python3 skills/quant-oral-to-code/scripts/test_skill_layout.py
python3 skills/quant-oral-to-code/scripts/test_guardrails.py

# 跨智能体适配（本仓库的 skill 可安装到多个 AI 智能体）
bash adapters/install.sh --all
python3 adapters/build_prompt_pack.py --check
```

校验依赖：`pip install --user duckdb jsonschema pandas`（无 pandas 时走 demo 数据路径也能过 cutoff 分支）。

## 更新工作流

1. 改模块（`modules/*.md`）与 SKILL.md 时保持**链路顺序**不被打乱：preflight → intake → dsl → guardrails → codegen → report
2. 改 schema/脚本必须以 `run_full_validation.py` 全绿为准（会真实跑 ma/chanlun/liangxue 三条 demo 的完整链路）
3. `guardrail_rules.json` 是**行为红线**：前视/过拟合/样本外/乐观成交假设的规则变更需要配一个对应的 demo 用例（学习 `ambiguous_demo`/`bad_csv_demo` 的 cutoff 模式）
4. 改动 SKILL.md / modules 后运行 `python3 adapters/build_prompt_pack.py` 保持提示词包零漂移

## 写入纪律

脚本打补丁时：每个文件用独立变量名；写 JSON 后立即 `json.loads` 断言；大改前先跑基线。

## provenance note

跨智能体适配层（`adapters/`、根 `AGENTS.md`）的设计与 mhsc 项目（mental-health-scale-chat）的 S5 套件同源：单一事实源 SKILL.md、软链优先安装、提示词包确定性生成 + `--check` 字节级漂移门。
