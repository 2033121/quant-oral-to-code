from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def load_generated_strategy(strategy_path: str | Path):
    strategy_file = Path(strategy_path)
    module_spec = spec_from_file_location("generated_strategy_module", strategy_file)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"unable to create module spec for {strategy_file}")

    module = module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    if not hasattr(module, "GeneratedStrategy"):
        raise AttributeError(f"{strategy_file} does not expose GeneratedStrategy")
    return module.GeneratedStrategy
