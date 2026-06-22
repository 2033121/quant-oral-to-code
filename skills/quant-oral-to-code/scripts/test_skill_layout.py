from __future__ import annotations

from validate_quant_oral_to_code import REQUIRED_FILES


def test_quant_oral_to_code_skill_layout_has_required_files():
    root = REQUIRED_FILES[0].resolve().parents[0]
    missing = [str(path.relative_to(root)) for path in REQUIRED_FILES if not path.exists()]
    assert not missing, f"missing required skill files: {missing}"
