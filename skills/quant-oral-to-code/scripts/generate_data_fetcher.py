from __future__ import annotations

import json
from pathlib import Path
from string import Template


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"
REFERENCE_NOTES = ROOT / "references" / "a_share_provider_notes.md"
TEMPLATE_MAP = {
    "akshare": "fetch_with_akshare.py.tmpl",
    "efinance": "fetch_with_efinance.py.tmpl",
    "adata": "fetch_with_adata.py.tmpl",
    "baostock": "fetch_with_baostock.py.tmpl",
    "tushare": "fetch_with_tushare.py.tmpl",
    "jqdatasdk": "fetch_with_jqdatasdk.py.tmpl",
}
AUTH_HINTS = {
    "none": "无需认证，安装依赖后即可运行。",
    "anonymous": "匿名登录，无需注册账号，但仍依赖 provider 当前可用。",
    "token": "需要先准备 token，推荐通过环境变量注入。",
    "username_password": "需要先准备用户名和密码，推荐通过环境变量注入。",
    "manual_export": "需要用户手工导出 CSV 或 Parquet，再进入标准化链路。",
}


def _render_template(template_name: str, context: dict[str, str]) -> str:
    template_path = TEMPLATE_DIR / template_name
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.substitute(context)


def _build_setup_text(provider: dict[str, object], symbol: str, start_date: str, end_date: str) -> str:
    auth_method = str(provider.get("auth", "unknown"))
    dependency = str(provider.get("dependency", "unknown"))
    notes = REFERENCE_NOTES.read_text(encoding="utf-8")
    summary_lines = [
        "# Provider Setup",
        "",
        f"- provider: {provider['provider']}",
        f"- tier: {provider['tier']}",
        f"- decision: {provider['decision']}",
        f"- dependency: {dependency}",
        f"- auth: {auth_method}",
        f"- auth_hint: {AUTH_HINTS.get(auth_method, '请参考 provider 官方认证方式。')}",
        f"- symbol_example: {symbol}",
        f"- start_date_example: {start_date}",
        f"- end_date_example: {end_date}",
        "- normalized_target: data/normalized/market.duckdb",
        "- raw_cache_target: data/raw/",
        "",
        "## Notes",
        "",
        notes.strip(),
        "",
    ]
    return "\n".join(summary_lines)


def generate_data_fetcher(
    provider: dict[str, object],
    output_dir: str | Path,
    symbol: str,
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-31",
) -> dict[str, object]:
    output_root = Path(output_dir)
    data_dir = output_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    provider_name = str(provider["provider"])
    decision = str(provider.get("decision", "generated_fetcher"))
    choice_path = data_dir / "provider_choice.json"
    setup_path = data_dir / "provider_setup.md"
    fetcher_path = data_dir / "fetch_data.py"

    provider_choice = {
        "provider": provider_name,
        "tier": provider.get("tier"),
        "decision": decision,
        "auth": provider.get("auth"),
        "dependency": provider.get("dependency"),
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "normalized_target": "data/normalized/market.duckdb",
    }
    choice_path.write_text(json.dumps(provider_choice, ensure_ascii=False, indent=2), encoding="utf-8")
    setup_path.write_text(
        _build_setup_text(provider, symbol=symbol, start_date=start_date, end_date=end_date),
        encoding="utf-8",
    )

    if decision == "data_required_cutoff":
        return {
            "decision": decision,
            "provider_choice_file": str(choice_path),
            "provider_setup_file": str(setup_path),
            "fetcher_file": None,
        }

    template_name = TEMPLATE_MAP.get(provider_name)
    if template_name is None:
        raise ValueError(f"No fetcher template defined for provider: {provider_name}")

    rendered = _render_template(
        template_name,
        {
            "provider_name": provider_name,
            "dependency_name": str(provider.get("dependency", provider_name)),
            "auth_method": str(provider.get("auth", "unknown")),
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    fetcher_path.write_text(rendered, encoding="utf-8")
    return {
        "decision": decision,
        "provider_choice_file": str(choice_path),
        "provider_setup_file": str(setup_path),
        "fetcher_file": str(fetcher_path),
    }
