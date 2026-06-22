from __future__ import annotations

import json
from pathlib import Path


CUTOFF_ALLOWED_ARTIFACTS = {
    "strategy_spec.json",
    "translation_trace.json",
    "data_contract.json",
    "claim_report.json",
    "README_beginner.md",
    "data/provider_choice.json",
}


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def validate_artifact_manifest(manifest: dict[str, object]) -> dict[str, object]:
    artifact_policy = manifest.get("artifact_policy")
    artifacts = manifest.get("artifacts")
    artifact_count = manifest.get("artifact_count")
    if not isinstance(artifacts, list):
        raise ValueError("artifacts must be a list")
    if artifact_count != len(artifacts):
        raise ValueError("artifact_count must equal len(artifacts)")
    if artifact_policy == "data_required_cutoff":
        forbidden = []
        for artifact in artifacts:
            path = _normalize_path(str(artifact.get("path", "")))
            if path not in CUTOFF_ALLOWED_ARTIFACTS:
                forbidden.append(path)
        if forbidden:
            raise ValueError(
                "data_required_cutoff 清单只允许固定白名单产物: "
                + ", ".join(sorted(forbidden))
            )
    return manifest


def emit_artifact_manifest(
    artifacts: dict[str, object] | list[dict[str, object]],
    claim_level: str,
    artifact_policy: str,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    manifest_artifacts: list[dict[str, object]] = []
    if isinstance(artifacts, dict):
        for path, value in artifacts.items():
            manifest_artifacts.append(
                {
                    "path": _normalize_path(path),
                    "value": value,
                    "kind": "generated_file",
                }
            )
    elif isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ValueError("artifacts list items must be dict objects")
            normalized_artifact = dict(artifact)
            normalized_artifact["path"] = _normalize_path(str(artifact.get("path", "")))
            normalized_artifact.setdefault("kind", "generated_file")
            manifest_artifacts.append(normalized_artifact)
    else:
        raise ValueError("artifacts must be a dict or list")

    manifest = {
        "claim_level": claim_level,
        "artifact_policy": artifact_policy,
        "artifact_count": len(manifest_artifacts),
        "artifacts": manifest_artifacts,
    }
    validate_artifact_manifest(manifest)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(
        json.dumps(
            emit_artifact_manifest(
                {"claim_report.json": "ok"},
                claim_level="portable_backtest",
                artifact_policy="data_required_cutoff",
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
