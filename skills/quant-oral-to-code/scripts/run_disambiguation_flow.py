from __future__ import annotations

import argparse
import json
from pathlib import Path

from apply_disambiguation_answers import apply_disambiguation_answers
from build_disambiguation_pack import build_disambiguation_pack
from build_strategy_spec import build_strategy_spec
from render_disambiguation_questions import render_disambiguation_questions


def build_questionnaire(prompt: str, output_dir: str | Path) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    spec = build_strategy_spec(prompt)
    pack = build_disambiguation_pack(prompt, spec)
    question_text = render_disambiguation_questions(pack)

    spec_path = output_path / "strategy_spec.initial.json"
    pack_path = output_path / "disambiguation_pack.json"
    questions_path = output_path / "disambiguation_questions.txt"

    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    questions_path.write_text(question_text, encoding="utf-8")

    return {
        "spec_path": str(spec_path),
        "pack_path": str(pack_path),
        "questions_path": str(questions_path),
        "question_count": len(pack.get("questions", [])),
        "can_continue_after_answers": bool(pack.get("can_continue_after_answers", False)),
    }


def apply_answers_file(
    spec_path: str | Path,
    answers_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    answers = json.loads(Path(answers_path).read_text(encoding="utf-8"))
    updated = apply_disambiguation_answers(spec, answers)
    target = Path(output_path) if output_path is not None else Path(spec_path).with_name("strategy_spec.resolved.json")
    target.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "output_path": str(target),
        "remaining_unresolved_terms": updated.get("unresolved_terms", []),
        "disambiguated_terms": updated.get("disambiguated_terms", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run quant-oral-to-code term disambiguation flow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--prompt-file", required=True)
    build_parser.add_argument("--output-dir", required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--spec-file", required=True)
    apply_parser.add_argument("--answers-file", required=True)
    apply_parser.add_argument("--output-file", default=None)

    args = parser.parse_args()
    if args.command == "build":
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
        result = build_questionnaire(prompt=prompt, output_dir=args.output_dir)
    else:
        result = apply_answers_file(
            spec_path=args.spec_file,
            answers_path=args.answers_file,
            output_path=args.output_file,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
