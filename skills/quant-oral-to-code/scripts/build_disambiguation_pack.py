from __future__ import annotations

import json
from pathlib import Path


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_library() -> dict[str, object]:
    library_path = _skill_root() / "references" / "term_disambiguation_library.json"
    return json.loads(library_path.read_text(encoding="utf-8"))


def _load_sources() -> dict[str, object]:
    ontology_path = _skill_root() / "references" / "domain_ontology.json"
    library = _load_library()
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))
    return {"library": library, "ontology": ontology}


def _pick_term_question(term: str, entry: dict[str, object]) -> str:
    category = str(entry.get("category", "general"))
    if category == "data_sensitive":
        return f"术语“{term}”你想按哪种数据口径或代理方式落地？"
    if category == "intraday":
        return f"术语“{term}”你是要保留分钟级原意，还是降级成日线代理？"
    if category == "structure":
        return f"术语“{term}”你希望按哪种结构化近似定义来实现？"
    return f"术语“{term}”你更想按哪种可回测定义来实现？"


def _build_choice(choice: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(choice.get("id", "")),
        "label": str(choice.get("label", "")),
        "description": str(choice.get("description", "")),
        "rule": choice.get("rule", {}),
        "requires": list(choice.get("requires", []))
        if isinstance(choice.get("requires"), list)
        else [],
    }


def build_disambiguation_pack(prompt: str, spec: dict) -> dict[str, object]:
    sources = _load_sources()
    library = sources["library"]
    ontology = sources["ontology"]

    unresolved_terms = [
        str(term)
        for term in spec.get("unresolved_terms", [])
        if isinstance(term, str) and term.strip()
    ]

    data_sensitive_terms = ontology.get("data_sensitive_terms", {})
    questions: list[dict[str, object]] = []
    pending_terms: list[str] = []
    search_hints: list[str] = []

    for term in unresolved_terms:
        library_entry = library.get(term)
        if not isinstance(library_entry, dict):
            pending_terms.append(term)
            continue

        choices = [
            _build_choice(item)
            for item in library_entry.get("choices", [])
            if isinstance(item, dict)
        ]
        if not choices:
            pending_terms.append(term)
            continue

        note = ""
        if term in data_sensitive_terms:
            note = str(data_sensitive_terms[term])

        questions.append(
            {
                "term": term,
                "category": str(library_entry.get("category", "general")),
                "question": _pick_term_question(term, library_entry),
                "note": note,
                "choices": choices,
            }
        )
        for hint in library_entry.get("search_hints", []):
            if isinstance(hint, str) and hint not in search_hints:
                search_hints.append(hint)

    return {
        "prompt": prompt,
        "pending_terms": pending_terms,
        "questions": questions,
        "search_hints": search_hints,
        "can_continue_after_answers": bool(questions),
    }


if __name__ == "__main__":
    demo_spec = {
        "unresolved_terms": ["龙头", "筹码", "均价线"],
    }
    print(
        json.dumps(
            build_disambiguation_pack("只做龙头，筹码稳，盘中别破均价线。", demo_spec),
            ensure_ascii=False,
            indent=2,
        )
    )
