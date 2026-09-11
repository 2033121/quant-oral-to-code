#!/usr/bin/env python3
"""build_release_bundle.py — 把 skill 打包成可分发 release bundle。

产物（默认写入仓库 dist/，已在 .gitignore）：
  dist/quant-oral-to-code.zip        技能目录打包（已跑 test_skill_layout 归一布局）
  dist/INSTALL.md                    各智能体安装说明（Claude/Codex/ZCode/DSH + prompt-pack 用户）
  dist/INSTALL.json                  机器可读安装清单
  dist/requirements.txt              校验依赖
  dist/quant-oral-to-code.zip.sha256 侧车哈希

确定性：zip 采用固定排序与固定时间戳（2026-01-01T00:00:00Z），同一内容产出字节相同的包。
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import zipfile

SKILL = pathlib.Path(__file__).resolve().parent.parent
REPO = SKILL.parent.parent
DIST = REPO / "dist"
TS = (2026, 1, 1, 0, 0, 0)

INSTALL_MD = """# quant-oral-to-code skill — 安装指南

本包是 `quant-oral-to-code` 技能的可穿戴发行包（zip + 校验和）。

## 校验文件完整性

```bash
sha256sum -c quant-oral-to-code.zip.sha256
```

## Claude Code

```bash
mkdir -p ~/.claude/skills
unzip quant-oral-to-code.zip -d ~/.claude/skills/quant-oral-to-code
```

## Codex CLI / ZCode（Agent Skills 兼容）

```bash
# Codex
mkdir -p ~/.codex/skills && unzip quant-oral-to-code.zip -d ~/.codex/skills/quant-oral-to-code
# ZCode
mkdir -p ~/.zcode/skills && unzip quant-oral-to-code.zip -d ~/.zcode/skills/quant-oral-to-code
# 随后在 设置→Skills 页面 Refresh
```

## DSH (DeepSeek Harness)

```bash
mkdir -p ~/.dsh/skills && unzip quant-oral-to-code.zip -d ~/.dsh/skills/quant-oral-to-code && 重启会话生效
```

## 聊天型智能体（无文件系统）

改用仓库 `adapters/prompt-pack/quant-oral-to-code-pack.md` 的复制版做流程转写；
回测执行需要回到上述任一文件型智能体。

## 结构校验（任何平台、装完即测）

```bash
python3 {skill_dir}/scripts/test_skill_layout.py
```

依赖见 requirements.txt（仅校验脚本需要：duckdb / jsonschema / pandas）。
"""

REQS = """# 仅校验/运行生成链路所需要
duckdb>=1.1
jsonschema>=4.0
pandas>=2.0
"""


def main() -> int:
    DIST.mkdir(exist_ok=True)
    zpath = DIST / "quant-oral-to-code.zip"

    import zipfile

    entries = sorted(
        p for p in SKILL.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts
    )
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in entries:
            arc = "quant-oral-to-code/" + p.relative_to(SKILL).as_posix()
            info = zipfile.ZipInfo(arc, date_time=TS)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, p.read_bytes())

    sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    (DIST / "quant-oral-to-code.zip.sha256").write_text(f"{sha}  quant-oral-to-code.zip\n", encoding="utf-8")

    (DIST / "INSTALL.md").write_text(INSTALL_MD.format(skill_dir="~/.claude/skills/quant-oral-to-code"), encoding="utf-8")
    (DIST / "requirements.txt").write_text(REQS, encoding="utf-8")

    install_json = {
        "skill": "quant-oral-to-code",
        "version": "ec1228c-adapter",
        "artifact": "quant-oral-to-code.zip",
        "sha256": sha,
        "installs": {
            "claude_code": "~/.claude/skills/quant-oral-to-code",
            "codex_cli": "~/.codex/skills/quant-oral-to-code",
            "zcode": "~/.zcode/skills/quant-oral-to-code",
            "dsh": "~/.dsh/skills/quant-oral-to-code",
        },
        "verify": ["sha256sum -c quant-oral-to-code.zip.sha256",
                   "python3 ~/.claude/skills/quant-oral-to-code/scripts/test_skill_layout.py"],
    }
    (DIST / "INSTALL.json").write_text(json.dumps(install_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads((DIST / "INSTALL.json").read_text())
    print(f"bundle: {zpath} sha256={sha[:12]}... files={len(entries)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
