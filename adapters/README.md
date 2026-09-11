# adapters/ — quant-oral-to-code 跨智能体适配层

> 本套件与 mhsc 项目（mental-health-scale-chat）S5 同源：单一事实源 SKILL.md、软链优先、提示词包确定性生成。
> 差异点：本 skill 含大量确定性 Python 脚本——提示词包只适合做**流程转写/讲解**，真正的回测执行必须回到有文件系统与 Python 的智能体（Claude Code / Codex / ZCode / DSH）。



本仓库的两个技能采用标准 **Agent Skills（SKILL.md）** 格式编写，这种格式已被主流 AI 编码智能体广泛采纳。本目录提供三件事：

1. **`install.sh`**：一条命令把技能安装到本机检测到的各智能体技能目录（软链默认、`--copy` 可选）。
2. **`build_prompt_pack.py`**：为**无本地文件系统 / 无技能装载机制**的聊天型智能体（WorkBuddy、通用聊天助手、网页版模型等）生成可一次性粘贴的**单文件提示词包**。
3. 本 README：各智能体的安装路径、装载方式与注意事项对照表。

## 适配矩阵 / Compatibility matrix

| 智能体 | 技能目录 | 安装命令 | 装载方式 | 注意事项 |
| --- | --- | --- | --- | --- |
| **Claude Code** | `~/.claude/skills/<name>/` | `adapters/install.sh --claude` | 目录内 `SKILL.md` + frontmatter | 开发文档 `CLAUDE.md` 已随附 |
| **Codex CLI** (OpenAI) | `~/.codex/skills/<name>/`（个人）；项目级 `.codex/skills/` | `adapters/install.sh --codex` | SKILL.md（Agent Skills） | 仓库级指令走根 `AGENTS.md`；Codex 自动读取 |
| **ZCode** (GLM 官方 harness) | `~/.zcode/skills/<name>/` | `adapters/install.sh --zcode` 或 Settings→Skills→Import（自动扫描外部智能体目录，支持 symlink/copy 模式） | SKILL.md | frontmatter 必须有 `name`+`description`，**description ≤1024 字符**（本仓库约 160，安全）；聊天中用 `$mental-health-scale-chat` 调用 |
| **OpenClaw / Cursor / Augment / Windsurf** | 各自家目录（如 `~/.agents/skills/`） | `adapters/install.sh --agents-dir "$HOME/.agents/skills"` | SKILL.md | 均兼容同一 SKILL.md 形态 |
| **DSH (DeepSeek Harness)** | `~/.dsh/skills/<name>/` | `adapters/install.sh --dsh` | 技能目录软链进 `~/.dsh/skills/`（web 重启生效） | 参考本仓库 research-skills 的啟停脚本模式 |
| **WorkBuddy（腾讯办公 Agent）** 及其他聊天型智能体 | 无本地技能目录 | `python3 adapters/build_prompt_pack.py` | 把生成的 `prompt-pack/*.md` 直接粘贴进对话/自定义指令 | 提示词包内联 SKILL 正文 + 全部模块文档（intake/dsl/guardrails/codegen/report 等）；脚本与 Schema 未内联（聊天环境无法执行，也避免包体过大）——聊天型智能体用它输出策略规格与评审结论，再由文件型智能体按包内规格落脚本 |

## 安装 / Install

```bash
cd <repo根目录>

# 全自动：探测本机已有的智能体目录并安装（已被别的技能占住同名位置时会提示 --skip-existing）
bash adapters/install.sh --all

# 指定平台
bash adapters/install.sh --claude --codex --zcode --dsh

# 以独立副本安装（不随仓库更新联动）
bash adapters/install.sh --all --copy

# 自定义附加目录（任何遵循 SKILL.md 约定的智能体）
bash adapters/install.sh --agents-dir "$HOME/.agents/skills"
```

安装后刷新：Codex / ZCode 在设置页点 Refresh 导入；Claude Code / DSH 重启会话生效。

## 设计原则

- **单一事实源**：`skills/mental-health-scale-chat/SKILL.md` 是唯一权威入口，所有平台形态均由它派生；提示词包由 `build_prompt_pack.py` 确定性生成（带内容自检）。
- **安全边界平移**：任何形态（软链 / 副本 / 提示词包）都完整保留危机熔断与非诊断边界，不得在适配层删减。
- **同步纪律**：改动 `SKILL.md` 或 `references/` 后必须运行 `python3 adapters/build_prompt_pack.py`，让提示词包与源文件保持零漂移。
