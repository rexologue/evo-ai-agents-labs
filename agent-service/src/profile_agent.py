"""Вспомогательные функции профильного агента."""

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
    """Создает экземпляр LLM для агентов."""

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
        temperature=0,
    )


async def generate_base_profile(description: str, llm: ChatOpenAI) -> CompanyProfileBase:
    """Генерирует базовый профиль компании из описания."""

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
    response = await chain.ainvoke({"description": description})
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


async def call_db_mcp_create(profile: CompanyProfileBase) -> CompanyProfileDB:
    """Вызывает MCP инструмент сохранения профиля в db-mcp."""

    url = f"{settings.db_mcp_url}/tools/create_company_profile/invoke"
    payload = {"profile": json.loads(profile.model_dump_json())}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        result = resp.json()
        content = result.get("structured_content") or result.get("content") or result
        if isinstance(content, dict) and "id" in content:
            return CompanyProfileDB(**content)
        if isinstance(result, dict) and "structured_content" in result:
            return CompanyProfileDB.model_validate(result["structured_content"])
        return CompanyProfileDB.model_validate(content)


async def run_profile_agent(description: str) -> dict[str, Any]:
    """Запускает агент для генерации и сохранения профиля компании."""

    llm = _create_llm()
    base_profile = await generate_base_profile(description, llm)
    classified_codes = await classify_okpd2(base_profile, llm)
    base_profile.okpd2_codes = classified_codes
    saved = await call_db_mcp_create(base_profile)
    summary = f"Компания: {saved.name}. Регионов: {len(saved.regions)}. ОКПД2: {[code.code for code in saved.okpd2_codes]}"
    return {
        "company_id": str(saved.id),
        "profile": saved.model_dump(),
        "summary": summary,
    }
