"""Основная логика PurchaseMatcher агента."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool

from config import get_settings, logger
from mcp_utils import load_mcp_tools
from prompts import (
    DESCRIPTION_SYSTEM_PROMPT,
    INTENT_SYSTEM_PROMPT,
    SCORING_SYSTEM_PROMPT,
)
from session_state import PurchaseMatcherState

settings = get_settings()


def _safe_parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _extract_json_block(text: str) -> str | None:
    """Выделяет JSON-блок из ответа LLM с размышлениями/разметкой."""

    if not text:
        return None

    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    # Markdown-кодблоки
    if "```" in stripped:
        parts = stripped.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[len("json") :].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate

    # Fallback: ищем первую и последнюю фигурные скобки
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]

    return None


class PurchaseMatcherAgent:
    """Оркестратор диалога и поиска закупок."""

    def __init__(self) -> None:
        self.sessions: Dict[str, PurchaseMatcherState] = {}
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_api_base,
            api_key=settings.llm_api_key,
            temperature=0.1,
        )
        # Подгружаем инструменты MCP
        self.tools = load_mcp_tools([settings.db_mcp_url, settings.gosplan_mcp_url])
        logger.info(
            "PurchaseMatcherAgent initialized with MCP tools: %s",
            list(self.tools.keys()),
        )

    def _get_state(self, session_id: str) -> PurchaseMatcherState:
        if session_id not in self.sessions:
            self.sessions[session_id] = PurchaseMatcherState()
        return self.sessions[session_id]

    def _reset_state(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].reset()

    @staticmethod
    def _extract_structured_content(tool_response: Any) -> Any:
        if tool_response is None:
            return None

        if hasattr(tool_response, "structured_content"):
            return getattr(tool_response, "structured_content")

        if isinstance(tool_response, dict):
            if "structured_content" in tool_response:
                return tool_response.get("structured_content")
            if "data" in tool_response:
                return tool_response.get("data")

        return tool_response

    async def _call_tool(self, tool_name: str, arguments: dict) -> Any:
        tool: BaseTool | None = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool {tool_name} not available")
        logger.debug("Calling tool '%s' with args=%s", tool_name, arguments)
        try:
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(arguments)
                logger.debug("Tool '%s' async result: %s", tool_name, result)
                return result
            # fallback sync
            result = tool.invoke(arguments)
            logger.debug("Tool '%s' sync result: %s", tool_name, result)
            return result
        except Exception:
            logger.exception("Tool '%s' failed on invoke, trying run()", tool_name)
            result = tool.run(arguments)
            logger.debug("Tool '%s' run result after exception: %s", tool_name, result)
            return result

    async def _parse_intent(self, message: str) -> Dict[str, Any]:
        msgs = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
        resp = await self.llm.ainvoke(msgs)
        resp_content = resp.content if hasattr(resp, "content") else str(resp)
        logger.info("Intent LLM raw response: %s", resp_content)

        json_block = _extract_json_block(resp_content) or ""
        data = _safe_parse_json(json_block)
        if not data:
            logger.warning("Intent JSON parsing failed for message='%s'", message)
            data = {}
        if not data.get("law_preference"):
            data["law_preference"] = "не указано"
        if not data.get("company_id"):
            logger.info(
                "Intent parsed without company_id. message='%s', company_name='%s'",
                message,
                data.get("company_name"),
            )
        logger.info("Parsed intent: %s", data)
        return data

    def _build_company_prompt(self, state: PurchaseMatcherState) -> str:
        lines: List[str] = []

        if not state.greeted:
            lines.append(
                "Привет! Чтобы подобрать закупки под вашу компанию, мне нужен её идентификатор или точное название."
            )
        else:
            lines.append(
                "Продолжаем. Без названия или ID компании я не смогу получить её профиль."
            )

        lines.append(
            "Пришлите id компании из базы или точное название, чтобы я нашла профиль."
        )

        state.greeted = True
        return "\n".join(lines)

    def _build_preferences_prompt(self, state: PurchaseMatcherState) -> str:
        company_part = "Профиль компании найден."
        if state.company_name or state.company_id:
            company_part = f"Профиль компании найден: {state.company_name or ''} (id: {state.company_id or 'нет id'})."

        questions = [
            "Есть ли особые условия для поиска закупок?",
            "— Нужна ли отсечка по приёму заявок (дата YYYY-MM-DD)?",
            "— Ищем по всем регионам из профиля или нужны свои?",
            "— Предпочтителен 44-ФЗ, 223-ФЗ или оба?",
            "— Есть ли пожелания по бюджету или ключевые требования?",
            "Если ничего не нужно уточнять — скажите, и я продолжу с текущими данными.",
        ]

        return "\n".join([company_part, *questions])

    async def _generate_description(self, purchase_number: str, detail: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(detail, ensure_ascii=False, indent=2)
        msgs = [
            SystemMessage(content=DESCRIPTION_SYSTEM_PROMPT),
            HumanMessage(content=f"Данные закупки:\n{payload}"),
        ]
        for _ in range(2):
            resp = await self.llm.ainvoke(msgs)
            data = _safe_parse_json(resp.content if hasattr(resp, "content") else str(resp))
            if data.get("purchase_number"):
                return data
        return {
            "purchase_number": purchase_number,
            "purchase_desc": "Не удалось построить описание",
            "urls": {"eis": None, "gosplan": None, "other": []},
        }

    async def _score_purchase(
        self,
        purchase_number: str,
        detail: Dict[str, Any],
        description: str,
        company: Dict[str, Any],
        query_description: str,
        applications_end_before: str,
    ) -> Dict[str, Any]:
        payload = json.dumps(
            {
                "company": company,
                "user_query": query_description,
                "applications_end_before": applications_end_before,
                "purchase_description": description,
                "purchase": detail,
            },
            ensure_ascii=False,
            indent=2,
        )
        msgs = [SystemMessage(content=SCORING_SYSTEM_PROMPT), HumanMessage(content=payload)]
        for _ in range(2):
            resp = await self.llm.ainvoke(msgs)
            data = _safe_parse_json(resp.content if hasattr(resp, "content") else str(resp))
            if data.get("purchase_number"):
                return data
        return {
            "purchase_number": purchase_number,
            "scores": {
                "activity_match_score": 0.0,
                "time_match_score": 0.0,
                "complexity_score": 0.0,
                "possible_benefit_score": 0.0,
            },
            "explanation": "Не удалось вычислить оценки",
        }

    def _extract_okpd_and_regions(self, company: Dict[str, Any], state: PurchaseMatcherState) -> Tuple[List[str], List[str]]:
        okpd2_codes = [item.get("code") for item in company.get("okpd2_codes", []) if item.get("code")]
        regions = [item.get("code") for item in company.get("regions_codes", []) if item.get("code")]
        if state.regions_override is not None:
            regions = state.regions_override
        return okpd2_codes, regions

    def _build_user_summary(self, results: List[Dict[str, Any]]) -> str:
        lines = ["Нашла подходящие закупки (топ-5):"]
        for item in results[:5]:
            scores = item.get("scores", {})
            lines.append(
                f"№ {item.get('purchase_number')}: {item.get('purchase_desc')[:180]}... "
                f"Польза={scores.get('possible_benefit_score', 0):.2f}, "
                f"Соответствие={scores.get('activity_match_score', 0):.2f}, "
                f"Сроки={scores.get('time_match_score', 0):.2f}"
            )
        return "\n".join(lines)

    def _format_jsonl(self, results: List[Dict[str, Any]]) -> str:
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in results)

    async def handle(self, message: str, session_id: str) -> Dict[str, Any]:
        state = self._get_state(session_id)

        intent = await self._parse_intent(message)
        if intent.get("reset"):
            state.reset()

        state.company_id = intent.get("company_id") or state.company_id
        state.company_name = intent.get("company_name") or state.company_name
        state.query_description = (
            intent.get("query_description")
            or intent.get("query_text")
            or state.query_description
        )
        state.applications_end_before = (
            intent.get("applications_end_before") or state.applications_end_before
        )
        state.regions_override = intent.get("regions_override") or state.regions_override
        state.law_preference = intent.get("law_preference") or state.law_preference
        state.price_notes = intent.get("price_notes") or state.price_notes

        logger.debug(
            "Session %s state after intent: company_id=%s, company_name=%s, query_description=%s, deadline=%s",
            session_id,
            state.company_id,
            state.company_name,
            state.query_description,
            state.applications_end_before,
        )

        if not state.company_profile:
            company = None
            try:
                if state.company_id:
                    logger.info(
                        "Session %s: fetching company profile by id=%s",
                        session_id,
                        state.company_id,
                    )
                    company_resp = await self._call_tool(
                        "get_company_profile", {"company_id": state.company_id}
                    )
                    company = self._extract_structured_content(company_resp)
                    logger.info(
                        "Session %s: company profile response (by id): %s",
                        session_id,
                        company,
                    )
                if not company and state.company_name:
                    logger.info(
                        "Session %s: searching company by name '%s'",
                        session_id,
                        state.company_name,
                    )
                    profiles_resp = await self._call_tool(
                        "list_company_profiles",
                        {"query": state.company_name, "limit": 1, "offset": 0},
                    )
                    structured = self._extract_structured_content(profiles_resp) or {}
                    logger.debug(
                        "Session %s: list_company_profiles structured response: %s",
                        session_id,
                        structured,
                    )
                    candidates = (
                        structured.get("items")
                        if isinstance(structured, dict)
                        else structured
                    )
                    if isinstance(candidates, list) and candidates:
                        company = candidates[0]
            except Exception:
                logger.exception("Session %s: company profile lookup failed", session_id)
                return {
                    "content": "Произошла ошибка при запросе профиля компании. Попробуйте ещё раз или укажите другое название/ID.",
                    "require_user_input": True,
                    "is_task_complete": False,
                    "is_error": True,
                }

            if not company:
                logger.warning(
                    "Session %s: company not found (id=%s, name=%s)",
                    session_id,
                    state.company_id,
                    state.company_name,
                )
                prompt = self._build_company_prompt(state)
                state.reset()
                return {
                    "content": prompt,
                    "require_user_input": True,
                    "is_task_complete": False,
                    "is_error": False,
                }
            state.company_profile = company
            state.company_id = company.get("id") or state.company_id
            state.company_name = company.get("name") or state.company_name
            logger.info(
                "Session %s: resolved company profile id=%s name='%s'",
                session_id,
                state.company_id,
                state.company_name,
            )

        if not state.preferences_prompted:
            prompt = self._build_preferences_prompt(state)
            state.preferences_prompted = True
            return {
                "content": prompt,
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": False,
            }

        query_description = (
            state.query_description
            or state.company_profile.get("description")
            or state.company_name
            or "Подобрать закупки по профилю компании"
        )

        okpd2_codes, regions_codes = self._extract_okpd_and_regions(state.company_profile, state)
        logger.info(
            "Session %s: filters okpd2=%s regions=%s deadline=%s",
            session_id,
            okpd2_codes,
            regions_codes,
            state.applications_end_before,
        )
        deadline = None
        if state.applications_end_before:
            try:
                deadline = (
                    datetime.fromisoformat(state.applications_end_before)
                    .date()
                    .isoformat()
                )
            except Exception:
                logger.warning(
                    "Session %s: invalid deadline format '%s'",
                    session_id,
                    state.applications_end_before,
                )
                return {
                    "content": "Дата дедлайна непонятна. Пришлите в формате YYYY-MM-DD или скажите, что без ограничений.",
                    "require_user_input": True,
                    "is_task_complete": False,
                    "is_error": False,
                }

        search_payload = {
            "classifiers": okpd2_codes,
            "region_codes": regions_codes or [],
            "limit": 9,
        }
        if deadline:
            search_payload["collecting_finished_before"] = deadline

        try:
            search_resp = await self._call_tool("search_purchases", search_payload)
        except Exception:
            logger.exception("Session %s: search_purchases failed", session_id)
            return {
                "content": "Не удалось выполнить поиск по gosplan-mcp. Попробуйте позже или скорректируйте запрос.",
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": True,
            }
        purchase_numbers = []
        structured_search = self._extract_structured_content(search_resp)
        logger.debug(
            "Session %s: search_purchases structured response: %s",
            session_id,
            structured_search,
        )
        if isinstance(structured_search, list):
            purchase_numbers = [
                item.get("purchase_number")
                if isinstance(item, dict)
                else item
                for item in structured_search
            ]
        elif isinstance(structured_search, dict):
            purchase_numbers = structured_search.get("data") or structured_search.get(
                "items", []
            )

        if not purchase_numbers:
            logger.info(
                "Session %s: no purchases found for payload=%s",
                session_id,
                search_payload,
            )
            return {
                "content": "По заданным фильтрам ничего не нашла. Можно попробовать позже, смягчить регионы или дедлайн?",
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": False,
            }

        state.purchase_numbers = [str(num) for num in purchase_numbers if num][:9]

        # Получаем детали
        for num in state.purchase_numbers:
            try:
                detail_resp = await self._call_tool(
                    "get_purchase_details", {"purchase_number": num}
                )
                detail = self._extract_structured_content(detail_resp) or {}
            except Exception:
                logger.exception(
                    "Session %s: failed to fetch purchase details for %s",
                    session_id,
                    num,
                )
                detail = {}
            if isinstance(detail, dict):
                state.purchase_details[num] = detail

        # Собираем описания и оценки
        results: List[Dict[str, Any]] = []
        for num in state.purchase_numbers:
            detail = state.purchase_details.get(num) or {}
            description_data = await self._generate_description(num, detail)
            state.purchase_descriptions[num] = description_data
            scoring_data = await self._score_purchase(
                num,
                detail,
                description_data.get("purchase_desc", ""),
                state.company_profile,
                query_description,
                state.applications_end_before or "",
            )
            state.purchase_scores[num] = scoring_data
            merged = {
                "purchase_number": num,
                "purchase_desc": description_data.get("purchase_desc"),
                "scores": scoring_data.get("scores", {}),
                "urls": description_data.get("urls", {}),
            }
            results.append(merged)

        results.sort(
            key=lambda x: (
                x.get("scores", {}).get("possible_benefit_score", 0),
                x.get("scores", {}).get("activity_match_score", 0),
                x.get("scores", {}).get("time_match_score", 0),
            ),
            reverse=True,
        )

        jsonl_block = self._format_jsonl(results)
        summary = self._build_user_summary(results)

        final_text = f"{summary}\n\nJSONL:\n{jsonl_block}"

        self._reset_state(session_id)
        return {
            "content": final_text,
            "require_user_input": False,
            "is_task_complete": True,
            "is_error": False,
        }
