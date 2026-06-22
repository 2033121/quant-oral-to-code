from __future__ import annotations

from pathlib import Path


SENTINEL_SETS: tuple[tuple[str, ...], ...] = (
    ("skills", "docs"),
    (".git",),
)


def _candidate_start(start: Path) -> Path:
    return start if start.is_dir() else start.parent


def resolve_repo_root(start: str | Path) -> Path:
    current = _candidate_start(Path(start).resolve())
    for candidate in (current, *current.parents):
        for sentinel_set in SENTINEL_SETS:
            if all((candidate / sentinel).exists() for sentinel in sentinel_set):
                return candidate
    raise FileNotFoundError(
        f"Unable to resolve repository root from {start!s} using sentinel directories {SENTINEL_SETS!r}"
    )


if __name__ == "__main__":
    print(resolve_repo_root(__file__))
