from resolve_codegen_mode import resolve_codegen_mode


def test_codegen_mode_defaults_to_standalone_generated():
    spec = {
        "strategy_family": "trend_basic",
        "entry_rules": [{"kind": "moving_average_cross", "fast": 5, "slow": 20}],
    }
    mode = resolve_codegen_mode(spec)
    assert mode["mode"] == "standalone_generated"
    assert mode["template"] == "single_asset_strategy.py.tmpl"
    assert "standalone_mapped" in mode["supports_future_modes"]
