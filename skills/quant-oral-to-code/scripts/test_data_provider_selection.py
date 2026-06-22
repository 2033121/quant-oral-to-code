from __future__ import annotations

from select_data_provider import select_data_provider


def test_provider_selection_and_cutoff_artifacts_are_different():
    provider = select_data_provider(
        {
            "needs_history_bars": True,
            "user_prefers_zero_setup": True,
            "user_can_register_account": False,
        }
    )
    assert provider["provider"] == "akshare"
    assert provider["tier"] == "tier_a_no_auth"
    assert provider["decision"] == "generated_fetcher"


def test_provider_selection_supports_all_required_routes():
    assert select_data_provider({"preferred_provider": "akshare"})["provider"] == "akshare"
    assert select_data_provider({"preferred_provider": "efinance"})["provider"] == "efinance"
    assert select_data_provider({"preferred_provider": "adata"})["provider"] == "adata"
    assert select_data_provider({"preferred_provider": "baostock"})["provider"] == "baostock"
    assert select_data_provider({"preferred_provider": "tushare"})["provider"] == "tushare"
    assert select_data_provider({"preferred_provider": "jqdatasdk"})["provider"] == "jqdatasdk"

    manual = select_data_provider({"preferred_provider": "manual_csv"})
    assert manual["provider"] == "manual_csv"
    assert manual["decision"] == "data_required_cutoff"


def test_provider_selection_can_upgrade_to_authenticated_sources():
    tushare = select_data_provider(
        {
            "needs_history_bars": True,
            "user_can_register_account": True,
            "prefers_authenticated_provider": True,
            "has_tushare_token": True,
        }
    )
    assert tushare["provider"] == "tushare"
    assert tushare["decision"] == "generated_fetcher"

    jqdata = select_data_provider(
        {
            "needs_history_bars": True,
            "user_can_register_account": True,
            "prefers_authenticated_provider": True,
            "has_jq_credentials": True,
        }
    )
    assert jqdata["provider"] == "jqdatasdk"
