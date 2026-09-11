#!/usr/bin/env bash
# adapters/install.sh — 将本仓库技能安装到本机各 AI 智能体的技能目录。
# 默认 symlink（随仓库更新联动）；--copy 改为独立副本；--skip-existing 覆盖同名已装技能。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_NAMES=(quant-oral-to-code)

COPY=0
STATUS=0
SKIP_EXISTING=0
TARGETS=()   # "label:path"

usage() {
  sed -n '2,40p' "$REPO_ROOT/adapters/README.md" | head -30
  echo "用法: $0 [--claude|--codex|--zcode|--dsh|--agents-dir DIR] [--all] [--status] [--copy] [--skip-existing]"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --claude)       TARGETS+=("claude:$HOME/.claude/skills");;
    --codex)        TARGETS+=("codex:$HOME/.codex/skills");;
    --zcode)        TARGETS+=("zcode:$HOME/.zcode/skills");;
    --dsh)          TARGETS+=("dsh:$HOME/.dsh/skills");;
    --all)          TARGETS+=("claude:$HOME/.claude/skills" "codex:$HOME/.codex/skills"
                              "zcode:$HOME/.zcode/skills" "dsh:$HOME/.dsh/skills");;
    --copy)         COPY=1;;
    --status)       STATUS=1;;
    --skip-existing) SKIP_EXISTING=1;;
    -h|--help)      usage; exit 0;;
    --agents-dir)   shift; TARGETS+=("custom:$1");;
    *)              echo "未知参数: $1"; usage; exit 2;;
  esac
  shift
done

install_into() {  # $1 = dest root
  local dest_root="$1" name src link
  [ -d "$dest_root" ] || mkdir -p "$dest_root"
  for name in "${SKILL_NAMES[@]}"; do
    src="$REPO_ROOT/skills/$name"
    dest="$dest_root/$name"
    if [ -e "$dest" ] || [ -L "$dest" ]; then
      if [ "$SKIP_EXISTING" = 1 ]; then
        echo "  skip（已存在）: $dest"; continue
      fi
      if [ -L "$dest" ]; then
        echo "  刷新软链: $dest"
        rm -f "$dest"
      else
        echo "  !! 已存在且不是软链，跳过（如需覆盖请手动处理）: $dest"
        continue
      fi
    fi
    if [ "$COPY" = 1 ]; then
      cp -r "$src" "$dest"
      echo "  copy: $dest"
    else
      ln -s "$src" "$dest"
      echo "  link: $dest -> $src"
    fi
  done
  # 校验 frontmatter（ZCode 规则：name+description 必备，description ≤1024 字符
  python3 - "$dest_root" <<'PY'
import sys, re, pathlib, glob
bad = []
for sk in glob.glob(sys.argv[1] + "/*/SKILL.md"):
    t = pathlib.Path(sk).read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        bad.append((sk, "no frontmatter")); continue
    fm = m.group(1)
    for key in ("name", "description"):
        if not re.search(rf"(?m)^{key}:", fm):
            bad.append((sk, f"missing {key}"))
    dm = re.search(r"description:(.*?)(?=\n\w+:|\Z)", fm, re.S)
    if dm and len(dm.group(1).strip()) > 1024:
        bad.append((sk, f"description >1024 chars ({len(dm.group(1).strip())})"))
if bad:
    for sk, why in bad: print(f"  WARN: {sk}: {why}")
    sys.exit(1)
print("  frontmatter OK (name+description, description<=1024)")
PY
}

mkdir -p "$REPO_ROOT/adapters/prompt-pack"
if [ "$STATUS" = 1 ]; then
  for t in "${TARGETS[@]}"; do
    label="${t%%:*}"; root="${t#*:}"
    echo "==> $label ($root)"
    for name in "${SKILL_NAMES[@]}"; do
      dest="$root/$name"
      if [ -L "$dest" ]; then
        echo "    $name: symlink -> $(readlink "$dest")"
      elif [ -d "$dest" ]; then
        echo "    $name: copy/dir（独立副本）"
      else
        echo "    $name: 未安装"
      fi
    done
  done
  [ -f "$REPO_ROOT/adapters/prompt-pack/quant-oral-to-code-pack.md" ] \
    && echo "prompt-pack: 已生成（$(ls "$REPO_ROOT/adapters/prompt-pack" | tr '\n' ' '）)" \
    || echo "prompt-pack: 未生成（python3 adapters/build_prompt_pack.py）"
  exit 0
fi
for t in "${TARGETS[@]}"; do
  label="${t%%:*}"; root="${t#*:}"
  echo "==> $label"
  install_into "$root"
done

if [ ! -f "$REPO_ROOT/adapters/prompt-pack/quant-oral-to-code-pack.md" ]; then
  echo ""
  echo "提示：尚未生成提示词包。运行: python3 $REPO_ROOT/adapters/build_prompt_pack.py"
fi

echo "DONE. 若平台需要刷新：Codex/ZCode 设置页 Refresh；Claude Code/DSH 重启会话。"
