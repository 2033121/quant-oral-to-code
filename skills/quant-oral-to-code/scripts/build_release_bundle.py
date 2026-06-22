from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return _skill_root().parents[1]


def _clean_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _ignore_patterns(directory: str, names: list[str]):
    ignored: set[str] = set()
    for name in names:
        if name == "__pycache__" or name.endswith(".pyc") or name == ".pytest_cache":
            ignored.add(name)
    return ignored


def _copy_skill_tree(target_root: Path) -> Path:
    source = _skill_root()
    target = target_root / "quant-oral-to-code"
    shutil.copytree(source, target, ignore=_ignore_patterns)
    return target


def _bundle_name_for_layout(layout: str) -> str:
    if layout == "skill-pack":
        return "quant-oral-to-code-skill-pack"
    return f"quant-oral-to-code-{layout}-bundle"


def _copy_requirements_file(target_root: Path) -> None:
    repo_root = _repo_root()
    source = repo_root / "requirements.txt"
    if source.exists():
        shutil.copy2(source, target_root / "requirements.txt")


def _write_legacy_pack_readme(target_root: Path) -> None:
    source = (_repo_root() / "README.md").read_text(encoding="utf-8")
    source = source.replace("(docs/2026-06-22-quant-oral-to-code.md)", "(skills/quant-oral-to-code/docs/2026-06-22-quant-oral-to-code.md)")
    source = source.replace("(docs/2026-06-22-a-share-data-sources.md)", "(skills/quant-oral-to-code/docs/2026-06-22-a-share-data-sources.md)")
    (target_root / "README.md").write_text(source, encoding="utf-8")


def _write_bundle_readme(target_root: Path, layout: str) -> None:
    validate_path = (
        ".\\quant-oral-to-code\\scripts\\validate_quant_oral_to_code.py"
        if layout in {"claude", "mimo"}
        else ".\\skills\\quant-oral-to-code\\scripts\\validate_quant_oral_to_code.py"
    )
    skill_entrypoint = (
        ".\\quant-oral-to-code\\SKILL.md"
        if layout in {"claude", "mimo"}
        else ".\\skills\\quant-oral-to-code\\SKILL.md"
    )
    readme_lines = [
        "# quant-oral-to-code bundle",
        "",
        f"- layout: `{layout}`",
        "",
        "## 安装方式",
        "",
    ]
    if layout in {"claude", "mimo"}:
        readme_lines.extend(
            [
                "1. 把当前目录里的全部内容解压或复制到目标 agent 的 `skills` 目录。",
                "2. 解压后目标目录里必须直接出现 `quant-oral-to-code/SKILL.md`。",
                "3. 不要额外保留最外层 bundle 目录。",
                "",
                "错误示例：`.../skills/quant-oral-to-code-claude-bundle/quant-oral-to-code/SKILL.md`",
                "正确示例：`.../skills/quant-oral-to-code/SKILL.md`",
            ]
        )
    else:
        readme_lines.extend(
            [
                "1. 把当前目录里的全部内容解压或复制到目标 agent 根目录。",
                "2. 保留当前 bundle 自带的 `skills/` 容器结构。",
                "3. 解压后目标目录里必须直接出现 `skills/quant-oral-to-code/SKILL.md`。",
                "4. 不要额外保留最外层 bundle 目录。",
                "",
                "错误示例：`.../agent-root/quant-oral-to-code-codex-bundle/skills/quant-oral-to-code/SKILL.md`",
                "正确示例：`.../agent-root/skills/quant-oral-to-code/SKILL.md`",
            ]
        )
    readme_lines.extend(
        [
            "",
            "## 依赖",
            "",
            "先安装最小依赖：",
            "",
            "```powershell",
            "python -m pip install -r .\\requirements.txt",
            "```",
            "",
            "## 校验",
            "",
            "确认技能入口存在：",
            "",
            f"- `{skill_entrypoint}`",
            "",
            "```powershell",
            f'python "{validate_path}"',
            "```",
            "",
        ]
    )
    (target_root / "INSTALL.md").write_text("\n".join(readme_lines), encoding="utf-8")


def _write_install_notes(target_root: Path, layout: str) -> None:
    extract_destination = "<agent-skills-dir>" if layout in {"claude", "mimo"} else "<agent-root>"
    skill_entrypoint = (
        "quant-oral-to-code/SKILL.md"
        if layout in {"claude", "mimo"}
        else "skills/quant-oral-to-code/SKILL.md"
    )
    validate_script = (
        "quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
        if layout in {"claude", "mimo"}
        else "skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py"
    )
    notes = {
        "layout": layout,
        "bundle_name": _bundle_name_for_layout(layout),
        "extract_destination": extract_destination,
        "copy_mode": (
            "extract_bundle_contents_into_skills_dir"
            if layout in {"claude", "mimo"}
            else "extract_bundle_contents_into_agent_root"
        ),
        "skill_entrypoint": skill_entrypoint,
        "validate_script": validate_script,
        "requirements_file": "requirements.txt",
    }
    (target_root / "INSTALL.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _zip_directory(source_dir: Path, zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(source_dir))
    return zip_path


def _write_sha256_file(file_path: Path) -> Path:
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    sha_path = file_path.with_name(f"{file_path.name}.sha256.txt")
    sha_path.write_text(f"{digest}  {file_path.name}\n", encoding="utf-8")
    return sha_path


def build_release_bundle(output_dir: str | Path, layout: str = "claude", make_zip: bool = False) -> dict[str, object]:
    output_root = Path(output_dir)
    bundle_root = output_root / _bundle_name_for_layout(layout)
    _clean_directory(bundle_root)

    if layout in {"codex", "skill-pack"}:
        skills_root = bundle_root / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)
        copied_skill = _copy_skill_tree(skills_root)
    elif layout in {"claude", "mimo"}:
        copied_skill = _copy_skill_tree(bundle_root)
    else:
        raise ValueError(f"unsupported layout: {layout}")

    _write_install_notes(bundle_root, layout=layout)
    _write_bundle_readme(bundle_root, layout=layout)
    _copy_requirements_file(bundle_root)
    if layout == "skill-pack":
        _write_legacy_pack_readme(bundle_root)

    zip_path = None
    sha256_path = None
    if make_zip:
        zip_path = _zip_directory(
            bundle_root,
            output_root / f"{bundle_root.name}.zip",
        )
        sha256_path = _write_sha256_file(zip_path)

    return {
        "layout": layout,
        "bundle_root": str(bundle_root),
        "skill_root": str(copied_skill),
        "zip_path": str(zip_path) if zip_path is not None else None,
        "sha256_path": str(sha256_path) if sha256_path is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build standalone release bundles for quant-oral-to-code.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--layout", choices=["claude", "mimo", "codex", "skill-pack", "all"], default="claude")
    parser.add_argument("--zip", action="store_true")
    args = parser.parse_args()

    if args.layout == "all":
        result = [
            build_release_bundle(
                output_dir=args.output_dir,
                layout=layout,
                make_zip=args.zip,
            )
            for layout in ("claude", "mimo", "codex", "skill-pack")
        ]
    else:
        result = build_release_bundle(
            output_dir=args.output_dir,
            layout=args.layout,
            make_zip=args.zip,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
