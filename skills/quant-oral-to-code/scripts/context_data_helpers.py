from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import duckdb
import pandas as pd


SCRIPT_ROOT = Path(__file__).resolve().parent
CONTEXT_TABLE_ORDER = [
    "security_master",
    "st_status",
    "suspension_status",
    "group_membership",
    "benchmark_series",
]


def _load_build_data_contract():
    module_path = SCRIPT_ROOT / "build_data_contract.py"
    spec = importlib.util.spec_from_file_location(
        "quant_oral_to_code_build_data_contract",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load build_data_contract from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_data_contract


build_data_contract = _load_build_data_contract()


def _to_dataframe(value: object) -> pd.DataFrame | None:
    if value is None:
        return None
    if isinstance(value, pd.DataFrame):
        frame = value.copy()
    elif isinstance(value, list):
        frame = pd.DataFrame(value)
    elif isinstance(value, dict):
        frame = pd.DataFrame([value])
    else:
        raise TypeError(f"Unsupported context payload type: {type(value).__name__}")
    if frame.empty:
        return None
    return frame.reset_index(drop=True)


def normalize_context_payload(context_payload: dict[str, object] | None) -> dict[str, pd.DataFrame | None]:
    payload = context_payload or {}
    normalized: dict[str, pd.DataFrame | None] = {}
    for context_key in CONTEXT_TABLE_ORDER:
        normalized[context_key] = _to_dataframe(payload.get(context_key))
    return normalized


def write_context_tables_to_duckdb(
    storage_target: str | Path,
    context_payload: dict[str, object] | None,
) -> dict[str, pd.DataFrame | None]:
    target_path = Path(storage_target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_context_payload(context_payload)
    conn = duckdb.connect(str(target_path))
    try:
        for context_key in CONTEXT_TABLE_ORDER:
            conn.execute(f'DROP TABLE IF EXISTS "{context_key}"')
            frame = normalized[context_key]
            if frame is None:
                continue
            relation_name = f"tmp_{context_key}"
            conn.register(relation_name, frame)
            conn.execute(f'CREATE TABLE "{context_key}" AS SELECT * FROM "{relation_name}"')
            conn.unregister(relation_name)
    finally:
        conn.close()
    return normalized


def build_context_tables_metadata(
    normalized_context_payload: dict[str, pd.DataFrame | None],
    provider_name: str,
    provider_support: dict[str, bool] | None = None,
    benchmark_code: str | None = None,
) -> dict[str, object]:
    support = provider_support or {}
    metadata: dict[str, object] = {}
    for context_key in CONTEXT_TABLE_ORDER:
        frame = normalized_context_payload.get(context_key)
        available = frame is not None and not frame.empty
        item: dict[str, object] = {
            "available": available,
            "table_name": context_key if available else None,
            "row_count": int(len(frame)) if available and frame is not None else 0,
            "source": provider_name,
            "provider_declares_support": bool(support.get(context_key, False)),
        }
        if context_key == "benchmark_series" and benchmark_code:
            item["benchmark_code"] = benchmark_code
        if not available:
            item["unavailable_reason"] = (
                "provider_capability_missing"
                if not support.get(context_key, False)
                else "provider_returned_no_rows"
            )
        metadata[context_key] = item
    return metadata


def build_sample_coverage(
    storage_target: str | Path,
    selection_method: str | None = None,
    universe_name: str | None = None,
) -> dict[str, object]:
    conn = duckdb.connect(str(storage_target), read_only=True)
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                COUNT(DISTINCT symbol) AS symbol_count,
                MIN(trade_date)::VARCHAR AS start_date,
                MAX(trade_date)::VARCHAR AS end_date
            FROM bars
            """
        ).fetchone()
    finally:
        conn.close()

    row_count = int(row[0] or 0)
    symbol_count = int(row[1] or 0)
    resolved_selection_method = selection_method or (
        "multi_symbol_api" if symbol_count > 1 else "single_symbol_manual"
    )
    return {
        "selection_method": resolved_selection_method,
        "symbol_count": symbol_count,
        "row_count": row_count,
        "start_date": row[2],
        "end_date": row[3],
        "universe_name": universe_name,
    }


def persist_real_data_artifacts(
    storage_target: str | Path,
    raw_input_format: str,
    provider_name: str,
    adjustment_mode: str,
    context_payload: dict[str, object] | None,
    provider_support: dict[str, bool] | None,
    selection_method: str | None,
    contract_output_path: str | Path,
    context_report_output_path: str | Path,
    benchmark_code: str | None = None,
    universe_name: str | None = None,
) -> dict[str, object]:
    normalized = write_context_tables_to_duckdb(storage_target, context_payload)
    context_tables = build_context_tables_metadata(
        normalized,
        provider_name=provider_name,
        provider_support=provider_support,
        benchmark_code=benchmark_code,
    )
    sample_coverage = build_sample_coverage(
        storage_target,
        selection_method=selection_method,
        universe_name=universe_name,
    )
    contract = build_data_contract(
        storage_target=storage_target,
        raw_input_format=raw_input_format,
        provider_name=provider_name,
        adjustment_mode=adjustment_mode,
        context_tables=context_tables,
        sample_coverage=sample_coverage,
    )
    contract_path = Path(contract_output_path)
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "provider_name": provider_name,
        "storage_target": str(storage_target),
        "context_tables": context_tables,
        "sample_coverage": sample_coverage,
    }
    context_report_path = Path(context_report_output_path)
    context_report_path.parent.mkdir(parents=True, exist_ok=True)
    context_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "context_tables": context_tables,
        "sample_coverage": sample_coverage,
        "data_contract": contract,
        "data_contract_file": str(contract_path),
        "context_report_file": str(context_report_path),
    }
