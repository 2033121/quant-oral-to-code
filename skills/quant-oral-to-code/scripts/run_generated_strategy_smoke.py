from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def run_generated_strategy_smoke(workspace: str | Path) -> dict[str, object]:
    workspace_path = Path(workspace).resolve()
    runner_path = workspace_path / "run_backtest.py"
    if not runner_path.exists():
        raise FileNotFoundError(f"missing generated runner: {runner_path}")

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, str(runner_path)],
        cwd=str(workspace_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "generated runner smoke failed with "
            f"exit code {completed.returncode}: {completed.stderr.strip()}"
        )

    metrics_path = workspace_path / "results" / "metrics_snapshot.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"runner did not write metrics snapshot: {metrics_path}")
    result = json.loads(metrics_path.read_text(encoding="utf-8"))
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
