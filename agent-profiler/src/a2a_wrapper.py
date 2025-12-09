"""Обертка LangChain агента для A2A протокола."""
import re
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, List

from langchain.agents import AgentExecutor
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think_blocks(text: str) -> str:
    """Удаляет из ответа скрытые блоки размышлений `<think>...</think>`."""
    if not text:
        return text

    return _THINK_BLOCK_RE.sub("", text).strip()


def _strip_need_input(text: str) -> tuple[str, bool]:
    """
    Убирает тег `<NEED_USER_INPUT>` и возвращает (очищенный_текст, нужен_ли_ответ_пользователя).
    """
    if not text:
        return text, False

    if "<NEED_USER_INPUT>" in text:
        clean = text.replace("<NEED_USER_INPUT>", "").strip()
        return clean, True

    return text, False


class LangChainA2AWrapper:
    """Обертка для преобразования LangChain агента в A2A-совместимый интерфейс."""

    # Для совместимости с A2A
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, agent_executor: AgentExecutor, auto_reset_on_complete: bool = False):
        self.agent_executor = agent_executor
        # ✅ история как список BaseMessage (HumanMessage / AIMessage)
        self.sessions: Dict[str, List[BaseMessage]] = {}
        # ✅ включаем/выключаем автоочистку сессии после завершения задачи
        # По умолчанию автоочистка отключена, чтобы не терять контекст между
        # запросами в интерактивных сценариях, где клиент может не передавать
        # стабильный context_id и чат должен продолжаться с черновиком.
        self.auto_reset_on_complete = auto_reset_on_complete

    def _get_session_history(self, session_id: str) -> List[BaseMessage]:
        """Получает историю сессии для подстановки в MessagesPlaceholder(chat_history)."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def _reset_session(self, session_id: str) -> None:
        """Полностью сбрасывает историю для сессии (логическое завершение контекста)."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug("Session %s has been reset (task complete).", session_id)

    async def invoke(self, query: str, session_id: str) -> Dict[str, Any]:
        """
        Синхронный (не-стриминговый) вызов агента.

        - чистим <think>...</think>
        - обрабатываем <NEED_USER_INPUT>
        - обновляем историю
        - при необходимости сбрасываем сессию после завершения задачи
        """
        try:
            chat_history = self._get_session_history(session_id)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.agent_executor.invoke(
                    {
                        "input": query,
                        "chat_history": chat_history,
                    }
                ),
            )

            if isinstance(result, dict):
                raw_output = result.get("output", "")
            else:
                raw_output = str(result)

            # Убираем служебные теги
            clean_output = _strip_think_blocks(raw_output)
            clean_output, need_input = _strip_need_input(clean_output)

            # Обновляем историю диалога
            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_output:
                chat_history.append(AIMessage(content=clean_output))

            response = {
                "is_task_complete": not need_input,
                "require_user_input": need_input,
                "content": clean_output,
                "is_error": False,
                "is_event": False,
            }

            # ✅ если задача завершена и не требуется ввод пользователя — чистим сессию
            if self.auto_reset_on_complete and not need_input:
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
        """
        Стриминговый вызов агента.

        - копим полный ответ в full_response
        - в конце чистим <think> и <NEED_USER_INPUT>
        - обновляем историю
        - по завершении, если не нужен ввод пользователя — сбрасываем сессию
        """
        try:
            chat_history = self._get_session_history(session_id)
            full_response = ""

            # LangChain AgentExecutor поддерживает astream
            async for chunk in self.agent_executor.astream(
                {
                    "input": query,
                    "chat_history": chat_history,
                }
            ):
                if not isinstance(chunk, dict):
                    continue

                # Основной поток текста
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

                # Промежуточные события о вызове инструментов
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

            # После окончания стрима чистим служебные теги
            clean_full = _strip_think_blocks(full_response)
            clean_full, need_input = _strip_need_input(clean_full)

            # Обновляем историю диалога
            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_full:
                chat_history.append(AIMessage(content=clean_full))

            # Готовим финальный payload
            if not full_response or clean_full != full_response:
                final_payload = {
                    "is_task_complete": not need_input,
                    "require_user_input": need_input,
                    "content": clean_full,
                    "is_error": False,
                    "is_event": False,
                }
            else:
                final_payload = {
                    "is_task_complete": not need_input,
                    "require_user_input": need_input,
                    "content": "",
                    "is_error": False,
                    "is_event": False,
                }

            # ✅ Автоочистка сессии, если задача завершена и не нужен ввод пользователя
            if self.auto_reset_on_complete and not need_input:
                self._reset_session(session_id)

            # Отдаём финальное сообщение
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
