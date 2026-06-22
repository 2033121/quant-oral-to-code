from __future__ import annotations

import importlib
from pathlib import Path

from resolve_repo_root import resolve_repo_root


REQUIRED_PYTHON_PACKAGES = ["duckdb"]


def check_runtime_capabilities(repo_root: str | Path | None = None) -> dict[str, object]:
    resolved_root = resolve_repo_root(repo_root or __file__)
    missing_dependencies: list[str] = []
    notes: list[str] = []

    capabilities: dict[str, object] = {}
    python_ok = True
    for package_name in REQUIRED_PYTHON_PACKAGES:
        try:
            module = importlib.import_module(package_name)
            capabilities[package_name] = {
                "installed": True,
                "hard_required": True,
                "version": getattr(module, "__version__", None),
                "error": None,
            }
        except Exception as exc:
            python_ok = False
            missing_dependencies.append(package_name)
            capabilities[package_name] = {
                "installed": False,
                "hard_required": True,
                "version": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
            notes.append(
                f"缺少硬依赖 {package_name}，必须先满足后才能进入 DuckDB 标准执行栈。"
            )

    if python_ok:
        notes.append("Python 运行时通过，DuckDB 硬依赖已满足。")

    return {
        "repo_root": str(resolved_root),
        "python_ok": python_ok,
        "overall_ready": python_ok and not missing_dependencies,
        "required_python_packages": list(REQUIRED_PYTHON_PACKAGES),
        "resolved_capabilities": capabilities,
        "missing_dependencies": missing_dependencies,
        "notes": notes,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(check_runtime_capabilities(), ensure_ascii=False, indent=2))
