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
        "supports_context_tables": provider.get("supports_context_tables", {}),
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
                reason="用户指定手工导入数据，但这条路径默认无法自动补齐真实上下文数据。",
            )
        return _build_result(preferred_provider, reason="尊重用户显式指定的数据提供方。")

    if user_has_manual_csv and not needs_history_bars:
        return _build_result(
            "manual_csv",
            decision="data_required_cutoff",
            reason="当前上下文以手工导出文件为主，先进入数据补齐截断并提示缺失上下文。",
        )

    if needs_history_bars:
        if user_prefers_zero_setup and not user_can_register_account:
            return _build_result(
                "akshare",
                decision="generated_fetcher",
                reason="优先满足零门槛历史行情获取，但这一路线通常仍需后续补齐 A 股上下文。",
            )
        if prefers_authenticated_provider and has_tushare_token:
            return _build_result(
                "tushare",
                decision="generated_fetcher",
                reason="用户接受认证且已有 TuShare token，适合直接拉完整上下文。",
            )
        if prefers_authenticated_provider and has_jq_credentials:
            return _build_result(
                "jqdatasdk",
                decision="generated_fetcher",
                reason="用户接受认证且已有聚宽凭证，适合直接拉完整上下文。",
            )
        if user_prefers_zero_setup or not user_can_register_account:
            return _build_result(
                "akshare",
                decision="generated_fetcher",
                reason="默认优先零门槛 provider，先保证行情获取成功。",
            )
        if has_tushare_token:
            return _build_result(
                "tushare",
                decision="generated_fetcher",
                reason="已具备 TuShare token，可直接进入完整数据获取路线。",
            )
        if has_jq_credentials:
            return _build_result(
                "jqdatasdk",
                decision="generated_fetcher",
                reason="已具备聚宽账号认证，可直接进入完整数据获取路线。",
            )
        if user_can_register_account and prefers_authenticated_provider:
            return _build_result(
                "tushare",
                decision="generated_fetcher",
                reason="用户接受注册配置，优先推荐可覆盖完整上下文的 TuShare。",
            )
        return _build_result(
            "akshare",
            decision="generated_fetcher",
            reason="历史行情默认从零门槛公共源起步，后续根据上下文缺口再升级 provider。",
        )

    if user_has_manual_csv:
        return _build_result(
            "manual_csv",
            decision="data_required_cutoff",
            reason="未要求实时生成 provider fetcher，保留为手工数据导入截断路径。",
        )

    return _build_result(
        "manual_csv",
        decision="data_required_cutoff",
        reason="缺少可自动获取真实数据的最小条件，进入 data_required_cutoff。",
    )
