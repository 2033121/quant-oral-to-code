from __future__ import annotations

from pathlib import Path


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_template(template_name: str) -> str:
    template_path = _skill_root() / "templates" / template_name
    return template_path.read_text(encoding="utf-8")


def generate_strategy_tests(spec: dict, output_dir: str | Path) -> dict[str, str]:
    _ = spec
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    test_text = _load_template("test_strategy_smoke.py.tmpl")
    test_file = output_path / "test_strategy_smoke.py"
    test_file.write_text(test_text, encoding="utf-8")
    return {"test_file": str(test_file)}
