from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from build_data_contract import build_data_contract
from check_runtime_capabilities import check_runtime_capabilities
from emit_artifact_manifest import validate_artifact_manifest


ROOT = Path(__file__).resolve().parents[1]

MODULE_TITLES = {
    "modules/preflight.md": "# preflight",
    "modules/intake.md": "# intake",
    "modules/dsl.md": "# dsl",
    "modules/guardrails.md": "# guardrails",
    "modules/data.md": "# data",
    "modules/codegen.md": "# codegen",
    "modules/onboarding.md": "# onboarding",
    "modules/report.md": "# report",
}

MODULE_PATHS = list(MODULE_TITLES.keys())

DOC_PATHS = [
    "docs/2026-06-22-quant-oral-to-code.md",
    "docs/2026-06-22-a-share-data-sources.md",
]

AGENT_METADATA_PATHS = [
    "agents/openai.yaml",
]

TASK2_SCHEMA_PATHS = [
    "schemas/preflight_report.schema.json",
    "schemas/data_profile.schema.json",
    "schemas/data_contract.schema.json",
    "schemas/claim_report.schema.json",
    "schemas/generated_artifact_manifest.schema.json",
    "schemas/experiment_protocol.schema.json",
]

TASK2_SCRIPT_PATHS = [
    "scripts/resolve_repo_root.py",
    "scripts/build_disambiguation_pack.py",
    "scripts/apply_disambiguation_answers.py",
    "scripts/check_runtime_capabilities.py",
    "scripts/build_release_bundle.py",
    "scripts/build_data_contract.py",
    "scripts/build_claim_report.py",
    "scripts/emit_artifact_manifest.py",
    "scripts/render_beginner_readme.py",
    "scripts/run_disambiguation_flow.py",
    "scripts/test_preflight.py",
    "scripts/test_data_contract.py",
    "scripts/test_claim_gate.py",
    "scripts/test_artifact_manifest.py",
    "scripts/test_disambiguation_flow.py",
    "scripts/render_disambiguation_questions.py",
    "scripts/test_build_release_bundle.py",
    "scripts/test_render_disambiguation_questions.py",
    "scripts/test_full_validation_disambiguation.py",
    "scripts/test_run_disambiguation_flow.py",
]

REQUIRED_FILES = [
    ROOT / "SKILL.md",
    *[ROOT / relative_path for relative_path in DOC_PATHS],
    *[ROOT / relative_path for relative_path in AGENT_METADATA_PATHS],
    *[ROOT / relative_path for relative_path in MODULE_PATHS],
    *[ROOT / relative_path for relative_path in TASK2_SCHEMA_PATHS],
    *[ROOT / relative_path for relative_path in TASK2_SCRIPT_PATHS],
    ROOT / "scripts" / "validate_quant_oral_to_code.py",
    ROOT / "scripts" / "test_skill_layout.py",
    ROOT / "references" / "term_disambiguation_library.json",
]


def _check_file(path: Path) -> dict[str, object]:
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    non_empty = size > 0
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": exists,
        "non_empty": non_empty,
        "size_bytes": size,
    }


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") and "\n---\n" in text


def _module_content_checks() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for relative_path, expected_heading in MODULE_TITLES.items():
        file_path = ROOT / relative_path
        text = _read_text(file_path)
        checks.append(
            {
                "path": relative_path,
                "rule": "has_expected_heading",
                "ok": bool(text.strip()) and expected_heading in text,
                "expected": expected_heading,
            }
        )
    return checks


def _skill_content_checks() -> list[dict[str, object]]:
    skill_path = ROOT / "SKILL.md"
    text = _read_text(skill_path)
    agent_yaml = _read_text(ROOT / "agents" / "openai.yaml")
    ordered_module_mentions = [text.find(relative_path) for relative_path in MODULE_PATHS]
    return [
        {
            "path": "SKILL.md",
            "rule": "has_frontmatter",
            "ok": _has_frontmatter(text),
            "expected": "frontmatter delimited by ---",
        },
        {
            "path": "SKILL.md",
            "rule": "has_name_field",
            "ok": "name:" in text,
            "expected": "name:",
        },
        {
            "path": "SKILL.md",
            "rule": "has_description_field",
            "ok": "description:" in text,
            "expected": "description:",
        },
        {
            "path": "SKILL.md",
            "rule": "has_argument_hint_field",
            "ok": "argument-hint:" in text,
            "expected": "argument-hint:",
        },
        {
            "path": "SKILL.md",
            "rule": "has_allowed_tools_field",
            "ok": "allowed-tools:" in text,
            "expected": "allowed-tools:",
        },
        *[
            {
                "path": "SKILL.md",
                "rule": "references_module_path",
                "ok": relative_path in text,
                "expected": relative_path,
            }
            for relative_path in MODULE_PATHS
        ],
        {
            "path": "SKILL.md",
            "rule": "mentions_duckdb_contract",
            "ok": "DuckDB" in text,
            "expected": "DuckDB",
        },
        {
            "path": "SKILL.md",
            "rule": "references_local_docs",
            "ok": "docs/2026-06-22-quant-oral-to-code.md" in text,
            "expected": "docs/2026-06-22-quant-oral-to-code.md",
        },
        {
            "path": "SKILL.md",
            "rule": "default_module_order_is_stable",
            "ok": all(index >= 0 for index in ordered_module_mentions)
            and ordered_module_mentions == sorted(ordered_module_mentions),
            "expected": "module paths appear in default read order",
        },
        {
            "path": "agents/openai.yaml",
            "rule": "has_display_name",
            "ok": "display_name:" in agent_yaml,
            "expected": "display_name:",
        },
        {
            "path": "agents/openai.yaml",
            "rule": "has_short_description",
            "ok": "short_description:" in agent_yaml,
            "expected": "short_description:",
        },
        {
            "path": "agents/openai.yaml",
            "rule": "has_default_prompt",
            "ok": "default_prompt:" in agent_yaml,
            "expected": "default_prompt:",
        },
    ]


def _semantic_checks() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    data_contract_schema = json.loads(
        (ROOT / "schemas" / "data_contract.schema.json").read_text(encoding="utf-8")
    )
    data_profile_schema = json.loads(
        (ROOT / "schemas" / "data_profile.schema.json").read_text(encoding="utf-8")
    )
    manifest_schema = json.loads(
        (ROOT / "schemas" / "generated_artifact_manifest.schema.json").read_text(encoding="utf-8")
    )
    preflight_schema = json.loads(
        (ROOT / "schemas" / "preflight_report.schema.json").read_text(encoding="utf-8")
    )
    claim_report_schema = json.loads(
        (ROOT / "schemas" / "claim_report.schema.json").read_text(encoding="utf-8")
    )

    bad_contract = {
        "storage_format": "duckdb",
        "storage_target": "generated_strategies/demo/data/normalized/market.duckdb",
        "bars_table_name": "bars",
        "table_layout": "partitioned",
        "primary_key": ["symbol", "trade_date"],
        "required_tables": ["bars"],
        "required_columns": ["symbol", "trade_date", "open", "high", "low", "close", "volume"],
        "write_disposition": "overwrite",
        "raw_input_format": "csv",
        "provider_name": "manual_csv",
        "adjustment_mode": "qfq",
        "data_hash": "x",
    }
    try:
        jsonschema.validate(bad_contract, data_contract_schema)
        contract_ok = False
    except jsonschema.ValidationError:
        contract_ok = True
    checks.append(
        {
            "path": "schemas/data_contract.schema.json",
            "rule": "rejects_non_single_table_layout",
            "ok": contract_ok,
            "expected": "table_layout must be single_table",
        }
    )

    bad_manifest = {
        "claim_level": "demo_only",
        "artifact_policy": "data_required_cutoff",
        "artifact_count": 1,
        "artifacts": [{"path": "strategy.py", "value": "bad", "kind": "generated_file"}],
    }
    try:
        jsonschema.validate(bad_manifest, manifest_schema)
        manifest_schema_ok = False
    except jsonschema.ValidationError:
        manifest_schema_ok = True
    checks.append(
        {
            "path": "schemas/generated_artifact_manifest.schema.json",
            "rule": "rejects_cutoff_runnable_artifact",
            "ok": manifest_schema_ok,
            "expected": "cutoff manifest paths must stay on whitelist",
        }
    )

    wrong_count_manifest = {
        "claim_level": "demo_only",
        "artifact_policy": "data_required_cutoff",
        "artifact_count": 2,
        "artifacts": [{"path": "claim_report.json", "value": "ok", "kind": "generated_file"}],
    }
    try:
        validate_artifact_manifest(wrong_count_manifest)
        manifest_semantic_ok = False
    except ValueError:
        manifest_semantic_ok = True
    checks.append(
        {
            "path": "scripts/emit_artifact_manifest.py",
            "rule": "rejects_wrong_artifact_count",
            "ok": manifest_semantic_ok,
            "expected": "artifact_count must equal len(artifacts)",
        }
    )

    missing_db = ROOT / "tmp" / "missing.duckdb"
    try:
        build_data_contract(
            storage_target=missing_db,
            raw_input_format="csv",
            provider_name="manual_csv",
            adjustment_mode="qfq",
        )
        missing_db_ok = False
    except FileNotFoundError:
        missing_db_ok = True
    checks.append(
        {
            "path": "scripts/build_data_contract.py",
            "rule": "rejects_missing_duckdb_storage_target",
            "ok": missing_db_ok,
            "expected": "build_data_contract should fail when duckdb file is missing",
        }
    )

    bad_null_hash_contract = {
        "storage_format": "duckdb",
        "storage_target": "generated_strategies/demo/data/normalized/market.duckdb",
        "bars_table_name": "bars",
        "table_layout": "single_table",
        "primary_key": ["symbol", "trade_date"],
        "required_tables": ["bars"],
        "required_columns": ["symbol", "trade_date", "open", "high", "low", "close", "volume"],
        "write_disposition": "overwrite",
        "raw_input_format": "csv",
        "provider_name": "manual_csv",
        "adjustment_mode": "qfq",
        "data_hash": None,
    }
    try:
        jsonschema.validate(bad_null_hash_contract, data_contract_schema)
        bad_null_hash_ok = False
    except jsonschema.ValidationError:
        bad_null_hash_ok = True
    checks.append(
        {
            "path": "schemas/data_contract.schema.json",
            "rule": "rejects_null_data_hash",
            "ok": bad_null_hash_ok,
            "expected": "data_hash must be non-empty string",
        }
    )

    bad_raw_input_contract = {
        "storage_format": "duckdb",
        "storage_target": "generated_strategies/demo/data/normalized/market.duckdb",
        "bars_table_name": "bars",
        "table_layout": "single_table",
        "primary_key": ["symbol", "trade_date"],
        "required_tables": ["bars"],
        "required_columns": ["symbol", "trade_date", "open", "high", "low", "close", "volume"],
        "write_disposition": "overwrite",
        "raw_input_format": "totally_fake_format",
        "provider_name": "manual_csv",
        "adjustment_mode": "qfq",
        "data_hash": "x",
    }
    try:
        jsonschema.validate(bad_raw_input_contract, data_contract_schema)
        bad_raw_input_ok = False
    except jsonschema.ValidationError:
        bad_raw_input_ok = True
    checks.append(
        {
            "path": "schemas/data_contract.schema.json",
            "rule": "rejects_invalid_raw_input_format",
            "ok": bad_raw_input_ok,
            "expected": "raw_input_format must be from the fixed enum",
        }
    )

    bad_profile = {
        "mode": "portable_csv_mode",
        "data_readiness": "ready",
        "raw_input_format": "totally_fake_format",
        "provider_name": "manual_csv",
    }
    try:
        jsonschema.validate(bad_profile, data_profile_schema)
        bad_profile_ok = False
    except jsonschema.ValidationError:
        bad_profile_ok = True
    checks.append(
        {
            "path": "schemas/data_profile.schema.json",
            "rule": "rejects_invalid_profile_raw_input_format",
            "ok": bad_profile_ok,
            "expected": "data_profile raw_input_format must be from the fixed enum",
        }
    )

    preflight = check_runtime_capabilities(ROOT)
    try:
        jsonschema.validate(preflight, preflight_schema)
        preflight_ok = True
    except jsonschema.ValidationError:
        preflight_ok = False
    checks.append(
        {
            "path": "schemas/preflight_report.schema.json",
            "rule": "accepts_runtime_capabilities_output",
            "ok": preflight_ok,
            "expected": "check_runtime_capabilities output should satisfy preflight schema",
        }
    )

    inconsistent_claim = {
        "claim_level": "portable_backtest",
        "artifact_policy": "full_workspace",
        "decision": "cutoff",
        "reasons": [],
        "review_summary": {},
        "data_summary": {},
    }
    try:
        jsonschema.validate(inconsistent_claim, claim_report_schema)
        inconsistent_claim_ok = False
    except jsonschema.ValidationError:
        inconsistent_claim_ok = True
    checks.append(
        {
            "path": "schemas/claim_report.schema.json",
            "rule": "rejects_inconsistent_artifact_policy_and_decision",
            "ok": inconsistent_claim_ok,
            "expected": "full_workspace must pair with decision=runnable",
        }
    )

    inconsistent_cutoff_claim = {
        "claim_level": "portable_backtest",
        "artifact_policy": "data_required_cutoff",
        "decision": "runnable",
        "reasons": [],
        "review_summary": {},
        "data_summary": {},
    }
    try:
        jsonschema.validate(inconsistent_cutoff_claim, claim_report_schema)
        inconsistent_cutoff_ok = False
    except jsonschema.ValidationError:
        inconsistent_cutoff_ok = True
    checks.append(
        {
            "path": "schemas/claim_report.schema.json",
            "rule": "rejects_cutoff_with_runnable_decision",
            "ok": inconsistent_cutoff_ok,
            "expected": "data_required_cutoff must pair with decision=cutoff",
        }
    )
    return checks


def build_validation_report() -> dict[str, object]:
    file_checks = [_check_file(path) for path in REQUIRED_FILES]
    content_checks = _skill_content_checks() + _module_content_checks() + _semantic_checks()
    missing = [item["path"] for item in file_checks if not item["exists"]]
    empty = [item["path"] for item in file_checks if item["exists"] and not item["non_empty"]]
    failed_content_checks = [item for item in content_checks if not item["ok"]]
    ok = not missing and not empty and not failed_content_checks
    return {
        "ok": ok,
        "skill": "quant-oral-to-code",
        "root": str(ROOT),
        "required_count": len(REQUIRED_FILES),
        "checks": {
            "files": file_checks,
            "content": content_checks,
        },
        "missing": missing,
        "empty": empty,
        "failed_content_checks": failed_content_checks,
    }


def main() -> int:
    report = build_validation_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
