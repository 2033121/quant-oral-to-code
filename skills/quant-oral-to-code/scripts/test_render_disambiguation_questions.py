from __future__ import annotations

from build_disambiguation_pack import build_disambiguation_pack
from build_strategy_spec import build_strategy_spec
from render_disambiguation_questions import render_disambiguation_questions


def test_render_disambiguation_questions_renders_numbered_choices():
    prompt = "只做龙头，情绪冰点后弱转强，最好有板块共振卡位。"
    spec = build_strategy_spec(prompt)
    pack = build_disambiguation_pack(prompt, spec)
    rendered = render_disambiguation_questions(pack)

    assert "1. 术语“龙头”" in rendered
    assert "回答格式建议" in rendered
    assert "情绪冰点" in rendered


def test_render_disambiguation_questions_handles_empty_pack():
    rendered = render_disambiguation_questions({"questions": []})
    assert "当前没有需要向用户继续确认的抽象术语" in rendered
