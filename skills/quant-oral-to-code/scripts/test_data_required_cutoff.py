from __future__ import annotations

from pathlib import Path

import duckdb

from build_claim_report import build_claim_report
from build_data_contract import build_data_contract
from review_guardrails import review_guardrails


def _create_market_duckdb(db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            create table bars (
                symbol varchar,
                trade_date date,
                open double,
                high double,
                low double,
                close double,
                volume double
            )
            """
        )
        con.execute(
            """
            insert into bars values
            ('000001.SZ', '2024-01-02', 10, 11, 9, 10.5, 1000)
            """
        )
    finally:
        con.close()
    return db_path


def test_data_required_cutoff_when_guardrail_has_blocking(tmp_path: Path):
    review = review_guardrails(
        {
            "source_prompt": "用 PE 选股并在全样本上调到最好，收盘买入。",
            "translation_confidence": 0.52,
            "unresolved_terms": ["强势"],
            "execution_requirements": {"execution_mode": "same_bar_close"},
        }
    )

    db_path = _create_market_duckdb(tmp_path / "blocked_case.duckdb")
    claim = build_claim_report(
        review=review,
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=build_data_contract(
            storage_target=db_path,
            raw_input_format="csv",
            provider_name="manual_csv",
            adjustment_mode="qfq",
            context_tables={
                "security_master": {"available": True, "source": "test_fixture"},
                "st_status": {"available": True, "source": "test_fixture"},
                "suspension_status": {"available": True, "source": "test_fixture"},
            },
            sample_coverage={"selection_method": "multi_symbol_fixture"},
        ),
        spec={"market": "A股"},
    )

    assert review["blocking"]
    assert claim["artifact_policy"] == "data_required_cutoff"
    assert claim["decision"] == "cutoff"
    assert any(str(reason).startswith("guardrail_blocking:") for reason in claim["reasons"])


def test_data_required_cutoff_when_future_leakage_blocking_is_triggered(tmp_path: Path):
    review = review_guardrails(
        {
            "source_prompt": "当天收盘最终站稳、次日还有溢价才算有效，然后当日收盘就进。",
            "translation_confidence": 0.91,
            "unresolved_terms": [],
        }
    )

    db_path = _create_market_duckdb(tmp_path / "future_leakage_case.duckdb")
    claim = build_claim_report(
        review=review,
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=build_data_contract(
            storage_target=db_path,
            raw_input_format="csv",
            provider_name="manual_csv",
            adjustment_mode="qfq",
            context_tables={
                "security_master": {"available": True, "source": "test_fixture"},
                "st_status": {"available": True, "source": "test_fixture"},
                "suspension_status": {"available": True, "source": "test_fixture"},
            },
            sample_coverage={"selection_method": "multi_symbol_fixture"},
        ),
        spec={"market": "A股"},
    )

    assert "future_leakage_or_hindsight_filtering" in review["blocking"]
    assert claim["artifact_policy"] == "data_required_cutoff"
    assert claim["decision"] == "cutoff"
    assert "guardrail_blocking:future_leakage_or_hindsight_filtering" in claim["reasons"]


def test_full_workspace_when_guardrail_is_clean_and_data_ready(tmp_path: Path):
    review = review_guardrails(
        {
            "source_prompt": "A股日线 5 日均线上穿 20 日均线，次日开盘成交，样本外验证。",
            "translation_confidence": 0.9,
            "unresolved_terms": [],
            "execution": {"mode": "next_open"},
            "validation": {
                "has_holdout": True,
                "sample_split": {
                    "train": "2018-01-01/2022-12-31",
                    "test": "2023-01-01/2024-12-31"
                }
            }
        }
    )

    db_path = _create_market_duckdb(tmp_path / "ready_case.duckdb")
    claim = build_claim_report(
        review=review,
        data_profile={"mode": "portable_csv_mode", "data_readiness": "ready"},
        data_contract=build_data_contract(
            storage_target=db_path,
            raw_input_format="csv",
            provider_name="manual_csv",
            adjustment_mode="qfq",
            context_tables={
                "security_master": {"available": True, "source": "test_fixture"},
                "st_status": {"available": True, "source": "test_fixture"},
                "suspension_status": {"available": True, "source": "test_fixture"},
            },
            sample_coverage={"selection_method": "multi_symbol_fixture"},
        ),
        spec={"market": "A股"},
    )

    assert review["blocking"] == []
    assert claim["artifact_policy"] == "full_workspace"
    assert claim["decision"] == "runnable"
    assert claim["claim_level"] == "portable_backtest"
