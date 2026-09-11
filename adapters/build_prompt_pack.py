#!/usr/bin/env python3
"""build_prompt_pack.py — quant-oral-to-code 的单文件提示词包生成器。

规则（与 mhsc 同源）：
- 内联 SKILL.md 正文 + agents（若有）+ 全部 modules/*.md；不内联 scripts/ 与 schemas/
  （脚本只能在有文件系统的智能体上运行；聊天型智能体用本包做策略规格转写与 guardrails 评审）
- 头部带防幻觉硬条款：缺数据/字段映射必须走 data_required_cutoff，不得假装完成回测
- `--check`：重建并与现有包字节级比对，漂移即退出 1
"""
import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / "skills" / "quant-oral-to-code"
OUT_DIR = REPO / "adapters" / "prompt-pack"

HEADER = """<!-- GENERATED FILE — DO NOT EDIT BY HAND. 源：skills/quant-oral-to-code/*，重建：adapters/build_prompt_pack.py -->
# quant-oral-to-code — 单文件提示词包

> 用途：在无文件系统的聊天型智能体（WorkBuddy、网页版 LLM 等）里，把口述量化策略转写成**结构化策略规格（DSL）+ guardrails 审查结论**，可直接交给文件型智能体（Claude Code / Codex / ZCode / DSH）按包内链路落脚本。
> 边界：聊天型环境**不声称能执行回测**；所有脚本与 Schema 在来源仓库 `skills/quant-oral-to-code/scripts/ 与 schemas/`。

## 包内文件

| # | 文件 |
| --- | --- |
{toc}

## 硬条款（防幻觉）

1. **数据门槛**：缺少真实数据、字段映射或关键定义时，必须进入 cutoff / `DATA_REQUIRED` 路径，禁止输出"回测完成"类结论。
2. **信念分级**：只能声明 `demo_only` / `portable_backtest` / `research_grade_local`，且必须给出支撑材料；聊天环境最多 `demo_only`，且需写明"仅流程转写，未执行"。
3. **guardrails 先行**：任何策略规格必须附前视/过拟合/样本外/成交假设的审查结论。
4. **DuckDB 固定口径**：生成的数据管道说明必须以"先落 DuckDB 再回测"为默认描述。
5. 条目缺失时明说，禁止编造字段名或数据源能力。

---
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    text = HEADER.format(toc="")
    inline = []
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    body = skill.split("---\n", 2)[2] if skill.startswith("---\n") else skill
    inline.append(("skills/quant-oral-to-code/SKILL.md（主协议）", body.strip()))
    for p in sorted((SKILL_DIR / "modules").glob("*.md")):
        inline.append((f"modules/{p.name}", p.read_text(encoding="utf-8").strip()))

    toc = "\n".join(f"| {i+1} | `{name}` |" for i, (name, _) in enumerate(inline))
    text = HEADER.format(toc=toc)
    for i, (name, body_) in enumerate(inline, 1):
        text += f"\n<!-- ===== 文件 {i}: {name} ===== -->\n\n## [{i}] {name}\n\n{body_}\n"

    out = OUT_DIR / "quant-oral-to-code-pack.md"
    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print("DRIFT — 请运行 python3 adapters/build_prompt_pack.py")
            return 1
        print("prompt pack OK（零漂移）")
    else:
        out.write_text(text, encoding="utf-8")
        print(f"生成 {out}（{len(text)} 字节，{len(inline)} 个内联文件）")

    # 自检：关键链路词必须都在
    required = ["guardrails", "DSL", "codegen", "demo_only", "DATA_REQUIRED", "DuckDB"]
    missing = [k for k in required if k.lower() not in text.lower()]
    if missing:
        print(f"SELF-CHECK FAIL: 缺 {missing}")
        return 1
    print("SELF-CHECK OK（链路/门槛词齐备）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
