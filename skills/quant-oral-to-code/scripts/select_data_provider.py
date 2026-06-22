from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "references" / "data_access_matrix.json"


def _load_matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _provider_lookup() -> dict[str, dict[str, object]]:
    matrix = _load_matrix()
    return {
        str(item["name"]): item
        for item in matrix.get("providers", [])
    }


def _build_result(provider_name: str, decision: str | None = None, reason: str | None = None) -> dict[str, object]:
    provider = _provider_lookup()[provider_name]
    resolved_decision = decision or str(provider["decision_default"])
    return {
        "provider": provider_name,
        "tier": provider["tier"],
        "auth": provider["auth"],
        "dependency": provider["dependency"],
        "supports_history_bars": provider["supports_history_bars"],
        "supports_intraday": provider["supports_intraday"],
        "decision": resolved_decision,
        "reason": reason or provider["notes"],
    }


def select_data_provider(context: dict[str, object]) -> dict[str, object]:
    preferred_provider = str(context.get("preferred_provider", "") or "").strip().lower()
    needs_history_bars = bool(context.get("needs_history_bars", False))
    user_prefers_zero_setup = bool(context.get("user_prefers_zero_setup", False))
    user_can_register_account = bool(context.get("user_can_register_account", False))
    has_tushare_token = bool(context.get("has_tushare_token", False))
    has_jq_credentials = bool(context.get("has_jq_credentials", False))
    user_has_manual_csv = bool(context.get("user_has_manual_csv", False))
    prefers_authenticated_provider = bool(context.get("prefers_authenticated_provider", False))

    supported = _provider_lookup()
    if preferred_provider:
        if preferred_provider not in supported:
            raise ValueError(f"Unsupported provider: {preferred_provider}")
        if preferred_provider == "manual_csv":
            return _build_result(
                "manual_csv",
                decision="data_required_cutoff",
                reason="用户指定手工导入数据，需要先准备 CSV/Parquet 后再进入标准化链路。",
            )
        return _build_result(preferred_provider, reason="尊重用户显式指定的 provider。")

    if user_has_manual_csv and not needs_history_bars:
        return _build_result(
            "manual_csv",
            decision="data_required_cutoff",
            reason="当前上下文以手工导出文件为主，先进入 DATA_REQUIRED 截断并提示准备文件。",
        )

    if needs_history_bars:
        if user_prefers_zero_setup and not user_can_register_account:
            return _build_result(
                "akshare",
                decision="generated_fetcher",
                reason="满足零门槛历史行情优先规则，先走 AKShare。",
            )
        if prefers_authenticated_provider and has_tushare_token:
            return _build_result(
                "tushare",
                decision="generated_fetcher",
                reason="用户偏好认证源且已具备 TuShare token。",
            )
        if prefers_authenticated_provider and has_jq_credentials:
            return _build_result(
                "jqdatasdk",
                decision="generated_fetcher",
                reason="用户偏好认证源且已具备聚宽认证信息。",
            )
        if user_prefers_zero_setup or not user_can_register_account:
            return _build_result(
                "akshare",
                decision="generated_fetcher",
                reason="默认优先零门槛 provider。",
            )
        if has_tushare_token:
            return _build_result("tushare", decision="generated_fetcher", reason="已具备 TuShare token。")
        if has_jq_credentials:
            return _build_result("jqdatasdk", decision="generated_fetcher", reason="已具备 JQData 账号认证。")
        if user_can_register_account and prefers_authenticated_provider:
            return _build_result(
                "tushare",
                decision="generated_fetcher",
                reason="用户接受注册配置，优先走 TuShare 升级路线。",
            )
        return _build_result(
            "akshare",
            decision="generated_fetcher",
            reason="历史行情默认从零门槛公共源起步。",
        )

    if user_has_manual_csv:
        return _build_result(
            "manual_csv",
            decision="data_required_cutoff",
            reason="未要求直接生成 provider API fetcher，改走手工文件导入路线。",
        )

    return _build_result(
        "manual_csv",
        decision="data_required_cutoff",
        reason="缺少可自动获取的最小条件，进入 DATA_REQUIRED 截断。",
    )
