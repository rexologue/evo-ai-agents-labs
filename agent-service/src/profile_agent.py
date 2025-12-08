from __future__ import annotations

import json
from typing import Any, Dict

import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .classifiers import classify_okpd2
from .config import get_settings
from .models import CompanyProfileBase, CompanyProfileDB

settings = get_settings()


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
        temperature=0,
    )


def generate_base_profile(description: str, llm: ChatOpenAI) -> CompanyProfileBase:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Ты аналитик по компаниям. На вход дается описание компании. Сформируй JSON строго по схеме CompanyProfileBase (без поля okpd2_codes или с пустым списком). Не добавляй лишних полей.",
            ),
            ("human", "Описание: {description}"),
        ]
    )
    chain = prompt | llm
    response = chain.invoke({"description": description})
    content = response.content if hasattr(response, "content") else str(response)
    data: Dict[str, Any]
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Не удалось распарсить профиль: {content}") from exc

    if "okpd2_codes" not in data:
        data["okpd2_codes"] = []
    profile = CompanyProfileBase(**data)
    return profile


def call_db_mcp_create(profile: CompanyProfileBase) -> CompanyProfileDB:
    url = f"{settings.db_mcp_url}/tools/create_company_profile/invoke"
    payload = {"profile": json.loads(profile.model_dump_json())}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        result = resp.json()
        content = result.get("content", result)
        if isinstance(content, dict) and "id" in content:
            return CompanyProfileDB(**content)
        return CompanyProfileDB.model_validate(content)


def run_profile_agent(description: str) -> dict[str, Any]:
    llm = _create_llm()
    base_profile = generate_base_profile(description, llm)
    classified_codes = classify_okpd2(base_profile, llm)
    base_profile.okpd2_codes = classified_codes
    saved = call_db_mcp_create(base_profile)
    summary = f"Компания: {saved.name}. Регионов: {len(saved.regions)}. ОКПД2: {[code.code for code in saved.okpd2_codes]}"
    return {
        "company_id": str(saved.id),
        "profile": saved.model_dump(),
        "summary": summary,
    }
