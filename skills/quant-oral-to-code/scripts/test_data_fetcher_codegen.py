from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path

from generate_data_fetcher import generate_data_fetcher
from select_data_provider import select_data_provider


def _assert_repo_root_resolution_snippet(fetcher_text: str) -> None:
    assert "def _resolve_repo_root() -> Path:" in fetcher_text
    assert 'REPO_ROOT_SENTINELS = (".git", "docs", "skills")' in fetcher_text
    assert 'SKILL_SCRIPT_SENTINELS = ("normalize_to_duckdb.py", "context_data_helpers.py")' in fetcher_text
    assert 'has_repo_sentinels = all((candidate / sentinel).exists() for sentinel in REPO_ROOT_SENTINELS)' in fetcher_text
    assert 'has_skill_sentinels = all((script_root / sentinel).exists() for sentinel in SKILL_SCRIPT_SENTINELS)' in fetcher_text
    assert "REPO_ROOT = _resolve_repo_root()" in fetcher_text
    assert "def _load_module(module_filename: str, module_name: str):" in fetcher_text
    assert '"normalize_to_duckdb.py"' in fetcher_text
    assert '"context_data_helpers.py"' in fetcher_text
    assert "persist_real_data_artifacts" in fetcher_text
    assert "REPO_ROOT = WORKSPACE_ROOT.parents[1]" not in fetcher_text
    assert "sys.path.insert" not in fetcher_text
    assert "from normalize_to_duckdb import normalize_to_duckdb" not in fetcher_text


@contextmanager
def _temporary_modules(modules: dict[str, types.ModuleType]):
    original = {name: sys.modules.get(name) for name in modules}
    sys.modules.update(modules)
    try:
        yield
    finally:
        for name, module in original.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def _execute_generated_fetcher_module(fetcher_path: Path):
    fake_pandas = types.ModuleType("pandas")
    fake_pandas.DataFrame = type("DataFrame", (), {})
    fake_akshare = types.ModuleType("akshare")
    polluted_normalizer = types.ModuleType("normalize_to_duckdb")

    def _wrong_normalize_to_duckdb(input_path, db_path):
        raise AssertionError(
            "generated fetcher should load normalize_to_duckdb from SCRIPT_ROOT, not sys.modules cache"
        )

    polluted_normalizer.normalize_to_duckdb = _wrong_normalize_to_duckdb

    module_name = f"generated_fetcher_{abs(hash(fetcher_path))}"
    spec = importlib.util.spec_from_file_location(module_name, fetcher_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    original_sys_path = sys.path.copy()
    with _temporary_modules(
        {
            "pandas": fake_pandas,
            "akshare": fake_akshare,
            "normalize_to_duckdb": polluted_normalizer,
        }
    ):
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path[:] = original_sys_path
            sys.modules.pop(module_name, None)
            sys.modules.pop("normalize_to_duckdb", None)
    return module


def _assert_generated_fetcher_compiles(fetcher_path: Path) -> str:
    text = fetcher_path.read_text(encoding="utf-8")
    compile(text, str(fetcher_path), "exec")
    return text


def test_provider_selection_and_cutoff_artifacts_are_different(tmp_path: Path):
    provider = select_data_provider(
        {
            "needs_history_bars": True,
            "user_prefers_zero_setup": True,
            "user_can_register_account": False,
        }
    )
    assert provider["provider"] == "akshare"
    assert provider["decision"] == "generated_fetcher"

    generated = generate_data_fetcher(provider, tmp_path, symbol="000001.SZ")
    assert generated["decision"] == "generated_fetcher"
    assert (tmp_path / "data" / "fetch_data.py").exists()
    assert (tmp_path / "data" / "provider_choice.json").exists()
    assert (tmp_path / "data" / "provider_setup.md").exists()
    fetcher_text = (tmp_path / "data" / "fetch_data.py").read_text(encoding="utf-8")
    setup_text = (tmp_path / "data" / "provider_setup.md").read_text(encoding="utf-8")
    assert 'PROVIDER_NAME = "akshare"' in fetcher_text
    assert "normalize_to_duckdb" in fetcher_text
    assert "market.duckdb" in fetcher_text
    assert "context_fetch_report.json" in fetcher_text
    assert "data_contract.json" in fetcher_text
    assert "PROVIDER_CONTEXT_SUPPORT" in fetcher_text
    assert "required_real_context_default" in setup_text
    assert "security_master" in setup_text
    assert "group_membership" in setup_text
    _assert_repo_root_resolution_snippet(fetcher_text)

    cutoff = generate_data_fetcher(
        {"provider": "manual_csv", "tier": "tier_d_manual_csv", "decision": "data_required_cutoff"},
        tmp_path / "cutoff_case",
        symbol="000001.SZ",
    )
    assert cutoff["decision"] == "data_required_cutoff"
    assert (tmp_path / "cutoff_case" / "data" / "fetch_data.py").exists() is False
    assert (tmp_path / "cutoff_case" / "data" / "provider_choice.json").exists()
    assert (tmp_path / "cutoff_case" / "data" / "provider_setup.md").exists()


def test_codegen_supports_all_real_provider_templates(tmp_path: Path):
    for provider_name in ["akshare", "efinance", "adata", "baostock", "tushare", "jqdatasdk"]:
        out_dir = tmp_path / provider_name
        result = generate_data_fetcher(
            {
                "provider": provider_name,
                "tier": "tier_a_no_auth" if provider_name in {"akshare", "efinance", "adata", "baostock"} else "tier_b_auth_or_trial",
                "decision": "generated_fetcher",
                "auth": "none",
                "dependency": provider_name,
            },
            out_dir,
            symbol="000001.SZ",
            start_date="2021-01-01",
            end_date="2021-12-31",
        )
        assert result["decision"] == "generated_fetcher"
        fetcher_path = out_dir / "data" / "fetch_data.py"
        assert fetcher_path.exists()
        text = _assert_generated_fetcher_compiles(fetcher_path)
        assert f'PROVIDER_NAME = "{provider_name}"' in text
        assert 'DEFAULT_SYMBOL = "000001.SZ"' in text
        assert "normalize_to_duckdb" in text
        assert "persist_real_data_artifacts" in text
        assert "data_contract.json" in text
        _assert_repo_root_resolution_snippet(text)


def test_generated_fetcher_path_resolution_stays_out_of_generated_strategies_skills(tmp_path: Path):
    repo_root = tmp_path / "repo"
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    script_root = repo_root / "skills" / "quant-oral-to-code" / "scripts"
    script_root.mkdir(parents=True, exist_ok=True)
    (script_root / "normalize_to_duckdb.py").write_text(
        "def normalize_to_duckdb(*args, **kwargs):\n"
        "    return {'source': 'real'}\n",
        encoding="utf-8",
    )
    (script_root / "context_data_helpers.py").write_text(
        "def persist_real_data_artifacts(*args, **kwargs):\n"
        "    return {'source': 'real_helper'}\n",
        encoding="utf-8",
    )

    workspace = repo_root / "generated_strategies" / "ma_demo"
    fake_script_root = repo_root / "generated_strategies" / "skills" / "quant-oral-to-code" / "scripts"
    fake_script_root.mkdir(parents=True, exist_ok=True)
    (fake_script_root / "normalize_to_duckdb.py").write_text(
        "def normalize_to_duckdb(*args, **kwargs):\n"
        "    return {'source': 'fake'}\n",
        encoding="utf-8",
    )
    (fake_script_root / "context_data_helpers.py").write_text(
        "def persist_real_data_artifacts(*args, **kwargs):\n"
        "    return {'source': 'fake_helper'}\n",
        encoding="utf-8",
    )

    result = generate_data_fetcher(
        {
            "provider": "akshare",
            "tier": "tier_a_no_auth",
            "decision": "generated_fetcher",
            "auth": "none",
            "dependency": "akshare",
        },
        workspace,
        symbol="000001.SZ",
    )

    assert result["decision"] == "generated_fetcher"
    fetcher_path = workspace / "data" / "fetch_data.py"
    fetcher_text = fetcher_path.read_text(encoding="utf-8")
    _assert_repo_root_resolution_snippet(fetcher_text)
    module = _execute_generated_fetcher_module(fetcher_path)

    assert module.WORKSPACE_ROOT == workspace
    assert module.REPO_ROOT == repo_root
    assert module.SCRIPT_ROOT == script_root
    assert module.SCRIPT_ROOT.parts[-3:] == ("skills", "quant-oral-to-code", "scripts")
    assert module.SCRIPT_ROOT != fake_script_root
    assert module.normalize_to_duckdb() == {"source": "real"}
    assert module.persist_real_data_artifacts() == {"source": "real_helper"}
