from __future__ import annotations

import json
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from rapidfuzz import fuzz

from .models import CompanyProfileBase, Okpd2Item
from .okpd2_index import OKPD2_INDEX


def select_top_candidates(profile: CompanyProfileBase, top_n: int = 20) -> List[Okpd2Item]:
    combined_text = f"{profile.description} " + " ".join(profile.industries)
    scored = []
    for item in OKPD2_INDEX:
        score = fuzz.partial_ratio(combined_text.lower(), f"{item.code} {item.title}".lower())
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_n]]


def classify_okpd2(profile: CompanyProfileBase, llm: ChatOpenAI, limit: int = 5) -> List[Okpd2Item]:
    candidates = select_top_candidates(profile)
    candidate_lines = [f"{item.code} — {item.title}" for item in candidates]
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Ты помощник по классификации. Ниже описание компании и список кандидатов ОКПД2. Выбери до {limit} наиболее подходящих кодов и верни JSON вида {\"codes\": [\"41.20\", ...]}. Отвечай только JSON.",
            ),
            ("human", "Описание: {description}\nОтрасли: {industries}\nКандидаты:\n{candidates}"),
        ]
    )
    chain = prompt | llm
    response = chain.invoke(
        {
            "description": profile.description,
            "industries": ", ".join(profile.industries),
            "candidates": "\n".join(candidate_lines),
            "limit": str(limit),
        }
    )
    content = response.content if hasattr(response, "content") else str(response)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Не удалось распарсить ответ LLM: {content}") from exc

    selected_codes = set(data.get("codes", []))
    picked: List[Okpd2Item] = []
    for item in candidates:
        if item.code in selected_codes:
            picked.append(item)
    return picked
