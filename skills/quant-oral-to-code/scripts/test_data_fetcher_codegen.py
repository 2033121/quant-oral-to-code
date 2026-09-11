from __future__ import annotations

from pathlib import Path

from generate_data_fetcher import generate_data_fetcher
from select_data_provider import select_data_provider


EXPECTED_RUNTIME_SUPPORT = {
    "normalize_to_duckdb.py",
    "context_data_helpers.py",
    "build_data_contract.py",
    "validate_fetched_dataset.py",
}


def _assert_local_runtime_snippet(fetcher_text: str) -> None:
    assert "from context_data_helpers import persist_real_data_artifacts" in fetcher_text
    assert "from normalize_to_duckdb import normalize_to_duckdb" in fetcher_text
    assert "from validate_fetched_dataset import validate_fetched_dataset" in fetcher_text
    assert "validation = validate_fetched_dataset(DUCKDB_OUTPUT)" in fetcher_text
    assert "dataset_validation" in fetcher_text
    assert "def _resolve_repo_root() -> Path:" not in fetcher_text
    assert "importlib.util" not in fetcher_text
    assert 'SCRIPT_ROOT = REPO_ROOT / "skills" / "quant-oral-to-code" / "scripts"' not in fetcher_text


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
    assert EXPECTED_RUNTIME_SUPPORT.issubset(
        {Path(path).name for path in generated["runtime_support_files"]}
    )

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
    _assert_local_runtime_snippet(fetcher_text)

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
        assert EXPECTED_RUNTIME_SUPPORT.issubset(
            {path.name for path in (out_dir / "data").iterdir() if path.is_file()}
        )
        _assert_local_runtime_snippet(text)
