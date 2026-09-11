from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from emit_artifact_manifest import emit_artifact_manifest, validate_artifact_manifest


def _load_schema() -> dict[str, object]:
    return json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "generated_artifact_manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )


def test_cutoff_manifest_accepts_only_cutoff_whitelist():
    manifest = emit_artifact_manifest(
        {
            "strategy_spec.json": "ok",
            "translation_trace.json": "ok",
            "disambiguation_pack.json": "ok",
            "disambiguation_answers.json": "ok",
            "data_contract.json": "ok",
            "claim_report.json": "ok",
            "README_beginner.md": "ok",
            "data/provider_choice.json": "ok",
        },
        claim_level="demo_only",
        artifact_policy="data_required_cutoff",
    )
    assert manifest["artifact_policy"] == "data_required_cutoff"
    assert manifest["artifact_count"] == 8


def test_cutoff_manifest_rejects_strategy_py():
    bad_manifest = {
        "claim_level": "demo_only",
        "artifact_policy": "data_required_cutoff",
        "artifact_count": 1,
        "artifacts": [{"path": "strategy.py", "value": "bad", "kind": "generated_file"}],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad_manifest, _load_schema())
    with pytest.raises(ValueError):
        validate_artifact_manifest(bad_manifest)


def test_cutoff_manifest_rejects_protocol_and_normalized_data():
    for bad_path in ["experiment_protocol.json", "data/normalized/market.duckdb"]:
        bad_manifest = {
            "claim_level": "demo_only",
            "artifact_policy": "data_required_cutoff",
            "artifact_count": 1,
            "artifacts": [{"path": bad_path, "value": "bad", "kind": "generated_file"}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad_manifest, _load_schema())
        with pytest.raises(ValueError):
            validate_artifact_manifest(bad_manifest)


def test_cutoff_manifest_rejects_wrong_artifact_count_semantically():
    manifest = emit_artifact_manifest(
        {"claim_report.json": "ok"},
        claim_level="demo_only",
        artifact_policy="data_required_cutoff",
    )
    manifest["artifact_count"] = 2
    with pytest.raises(ValueError):
        validate_artifact_manifest(manifest)


def test_full_workspace_manifest_accepts_runnable_artifacts():
    manifest = emit_artifact_manifest(
        {
            "strategy.py": "ok",
            "run_backtest.py": "ok",
            "results/metrics_snapshot.json": "ok",
        },
        claim_level="portable_backtest",
        artifact_policy="full_workspace",
    )
    jsonschema.validate(manifest, _load_schema())
    assert manifest["artifact_policy"] == "full_workspace"
    assert manifest["artifact_count"] == 3


def test_manifest_accepts_artifact_list_and_normalizes_windows_paths():
    manifest = emit_artifact_manifest(
        [
            {"path": r"results\result_summary.md", "value": "ok", "kind": "report"},
            {"path": r"results\equity_curve.png", "value": {"exists": True}},
        ],
        claim_level="portable_backtest",
        artifact_policy="full_workspace",
    )

    jsonschema.validate(manifest, _load_schema())
    assert manifest["artifact_count"] == 2
    assert manifest["artifacts"][0]["path"] == "results/result_summary.md"
    assert manifest["artifacts"][0]["kind"] == "report"
    assert manifest["artifacts"][1]["path"] == "results/equity_curve.png"
    assert manifest["artifacts"][1]["kind"] == "generated_file"


def test_cutoff_manifest_rejects_list_entry_outside_whitelist():
    with pytest.raises(ValueError):
        emit_artifact_manifest(
            [{"path": "results/result_summary.md", "value": "bad"}],
            claim_level="demo_only",
            artifact_policy="data_required_cutoff",
        )
