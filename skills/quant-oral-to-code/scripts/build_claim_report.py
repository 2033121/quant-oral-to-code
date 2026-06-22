from __future__ import annotations

from pathlib import Path

import duckdb
from build_data_contract import ALLOWED_RAW_INPUT_FORMATS, compute_data_hash
from resolve_required_context import resolve_required_context


REQUIRED_BARS_COLUMNS = {
    "symbol",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
}
NUMERIC_BARS_COLUMNS = ("open", "high", "low", "close", "volume")
REQUIRED_CONTRACT_FIELDS = [
    "storage_format",
    "storage_target",
    "bars_table_name",
    "table_layout",
    "primary_key",
    "required_tables",
    "required_columns",
    "write_disposition",
    "raw_input_format",
    "provider_name",
    "adjustment_mode",
    "data_hash",
    "context_tables",
    "sample_coverage",
]
RESEARCH_EVIDENCE_REQUIREMENTS = {
    "has_oos_validation": "missing_oos_validation",
    "has_pit_data": "missing_pit_data",
    "has_cost_model": "missing_cost_model",
    "has_real_equity_curve": "missing_real_equity_curve",
}


def _inspect_duckdb_contract(data_contract: dict[str, object] | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not data_contract:
        return False, ["duckdb_contract_missing"]
    for field_name in REQUIRED_CONTRACT_FIELDS:
        value = data_contract.get(field_name)
        if value is None or value == "":
            reasons.append(f"contract_field_missing:{field_name}")
    if data_contract.get("storage_format") != "duckdb":
        reasons.append("storage_format_not_duckdb")
    if data_contract.get("bars_table_name") != "bars":
        reasons.append("bars_table_name_invalid")
    if data_contract.get("table_layout") != "single_table":
        reasons.append("table_layout_invalid")
    if data_contract.get("primary_key") != ["symbol", "trade_date"]:
        reasons.append("primary_key_invalid")
    required_tables = data_contract.get("required_tables")
    if not isinstance(required_tables, list) or "bars" not in required_tables:
        reasons.append("required_tables_missing_bars")
    required_columns = data_contract.get("required_columns")
    if not isinstance(required_columns, list):
        reasons.append("required_columns_invalid")
    else:
        missing_contract_columns = sorted(REQUIRED_BARS_COLUMNS - set(required_columns))
        if missing_contract_columns:
            reasons.append(
                "required_columns_missing:" + ",".join(missing_contract_columns)
            )
    if data_contract.get("write_disposition") not in {"overwrite", "append", "upsert"}:
        reasons.append("write_disposition_invalid")
    if data_contract.get("raw_input_format") not in ALLOWED_RAW_INPUT_FORMATS:
        reasons.append("raw_input_format_invalid")
    if data_contract.get("adjustment_mode") not in {"none", "qfq", "hfq"}:
        reasons.append("adjustment_mode_invalid")

    storage_target = data_contract.get("storage_target")
    if not storage_target:
        reasons.append("storage_target_missing")
        return False, reasons

    db_path = Path(str(storage_target))
    if not db_path.exists():
        reasons.append("storage_target_missing_on_disk")
        return False, reasons

    expected_hash = str(data_contract.get("data_hash", ""))
    try:
        actual_hash = compute_data_hash(
            db_path,
            raw_input_format=str(data_contract.get("raw_input_format", "")),
            provider_name=str(data_contract.get("provider_name", "")),
            adjustment_mode=str(data_contract.get("adjustment_mode", "")),
        )
        if expected_hash != actual_hash:
            reasons.append("data_hash_mismatch")
    except FileNotFoundError:
        reasons.append("storage_target_missing_on_disk")
        return False, reasons

    try:
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            table_exists = con.execute(
                "select count(*) from information_schema.tables where table_name = 'bars'"
            ).fetchone()[0]
            if not table_exists:
                reasons.append("bars_table_missing")
                return False, reasons

            rows = con.execute("pragma table_info('bars')").fetchall()
            column_names = {str(row[1]) for row in rows}
            missing_columns = sorted(REQUIRED_BARS_COLUMNS - column_names)
            if missing_columns:
                reasons.append(f"bars_columns_missing:{','.join(missing_columns)}")
                return False, reasons

            for column_name in sorted(REQUIRED_BARS_COLUMNS):
                null_count = con.execute(
                    f'SELECT COUNT(*) FROM "bars" WHERE "{column_name}" IS NULL'
                ).fetchone()[0]
                if null_count > 0:
                    reasons.append(
                        f"core_column_has_nulls:{column_name}:{int(null_count)}"
                    )

            duplicate_count = con.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT symbol, trade_date
                    FROM "bars"
                    GROUP BY symbol, trade_date
                    HAVING COUNT(*) > 1
                ) duplicate_rows
                """
            ).fetchone()[0]
            if duplicate_count > 0:
                reasons.append(
                    f"duplicate_symbol_trade_date_keys:{int(duplicate_count)}"
                )

            for column_name in NUMERIC_BARS_COLUMNS:
                non_finite_count = con.execute(
                    f'SELECT COUNT(*) FROM "bars" WHERE NOT isfinite("{column_name}")'
                ).fetchone()[0]
                if non_finite_count > 0:
                    reasons.append(
                        "numeric_column_has_non_finite_values:"
                        f"{column_name}:{int(non_finite_count)}"
                    )
        finally:
            con.close()
    except Exception as exc:
        reasons.append(f"duckdb_readonly_validation_failed:{type(exc).__name__}")
        return False, reasons

    return not reasons, reasons


def _evaluate_required_context_coverage(
    spec: dict[str, object] | None,
    data_profile: dict[str, object],
    data_contract: dict[str, object] | None,
) -> list[str]:
    resolved = resolve_required_context(spec if isinstance(spec, dict) else {})
    reasons: list[str] = []

    if data_profile.get("mode") == "demo_mode":
        reasons.append("real_data_required:demo_mode_forbidden")

    context_tables = {}
    if isinstance(data_contract, dict) and isinstance(data_contract.get("context_tables"), dict):
        context_tables = data_contract["context_tables"]

    for item in resolved.get("blocking_requirements", []):
        reasons.append(f"context_requirement_blocking:{item}")

    for context_key in resolved.get("required_context_keys", []):
        metadata = context_tables.get(context_key)
        if not isinstance(metadata, dict):
            reasons.append(f"context_table_missing:{context_key}")
            continue
        if metadata.get("available") is not True:
            reasons.append(f"context_table_unavailable:{context_key}")

    if resolved.get("requires_cross_sectional_universe") is True:
        sample_coverage = {}
        if isinstance(data_contract, dict) and isinstance(data_contract.get("sample_coverage"), dict):
            sample_coverage = data_contract["sample_coverage"]
        if sample_coverage.get("selection_method") in (None, "", "single_symbol_manual"):
            reasons.append("cross_sectional_universe_not_verified")

    return reasons


def _collect_research_evidence_gaps(
    data_profile: dict[str, object],
) -> list[str]:
    evidence = data_profile.get("research_evidence")
    if not isinstance(evidence, dict):
        return [f"research_evidence:{reason}" for reason in RESEARCH_EVIDENCE_REQUIREMENTS.values()]

    gaps: list[str] = []
    for field_name, reason in RESEARCH_EVIDENCE_REQUIREMENTS.items():
        if evidence.get(field_name) is not True:
            gaps.append(f"research_evidence:{reason}")
    return gaps


def _determine_claim_level(
    data_profile: dict[str, object],
    has_duckdb_contract: bool,
) -> tuple[str, list[str]]:
    mode = data_profile.get("mode")
    readiness = data_profile.get("data_readiness")
    if readiness == "ready" and has_duckdb_contract:
        if mode == "full_research_mode":
            research_gaps = _collect_research_evidence_gaps(data_profile)
            if not research_gaps:
                return "research_grade_local", []
            return "portable_backtest", [
                "claim_downgraded:research_grade_local_requires_explicit_evidence",
                *research_gaps,
            ]
        if mode == "portable_csv_mode":
            return "portable_backtest", []
        if mode == "demo_mode":
            return "demo_only", []
    return "demo_only", []


def build_claim_report(
    review: dict[str, object],
    data_profile: dict[str, object],
    data_contract: dict[str, object] | None,
    spec: dict[str, object] | None = None,
) -> dict[str, object]:
    blocking = list(review.get("blocking", []))
    warnings = list(review.get("warnings", []))
    readiness = data_profile.get("data_readiness")
    mode = data_profile.get("mode")

    has_duckdb_contract, contract_reasons = _inspect_duckdb_contract(data_contract)
    claim_level, claim_level_reasons = _determine_claim_level(
        data_profile, has_duckdb_contract
    )
    context_reasons = _evaluate_required_context_coverage(spec, data_profile, data_contract)

    reasons: list[str] = []
    if blocking:
        reasons.extend([f"guardrail_blocking:{item}" for item in blocking])
    if readiness != "ready":
        reasons.append(f"data_readiness:{readiness}")
    if not has_duckdb_contract:
        reasons.extend(contract_reasons or ["duckdb_contract_incomplete"])
    reasons.extend(context_reasons)
    reasons.extend(claim_level_reasons)

    if blocking or readiness != "ready" or not has_duckdb_contract or context_reasons:
        artifact_policy = "data_required_cutoff"
        decision = "cutoff"
    else:
        artifact_policy = "full_workspace"
        decision = "runnable"

    return {
        "claim_level": claim_level,
        "artifact_policy": artifact_policy,
        "decision": decision,
        "reasons": reasons,
        "review_summary": {
            "blocking": blocking,
            "warnings": warnings,
        },
        "data_summary": {
            "mode": mode,
            "data_readiness": readiness,
            "has_duckdb_contract": has_duckdb_contract,
            "required_context": resolve_required_context(spec if isinstance(spec, dict) else {}),
            "research_evidence": (
                data_profile.get("research_evidence")
                if isinstance(data_profile.get("research_evidence"), dict)
                else {}
            ),
        },
    }


if __name__ == "__main__":
    import json

    report = build_claim_report(
        review={"blocking": [], "warnings": []},
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract={
            "storage_format": "duckdb",
            "bars_table_name": "bars",
            "primary_key": ["symbol", "trade_date"],
            "data_hash": "example",
        },
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
