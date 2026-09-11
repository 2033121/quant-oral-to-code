from __future__ import annotations

import json
from pathlib import Path

from run_disambiguation_flow import apply_answers_file, build_questionnaire


def test_run_disambiguation_flow_builds_questions_and_applies_answers(tmp_path: Path):
    prompt = "A股日线里只做龙头，最好弱转强后放量确认。"
    built = build_questionnaire(prompt=prompt, output_dir=tmp_path)

    assert built["question_count"] >= 1
    assert Path(built["pack_path"]).exists()
    assert Path(built["questions_path"]).exists()

    answers_path = tmp_path / "answers.json"
    answers_path.write_text(
        json.dumps(
            {
                "龙头": "leader_return_rank",
                "弱转强": "weak_to_strong_gap_followthrough",
                "放量确认": "volume_ratio_confirmation",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    applied = apply_answers_file(
        spec_path=built["spec_path"],
        answers_path=answers_path,
    )
    assert Path(applied["output_path"]).exists()
    assert isinstance(applied["disambiguated_terms"], list)
