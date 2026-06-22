from __future__ import annotations

from pathlib import Path

import duckdb
from build_data_contract import ALLOWED_RAW_INPUT_FORMATS, compute_data_hash


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
]


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


def _determine_claim_level(
    data_profile: dict[str, object],
    has_duckdb_contract: bool,
) -> str:
    mode = data_profile.get("mode")
    readiness = data_profile.get("data_readiness")
    if mode == "full_research_mode" and readiness == "ready" and has_duckdb_contract:
        return "research_grade_local"
    if mode == "portable_csv_mode" and readiness == "ready" and has_duckdb_contract:
        return "portable_backtest"
    return "demo_only"


def build_claim_report(
    review: dict[str, object],
    data_profile: dict[str, object],
    data_contract: dict[str, object] | None,
) -> dict[str, object]:
    blocking = list(review.get("blocking", []))
    warnings = list(review.get("warnings", []))
    readiness = data_profile.get("data_readiness")
    mode = data_profile.get("mode")

    has_duckdb_contract, contract_reasons = _inspect_duckdb_contract(data_contract)
    claim_level = _determine_claim_level(data_profile, has_duckdb_contract)

    reasons: list[str] = []
    if blocking:
        reasons.extend([f"guardrail_blocking:{item}" for item in blocking])
    if readiness != "ready":
        reasons.append(f"data_readiness:{readiness}")
    if not has_duckdb_contract:
        reasons.extend(contract_reasons or ["duckdb_contract_incomplete"])

    if blocking or readiness != "ready" or not has_duckdb_contract:
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
