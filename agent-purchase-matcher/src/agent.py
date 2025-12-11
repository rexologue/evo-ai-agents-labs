"""Основная логика PurchaseMatcher агента."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool

from .config import get_settings
from .mcp_utils import load_mcp_tools
from .prompts import (
    DESCRIPTION_SYSTEM_PROMPT,
    INTENT_SYSTEM_PROMPT,
    SCORING_SYSTEM_PROMPT,
)
from .session_state import PurchaseMatcherState

settings = get_settings()


def _safe_parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


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

    def _get_state(self, session_id: str) -> PurchaseMatcherState:
        if session_id not in self.sessions:
            self.sessions[session_id] = PurchaseMatcherState()
        return self.sessions[session_id]

    def _reset_state(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].reset()

    async def _call_tool(self, tool_name: str, arguments: dict) -> Any:
        tool: BaseTool | None = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool {tool_name} not available")
        try:
            if hasattr(tool, "ainvoke"):
                return await tool.ainvoke(arguments)
            # fallback sync
            return tool.invoke(arguments)
        except Exception:
            return tool.run(arguments)

    async def _parse_intent(self, message: str) -> Dict[str, Any]:
        msgs = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
        resp = await self.llm.ainvoke(msgs)
        data = _safe_parse_json(resp.content if hasattr(resp, "content") else str(resp))
        return data

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
        user_query: str,
        applications_end_before: str,
    ) -> Dict[str, Any]:
        payload = json.dumps(
            {
                "company": company,
                "user_query": user_query,
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
        state.user_query = intent.get("query_text") or state.user_query
        state.applications_end_before = (
            intent.get("applications_end_before") or state.applications_end_before
        )
        state.regions_override = intent.get("regions_override") or state.regions_override
        state.law_preference = intent.get("law_preference") or state.law_preference
        state.price_notes = intent.get("price_notes") or state.price_notes

        if not state.company_profile:
            company = None
            try:
                if state.company_id:
                    company = await self._call_tool(
                        "get_company_profile_by_id", {"company_id": state.company_id}
                    )
                if not company and state.company_name:
                    company = await self._call_tool(
                        "search_company_profile_by_name", {"name_query": state.company_name}
                    )
            except Exception:
                return {
                    "content": "Произошла ошибка при запросе профиля компании. Попробуйте ещё раз или проверьте параметры.",
                    "require_user_input": True,
                    "is_task_complete": False,
                    "is_error": True,
                }

            if not company:
                self._reset_state(session_id)
                return {
                    "content": "Не нашла профиль компании. Пожалуйста, сначала создайте профиль компании в системе, затем пришлите id или точное название.",
                    "require_user_input": True,
                    "is_task_complete": False,
                    "is_error": False,
                }
            state.company_profile = company
            state.company_id = company.get("id") or state.company_id
            state.company_name = company.get("name") or state.company_name

        if not state.applications_end_before:
            return {
                "content": "Укажите, пожалуйста, крайний прием заявок (дата YYYY-MM-DD), чтобы отфильтровать закупки.",
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": False,
            }

        if not state.user_query:
            return {
                "content": "Расскажите, какие закупки нужны (вид работ/услуг, регионы, бюджет).",
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": False,
            }

        okpd2_codes, regions_codes = self._extract_okpd_and_regions(state.company_profile, state)
        try:
            deadline = datetime.fromisoformat(state.applications_end_before).date().isoformat()
        except Exception:
            return {
                "content": "Дата дедлайна непонятна. Пришлите в формате YYYY-MM-DD.",
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": False,
            }

        search_payload = {
            "okpd2_codes": okpd2_codes,
            "regions_codes": regions_codes or [],
            "applications_end_before": deadline,
            "limit": 9,
        }

        try:
            search_resp = await self._call_tool("search_purchases", search_payload)
        except Exception:
            return {
                "content": "Не удалось выполнить поиск по gosplan-mcp. Попробуйте позже или скорректируйте запрос.",
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": True,
            }
        purchase_numbers = []
        if isinstance(search_resp, dict) and "data" in search_resp:
            # Structured langchain tool response
            purchase_numbers = search_resp.get("data", [])
        elif isinstance(search_resp, list):
            purchase_numbers = search_resp

        if not purchase_numbers:
            return {
                "content": "По заданным фильтрам ничего не нашла. Можно попробовать позже, смягчить регионы или дедлайн?",
                "require_user_input": True,
                "is_task_complete": False,
                "is_error": False,
            }

        state.purchase_numbers = [str(num) for num in purchase_numbers][:9]

        # Получаем детали
        for num in state.purchase_numbers:
            try:
                detail = await self._call_tool("get_purchase_details", {"purchase_number": num})
            except Exception:
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
                state.user_query,
                state.applications_end_before,
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
