from __future__ import annotations


def render_disambiguation_questions(pack: dict[str, object]) -> str:
    questions = pack.get("questions", [])
    if not isinstance(questions, list) or not questions:
        return "当前没有需要向用户继续确认的抽象术语。"

    lines: list[str] = []
    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", ""))
        question = str(item.get("question", ""))
        note = str(item.get("note", "")).strip()
        lines.append(f"{index}. {question}")
        if note:
            lines.append(f"说明：{note}")

        choices = item.get("choices", [])
        if isinstance(choices, list):
            for choice_index, choice in enumerate(choices, start=1):
                if not isinstance(choice, dict):
                    continue
                label = str(choice.get("label", ""))
                description = str(choice.get("description", ""))
                lines.append(f"{choice_index}. {label}：{description}")

        if term:
            lines.append(f"回答格式建议：`{term}=选项编号`，如果都不合适，就直接补充你自己的定义。")
        lines.append("")

    return "\n".join(lines).strip()


if __name__ == "__main__":
    demo_pack = {
        "questions": [
            {
                "term": "龙头",
                "question": "术语“龙头”你更想按哪种可回测定义来实现？",
                "note": "",
                "choices": [
                    {"label": "区间涨幅领先", "description": "最近 N 日涨幅前列"},
                    {"label": "用户自己定义", "description": "由用户补充"},
                ],
            }
        ]
    }
    print(render_disambiguation_questions(demo_pack))
