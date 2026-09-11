[English](README.en.md) | 中文

# quant-oral-to-code

`quant-oral-to-code` 是一个面向量化初学者和通用 Agent 的开源 skill。它的定位是把自然语言策略想法整理成可检查、可复跑、可解释的策略工作区骨架，而不是直接承诺研究级收益结论。

## 项目定位

- 面向自然语言量化策略描述的开源工作区骨架
- 默认产物口径以审计、解释和最小可复跑为主
- 当前高层标准以本仓库真实实现为准，不引用旧 `.trae` 私有路径或历史草稿文件
- 若下游模块或参考文档与当前高层口径冲突，以本 `README.md` 与 `docs/2026-06-22-quant-oral-to-code.md` 为准

## 最小依赖

当前根仓库没有 `pyproject.toml`，根目录保留最小依赖文件 `requirements.txt`：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

最小依赖包括：

- `duckdb`
- `jsonschema`

`pandas` 不属于当前最小验证链路的硬依赖。它只用于部分可选取数模板或数据整理场景，不进入根目录最小依赖集合。

可选 provider 或模板依赖不进入根目录最小依赖集合，按使用场景自行安装。

## 安装与发布布局

当前发布统一分成四种布局：

- `quant-oral-to-code-claude-bundle.zip`
  适合 Claude / 直接技能目录型 agent。解压到目标 `skills` 目录后，应直接出现 `quant-oral-to-code/SKILL.md`。
- `quant-oral-to-code-mimo-bundle.zip`
  适合 MiMo Code 这类同样要求“技能目录直挂”的系统。解压后同样应直接出现 `quant-oral-to-code/SKILL.md`。
- `quant-oral-to-code-codex-bundle.zip`
  适合需要外层 `skills/` 容器的系统。解压后应出现 `skills/quant-oral-to-code/SKILL.md`。
- `quant-oral-to-code-skill-pack`
  这是保留给旧分发链路的兼容目录，现已对齐新版内容，不再是历史旧包。

如果某个 agent 安装后“找不到 skill”，先检查是不是多复制了一层外壳目录。正确结果不是：

- `.../skills/quant-oral-to-code-claude-bundle/quant-oral-to-code/SKILL.md`

正确结果应该是以下两种之一：

- `.../skills/quant-oral-to-code/SKILL.md`
- `.../skills/skills/quant-oral-to-code/SKILL.md`

具体取决于目标系统是否要求外层 `skills/` 容器。

重新生成全部发布产物：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" "skills/quant-oral-to-code/scripts/build_release_bundle.py" --output-dir "..\packages" --layout all --zip
```

## 数据存储标准

- DuckDB 是唯一标准持久化格式
- 标准路径是 `generated_strategies/<slug>/data/normalized/market.duckdb`
- 标准表名是 `bars`
- 标准主键是 `["symbol", "trade_date"]`
- 外部输入可以来自 `csv / parquet / json / sqlite / provider api`，但进入统一链路前必须归一化到 DuckDB
- 缺少真实数据、字段映射、关键列或最小数据契约时，必须进入 `data_required_cutoff` 截断，不能伪装成“已完成正式回测”

## 验证方式与副作用边界

只读结构验证：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" "skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
```

全链路验证：

```powershell
& "C:\Users\xing\AppData\Local\Programs\Python\Python312\python.exe" "skills/quant-oral-to-code/scripts/run_full_validation.py"
```

`run_full_validation.py` 不是“最小验证”。它具有工作区副作用，但范围只限 `CASES` 中固定示例 slug 的工作区；对进入 `data_required_cutoff` 截断的示例，也只清理该工作区内预定义产物，不应当作只读检查。

## 结果口径边界

- 默认摘要可以报告 claim level、decision、guardrail 提示、动作计数和样本规模
- 默认摘要不宣称真实收益、最大回撤或 Sharpe
- 只有在后续明确接入真实 PnL / equity curve 证据链后，才允许把这类指标写成可用结论

## 参考文档

- [开源版口径与边界说明](docs/2026-06-22-quant-oral-to-code.md)
- [A 股数据源说明](docs/2026-06-22-a-share-data-sources.md)

## License

MIT
## 多智能体适配 / Cross-agent compatibility

两个 skill 形态均为标准 Agent Skills（SKILL.md），可装载到多个智能体：

```bash
bash adapters/install.sh --claude --codex --zcode --dsh   # 软链安装到对应 skills 目录（含 ZCode frontmatter 校验）
python3 adapters/build_prompt_pack.py                     # 生成聊天型智能体（WorkBuddy 等）可粘贴的单文件包
```

注意：`scripts/` 与 `schemas/` 未内联进提示词包——聊天型智能体用它做**策略规格转写与 guardrails 评审**（最多 `demo_only` 信念分级），真正的回测执行需要文件型智能体。详见根 `AGENTS.md` 与 `adapters/README.md`。
