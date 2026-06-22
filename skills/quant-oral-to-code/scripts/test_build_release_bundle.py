from __future__ import annotations

import zipfile
from pathlib import Path

from build_release_bundle import build_release_bundle


def test_build_release_bundle_for_claude_layout(tmp_path: Path):
    result = build_release_bundle(tmp_path, layout="claude", make_zip=False)
    bundle_root = Path(result["bundle_root"])
    skill_root = Path(result["skill_root"])
    assert skill_root.name == "quant-oral-to-code"
    assert (skill_root / "SKILL.md").exists()
    assert (skill_root / "agents" / "openai.yaml").exists()
    assert (skill_root / "docs" / "2026-06-22-quant-oral-to-code.md").exists()
    assert (bundle_root / "INSTALL.json").exists()
    assert (bundle_root / "INSTALL.md").exists()
    assert (bundle_root / "requirements.txt").exists()
    assert "python -m pip install -r .\\requirements.txt" in (bundle_root / "INSTALL.md").read_text(encoding="utf-8")


def test_build_release_bundle_for_codex_layout(tmp_path: Path):
    result = build_release_bundle(tmp_path, layout="codex", make_zip=False)
    skill_root = Path(result["skill_root"])
    assert skill_root.parts[-2:] == ("skills", "quant-oral-to-code")
    assert (skill_root / "scripts" / "validate_quant_oral_to_code.py").exists()


def test_build_release_bundle_for_mimo_layout(tmp_path: Path):
    result = build_release_bundle(tmp_path, layout="mimo", make_zip=False)
    bundle_root = Path(result["bundle_root"])
    skill_root = Path(result["skill_root"])
    assert skill_root.name == "quant-oral-to-code"
    assert (bundle_root / "requirements.txt").exists()
    install_json = (bundle_root / "INSTALL.json").read_text(encoding="utf-8")
    assert "extract_bundle_contents_into_skills_dir" in install_json
    assert (skill_root / "agents" / "openai.yaml").exists()


def test_build_release_bundle_for_legacy_skill_pack_layout(tmp_path: Path):
    result = build_release_bundle(tmp_path, layout="skill-pack", make_zip=False)
    bundle_root = Path(result["bundle_root"])
    skill_root = Path(result["skill_root"])
    assert bundle_root.name == "quant-oral-to-code-skill-pack"
    assert skill_root.parts[-2:] == ("skills", "quant-oral-to-code")
    assert (bundle_root / "README.md").exists()
    assert (bundle_root / "requirements.txt").exists()
    readme_text = (bundle_root / "README.md").read_text(encoding="utf-8")
    assert "skills/quant-oral-to-code/docs/2026-06-22-quant-oral-to-code.md" in readme_text
    assert not any(path.name == "__pycache__" for path in bundle_root.rglob("*"))


def test_build_release_bundle_writes_sha256_for_zip(tmp_path: Path):
    result = build_release_bundle(tmp_path, layout="claude", make_zip=True)
    sha256_path = Path(result["sha256_path"])
    assert sha256_path.exists()
    assert "quant-oral-to-code-claude-bundle.zip" in sha256_path.read_text(encoding="utf-8")


def test_build_release_bundle_zip_is_directly_extractable(tmp_path: Path):
    result = build_release_bundle(tmp_path, layout="codex", make_zip=True)
    zip_path = Path(result["zip_path"])
    with zipfile.ZipFile(zip_path) as archive:
        names = {entry.filename for entry in archive.infolist()}
    assert "INSTALL.md" in names
    assert "requirements.txt" in names
    assert "skills/quant-oral-to-code/SKILL.md" in names
    assert "quant-oral-to-code-codex-bundle/skills/quant-oral-to-code/SKILL.md" not in names
