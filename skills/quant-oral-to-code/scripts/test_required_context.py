from __future__ import annotations

from resolve_required_context import resolve_required_context


def test_required_context_for_default_a_share_strategy_includes_st_and_suspension():
    resolved = resolve_required_context({"market": "\u0041\u80a1"})
    assert "security_master" in resolved["required_context_keys"]
    assert "st_status" in resolved["required_context_keys"]
    assert "suspension_status" in resolved["required_context_keys"]
    assert resolved["requires_real_data"] is True


def test_required_context_for_sector_resonance_requires_group_and_benchmark():
    resolved = resolve_required_context(
        {
            "market": "\u0041\u80a1",
            "selection_filters": [{"kind": "group_relative_strength", "lookback": 5}],
            "data_requirements": {"鏉垮潡鍏辨尟": ["group_membership", "benchmark_series"]},
        }
    )
    assert "group_membership" in resolved["required_context_keys"]
    assert "benchmark_series" in resolved["required_context_keys"]
    assert "cross_sectional_universe" not in resolved["required_context_keys"]
    assert resolved["requires_cross_sectional_universe"] is True
