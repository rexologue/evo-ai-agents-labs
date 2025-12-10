############################
# FILE: src/a2a_wrapper.py #
############################

"""Обертка LangChain агента для A2A протокола."""

import re
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, List, Optional

from langchain.agents import AgentExecutor
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think_blocks(text: str) -> str:
    """Удаляет из ответа скрытые блоки размышлений `<think>...</think>`."""
    if not text:
        return text
    return _THINK_BLOCK_RE.sub("", text).strip()


def _was_create_company_profile_called(intermediate_steps: Any) -> bool:
    """Проверяет по intermediate_steps, вызывался ли тул create_company_profile.

    Ожидаем формат intermediate_steps от LangChain AgentExecutor:
    список кортежей (AgentAction, Any).
    """
    if not intermediate_steps:
        return False

    try:
        for step in intermediate_steps:
            # Обычно это (AgentAction, tool_output)
            if not isinstance(step, (list, tuple)) or not step:
                continue

            action = step[0]
            tool_name: Optional[str] = getattr(action, "tool", None) or getattr(
                action, "name", None
            )
            if not tool_name:
                continue

            if "create_company_profile" in str(tool_name):
                logger.info("Detected create_company_profile tool call in intermediate_steps")
                return True
    except Exception as exc:
        logger.warning("Failed to inspect intermediate_steps: %s", exc)

    return False


class LangChainA2AWrapper:
    """Обертка для преобразования LangChain агента в A2A-совместимый интерфейс."""

    # Для совместимости с A2A
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(
        self, agent_executor: AgentExecutor, auto_reset_on_complete: bool = True
    ) -> None:
        self.agent_executor = agent_executor
        # история как список BaseMessage (HumanMessage / AIMessage)
        self.sessions: Dict[str, List[BaseMessage]] = {}

        # включаем/выключаем автоочистку сессии после завершения задачи
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
        """Синхронный (не-стриминговый) вызов агента."""
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

            intermediate_steps = None
            if isinstance(result, dict):
                raw_output = result.get("output", "")
                intermediate_steps = result.get("intermediate_steps")
            else:
                raw_output = str(result)

            clean_output = _strip_think_blocks(raw_output)

            # обновляем историю диалога
            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_output:
                chat_history.append(AIMessage(content=clean_output))

            tool_called = _was_create_company_profile_called(intermediate_steps)

            # Критерий завершения:
            #   задача завершена, когда был вызван тул create_company_profile.
            #   Всё остальное — ещё рабочий процесс, и после ответа пользователя логично ждать.
            is_task_complete = bool(tool_called)

            # Пока профиль не сохранён, и есть текст — ожидаем ответ пользователя
            require_user_input = not is_task_complete and bool(
                clean_output and clean_output.strip()
            )

            response = {
                "is_task_complete": is_task_complete,
                "require_user_input": require_user_input,
                "content": clean_output,
                "is_error": False,
                "is_event": False,
            }

            if self.auto_reset_on_complete and is_task_complete:
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

    async def stream(self, query: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Стриминговый вызов агента."""
        try:
            chat_history = self._get_session_history(session_id)
            logger.info(
                "LC-A2A stream: session_id=%s, history_len(before)=%d",
                session_id,
                len(chat_history),
            )

            full_response = ""
            tool_called: bool = False

            async for chunk in self.agent_executor.astream(
                {
                    "input": query,
                    "chat_history": chat_history,
                }
            ):
                if not isinstance(chunk, dict):
                    continue

                # Поток основного текста
                if "output" in chunk and isinstance(chunk["output"], str):
                    delta = chunk["output"]
                    if delta:
                        full_response += delta
                        # Промежуточные токены — просто "working", без ожидания ввода
                        yield {
                            "is_task_complete": False,
                            "require_user_input": False,
                            "content": delta,
                            "is_error": False,
                            "is_event": False,
                        }

                # Поток шагов с инструментами
                if "intermediate_steps" in chunk:
                    steps_batch = chunk["intermediate_steps"] or []
                    if _was_create_company_profile_called(steps_batch):
                        tool_called = True

            # После окончания стрима обрабатываем накопленный ответ
            clean_full = _strip_think_blocks(full_response)

            # Обновляем историю диалога
            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_full:
                chat_history.append(AIMessage(content=clean_full))

            logger.debug(
                "LC-A2A stream: session_id=%s, history_len(after)=%d",
                session_id,
                len(chat_history),
            )

            # Завершение – по факту вызова create_company_profile
            is_task_complete = bool(tool_called)
            require_user_input = not is_task_complete and bool(
                clean_full and clean_full.strip()
            )

            if not full_response or clean_full != full_response:
                final_payload = {
                    "is_task_complete": is_task_complete,
                    "require_user_input": require_user_input,
                    "content": clean_full,
                    "is_error": False,
                    "is_event": False,
                }
            else:
                # Весь текст уже ушёл стримом, финальное сообщение — только статус
                final_payload = {
                    "is_task_complete": is_task_complete,
                    "require_user_input": require_user_input,
                    "content": "",
                    "is_error": False,
                    "is_event": False,
                }

            if self.auto_reset_on_complete and is_task_complete:
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
