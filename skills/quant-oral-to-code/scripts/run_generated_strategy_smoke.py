from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_generated_strategy_smoke(workspace: str | Path) -> dict[str, object]:
    workspace_path = Path(workspace).resolve()
    runner_path = workspace_path / "run_backtest.py"
    if not runner_path.exists():
        raise FileNotFoundError(f"missing generated runner: {runner_path}")

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    namespace: dict[str, object] = {
        "__file__": str(runner_path),
        "__name__": "generated_runner_smoke",
    }
    exec(compile(runner_path.read_text(encoding="utf-8"), str(runner_path), "exec"), namespace)
    main = namespace.get("main")
    if not callable(main):
        raise AttributeError(f"runner does not expose callable main(): {runner_path}")
    result = main()
    if not isinstance(result, dict):
        raise TypeError(f"runner main() must return dict, got {type(result).__name__}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run generated strategy smoke validation.")
    parser.add_argument("workspace", help="Path to generated strategy workspace")
    args = parser.parse_args()
    result = run_generated_strategy_smoke(args.workspace)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
