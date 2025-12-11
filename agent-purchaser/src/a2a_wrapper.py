"""Обертка LangChain агента PurchaseMatcher для A2A протокола."""

import re
import json
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, List

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_RESET_TOKEN = "<RESET_CONTEXT>"


def _strip_think_blocks(text: str) -> str:
    """Удаляет из ответа скрытые блоки размышлений `<think>...</think>`."""
    if not text:
        return text
    return _THINK_BLOCK_RE.sub("", text).strip()


def _strip_reset_token(text: str) -> tuple[str, bool]:
    """Удаляет служебный маркер <RESET_CONTEXT>, возвращает (чистый_текст, был_ли_маркер)."""
    if not text:
        return text, False

    had_token = _RESET_TOKEN in text
    if not had_token:
        return text, False

    cleaned = text.replace(_RESET_TOKEN, "").strip()
    return cleaned, True


def _looks_like_jsonl(text: str) -> bool:
    """
    Проверяет, что ответ — чистый JSONL:
    - есть хотя бы одна непустая строка;
    - КАЖДАЯ непустая строка парсится как корректный JSON-объект.
    """
    if not text:
        return False

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    try:
        for line in lines:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                return False
        return True
    except Exception:
        return False


class LangChainA2AWrapper:
    """Обертка для преобразования LangChain агента PurchaseMatcher в A2A-интерфейс."""

    # Для совместимости с A2A
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, agent_executor, auto_reset_on_complete: bool = True) -> None:
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

    def _postprocess_output(self, raw_output: str) -> tuple[str, bool, bool]:
        """
        Применяет все пост-обработки и возвращает:
        - clean_output: текст без <think> и служебных маркеров,
        - is_final_jsonl: является ли текст финальным JSONL-результатом,
        - reset_context: нужно ли сбросить контекст (<RESET_CONTEXT> был найден).
        """
        without_think = _strip_think_blocks(raw_output)
        cleaned, had_reset = _strip_reset_token(without_think)
        is_jsonl = _looks_like_jsonl(cleaned)
        return cleaned, is_jsonl, had_reset

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

            if isinstance(result, dict):
                raw_output = result.get("output", "")
            else:
                raw_output = str(result)

            clean_output, is_final_jsonl, reset_context = self._postprocess_output(raw_output)

            # обновляем историю диалога
            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_output:
                chat_history.append(AIMessage(content=clean_output))

            # критерии завершения:
            # - если был служебный маркер <RESET_CONTEXT> → задача завершена, контекст сбрасываем;
            # - если ответ — чистый JSONL → считаем, что это финальный результат и задача завершена.
            is_task_complete = bool(is_final_jsonl or reset_context)

            # пока не финальный JSONL и не RESET_CONTEXT — ожидаем ответ пользователя
            require_user_input = not is_task_complete and bool(clean_output and clean_output.strip())

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

            # После окончания стрима обрабатываем накопленный ответ
            clean_full, is_final_jsonl, reset_context = self._postprocess_output(full_response)

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

            is_task_complete = bool(is_final_jsonl or reset_context)
            require_user_input = not is_task_complete and bool(clean_full and clean_full.strip())

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
