from __future__ import annotations

from pathlib import Path


SUPPORTED_FORMATS = ("csv", "parquet", "json", "sqlite", "duckdb")
SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}
DUCKDB_SUFFIXES = {".duckdb", ".ddb"}


def _classify_file(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".parquet":
        return "parquet"
    if suffix == ".json":
        return "json"
    if suffix in SQLITE_SUFFIXES:
        return "sqlite"
    if suffix in DUCKDB_SUFFIXES:
        return "duckdb"
    return None


def _iter_candidates(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def detect_data_profile(path: str | Path) -> dict[str, object]:
    root = Path(path)
    candidates = _iter_candidates(root)

    for format_name in SUPPORTED_FORMATS:
        for candidate in candidates:
            if _classify_file(candidate) != format_name:
                continue
            return {
                "mode": "portable_csv_mode",
                "raw_input_format": format_name,
                "data_readiness": "ready",
                "provider_name": "manual_file_import",
                "input_path": str(candidate),
                "detection_basis": "suffix_scan",
                "available_formats": [format_name],
            }

    return {
        "mode": "demo_mode",
        "raw_input_format": None,
        "data_readiness": "needs_data",
        "provider_name": None,
        "input_path": str(root),
        "detection_basis": "no_supported_files_found",
        "available_formats": [],
    }


if __name__ == "__main__":
    import json
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print(json.dumps(detect_data_profile(target), ensure_ascii=False, indent=2))
