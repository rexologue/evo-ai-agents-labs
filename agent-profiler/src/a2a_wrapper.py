"""Обертка LangChain агента для A2A протокола с трекингом CompanyFacts."""

import re
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, AsyncGenerator, List, Optional

from langchain.agents import AgentExecutor
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from company_facts import CompanyFacts, FIELD_ORDER

logger = logging.getLogger(__name__)


def _strip_think_blocks(text: str) -> str:
    """Удаляет служебные блоки `<think>...</think>` из ответа модели."""
    if not text:
        return text
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)


def _parse_output_value(text: str) -> Optional[str]:
    """Извлекает значение из единственного тега <output>…</output>."""
    if not text:
        return None
    match = re.search(r"<output>(.*?)</output>", text, flags=re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def _detect_field_by_keywords(text: str) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    keyword_map = {
        "name": ["назван", "бренд", "компани"],
        "description": ["описан", "чем занимает", "что делаете", "деятель"],
        "regions": ["регион", "город", "мест", "географ"],
        "min_contract_price": ["миним", "минимальн", "нижн", "минимум"],
        "max_contract_price": ["максим", "максимальн", "верхн"],
        "industries": ["отрас", "сфер", "индустр", "рынок"],
        "resources": ["ресурс", "команд", "оборуд", "техн", "цех", "магазин"],
        "risk_tolerance": ["риск"],
    }
    for field_name, keywords in keyword_map.items():
        if any(word in lowered for word in keywords):
            return field_name
    return None


def _is_final_message(text: str) -> bool:
    if not text:
        return False
    return "id профиля" in text.lower()


@dataclass
class SessionState:
    facts: CompanyFacts = field(default_factory=CompanyFacts)
    mode: str = "collecting"  # collecting -> review -> finalized
    current_field: Optional[str] = None
    company_id: Optional[str] = None

    def refresh_current_field(self, user_hint: Optional[str] = None) -> None:
        """Определяет, какое поле нужно спросить дальше."""
        if self.mode == "collecting":
            self.current_field = self.facts.next_unfilled_field()
            if self.current_field is None:
                self.mode = "review"
                self.current_field = None
        elif self.mode == "review" and user_hint:
            self.current_field = user_hint


class LangChainA2AWrapper:
    """Обертка для преобразования LangChain агента в A2A-совместимый интерфейс."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, agent_executor: AgentExecutor, auto_reset_on_complete: bool = True):
        self.agent_executor = agent_executor
        self.sessions: Dict[str, List[BaseMessage]] = {}
        self.session_states: Dict[str, SessionState] = {}
        self.auto_reset_on_complete = auto_reset_on_complete

    def _get_session_history(self, session_id: str) -> List[BaseMessage]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def _get_session_state(self, session_id: str) -> SessionState:
        if session_id not in self.session_states:
            self.session_states[session_id] = SessionState()
        return self.session_states[session_id]

    def _reset_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
        logger.debug("Session %s has been reset (task complete).", session_id)

    def _build_state_context(self, state: SessionState) -> str:
        lines = [
            "Служебный контекст state_context для CompanyProfiler.",
            f"Текущий режим: {state.mode} (collecting -> review -> finalized)",
            f"Поле, которое нужно уточнить сейчас: {state.current_field or 'нет, жди указаний пользователя'}",
            "Текущие факты профиля:",
            state.facts.summary(),
        ]

        if state.mode == "collecting" and (state.current_field is None or state.current_field == FIELD_ORDER[0]):
            lines.append("Если данных пока нет, начни диалог с приветствия и вопроса о названии компании.")

        if state.mode == "review":
            lines.append(
                "Все основные поля собраны. Покажи полный профиль, попроси подтвердить или указать, что поправить."
            )
        elif state.mode == "finalized":
            lines.append("Профиль сохранён. Не задавай больше вопросов.")

        lines.append("Помни: используешь один тег <output>...</output> только для значения текущего поля.")
        return "\n".join(lines)

    def _update_state_from_reply(self, state: SessionState, agent_text: str, user_text: str) -> None:
        value = _parse_output_value(agent_text)

        target_field = state.current_field
        if state.mode == "review" and target_field is None:
            target_field = _detect_field_by_keywords(agent_text) or _detect_field_by_keywords(user_text)
            if target_field:
                state.current_field = target_field

        if value is not None and value.strip() and target_field:
            saved = state.facts.set_field_value(target_field, value)
            if saved:
                if state.mode == "collecting":
                    state.current_field = state.facts.next_unfilled_field()
                    if state.current_field is None:
                        state.mode = "review"
                elif state.mode == "review":
                    state.current_field = None

        if _is_final_message(agent_text):
            state.mode = "finalized"
            state.company_id = self._extract_company_id(agent_text)

    def _extract_company_id(self, text: str) -> Optional[str]:
        if not text:
            return None
        match = re.search(r"ID\s*профиля\s*:\s*([A-Za-z0-9\-]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _should_reset(self, state: SessionState) -> bool:
        return state.mode == "finalized"

    async def invoke(self, query: str, session_id: str) -> Dict[str, Any]:
        try:
            chat_history = self._get_session_history(session_id)
            session_state = self._get_session_state(session_id)

            user_hint = _detect_field_by_keywords(query) if session_state.mode == "review" else None
            session_state.refresh_current_field(user_hint)
            state_context = self._build_state_context(session_state)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.agent_executor.invoke(
                    {
                        "input": query,
                        "chat_history": chat_history,
                        "state_context": state_context,
                    }
                ),
            )

            if isinstance(result, dict):
                raw_output = result.get("output", "")
            else:
                raw_output = str(result)

            clean_output = _strip_think_blocks(raw_output)

            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_output:
                chat_history.append(AIMessage(content=clean_output))

            self._update_state_from_reply(session_state, clean_output, query)

            require_input = session_state.mode != "finalized"

            response = {
                "is_task_complete": not require_input,
                "require_user_input": require_input,
                "content": clean_output,
                "is_error": False,
                "is_event": False,
            }

            if self.auto_reset_on_complete and self._should_reset(session_state):
                self._reset_session(session_id)

            return response

        except Exception as e:
            logger.exception("Error in LangChainA2AWrapper.invoke")
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"Ошибка: {str(e)}",
                "is_error": True,
                "is_event": False,
            }

    async def stream(
        self,
        query: str,
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            chat_history = self._get_session_history(session_id)
            session_state = self._get_session_state(session_id)

            user_hint = _detect_field_by_keywords(query) if session_state.mode == "review" else None
            session_state.refresh_current_field(user_hint)
            state_context = self._build_state_context(session_state)

            full_response = ""

            async for chunk in self.agent_executor.astream(
                {
                    "input": query,
                    "chat_history": chat_history,
                    "state_context": state_context,
                }
            ):
                if not isinstance(chunk, dict):
                    continue

                if "output" in chunk and isinstance(chunk["output"], str):
                    delta = chunk["output"]
                    if delta:
                        full_response += delta
                        yield {
                            "is_task_complete": False,
                            "require_user_input": False,
                            "content": delta,
                            "is_error": False,
                            "is_event": False,
                        }

                if "intermediate_steps" in chunk:
                    for step in chunk["intermediate_steps"] or []:
                        try:
                            tool_name = getattr(step[0], "tool", "tool")
                        except Exception:
                            tool_name = "tool"
                        yield {
                            "is_task_complete": False,
                            "require_user_input": False,
                            "content": f"Использую инструмент: {tool_name}\n",
                            "is_error": False,
                            "is_event": True,
                        }

            clean_full = _strip_think_blocks(full_response)

            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_full:
                chat_history.append(AIMessage(content=clean_full))

            self._update_state_from_reply(session_state, clean_full, query)

            require_input = session_state.mode != "finalized"

            final_payload = {
                "is_task_complete": not require_input,
                "require_user_input": require_input,
                "content": clean_full,
                "is_error": False,
                "is_event": False,
            }

            if self.auto_reset_on_complete and self._should_reset(session_state):
                self._reset_session(session_id)

            yield final_payload

        except Exception as e:
            logger.exception("Error in LangChainA2AWrapper.stream")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"Ошибка: {str(e)}",
                "is_error": True,
                "is_event": False,
            }
