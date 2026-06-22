from __future__ import annotations

from pathlib import Path


SKILL_ROOT_SENTINELS: tuple[str, ...] = (
    "SKILL.md",
    "docs",
    "modules",
    "references",
    "schemas",
    "scripts",
    "templates",
)
SKILL_DIRNAME = "quant-oral-to-code"


def _candidate_start(start: Path) -> Path:
    return start if start.is_dir() else start.parent


def _is_standalone_skill_root(candidate: Path) -> bool:
    return all((candidate / sentinel).exists() for sentinel in SKILL_ROOT_SENTINELS)


def _is_repo_root(candidate: Path) -> bool:
    return _is_standalone_skill_root(candidate / "skills" / SKILL_DIRNAME)


def resolve_repo_root(start: str | Path) -> Path:
    current = _candidate_start(Path(start).resolve())
    for candidate in (current, *current.parents):
        if _is_repo_root(candidate):
            return candidate
        if _is_standalone_skill_root(candidate):
            return candidate
    raise FileNotFoundError(
        "Unable to resolve quant-oral-to-code runtime root from "
        f"{start!s}. Expected either a repository root containing "
        "`skills/quant-oral-to-code/` or a standalone skill root with "
        f"{SKILL_ROOT_SENTINELS!r}."
    )


if __name__ == "__main__":
    print(resolve_repo_root(__file__))
