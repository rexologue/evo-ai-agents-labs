"""Обертка LangChain агента PurchaseMatcher для A2A протокола."""

import re
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, List, Tuple, Optional

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_RESET_TOKEN = "<RESET_CONTEXT>"
_END_TOKEN = "<END_OF_SUGGESTION>"


def _strip_think_blocks(text: str) -> str:
    """Удаляет из ответа скрытые блоки размышлений `<think>...</think>`."""
    if not text:
        return text
    return _THINK_BLOCK_RE.sub("", text).strip()


def _strip_token(text: str, token: str) -> Tuple[str, bool]:
    """
    Удаляет служебный токен, возвращает (чистый_текст, был_ли_токен).
    Удаляет ВСЕ вхождения токена (на всякий случай).
    """
    if not text:
        return text, False

    had_token = token in text
    if not had_token:
        return text, False

    cleaned = text.replace(token, "").strip()
    return cleaned, True


def _find_earliest_token(s: str, tokens: Tuple[str, ...]) -> Tuple[Optional[int], Optional[str]]:
    """Возвращает (позиция, токен) для самого раннего вхождения любого токена в строке."""
    earliest_pos: Optional[int] = None
    earliest_tok: Optional[str] = None
    for tok in tokens:
        pos = s.find(tok)
        if pos != -1 and (earliest_pos is None or pos < earliest_pos):
            earliest_pos = pos
            earliest_tok = tok
    return earliest_pos, earliest_tok


def _longest_suffix_prefix_len(s: str, tokens: Tuple[str, ...]) -> int:
    """
    Длина максимального суффикса s, который является префиксом одного из tokens,
    но НЕ равен полному токену.
    Это позволяет безопасно стримить, не "протекают" стоп-токены через границы чанков.
    """
    if not s:
        return 0

    best = 0
    n = len(s)
    for tok in tokens:
        # держим только "недопрефикс", т.е. < len(tok)
        max_k = min(len(tok) - 1, n)
        # ищем самый длинный k
        for k in range(max_k, 0, -1):
            if s.endswith(tok[:k]):
                if k > best:
                    best = k
                break
    return best


class LangChainA2AWrapper:
    """Обертка для преобразования LangChain агента PurchaseMatcher в A2A-интерфейс."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, agent_executor, auto_reset_on_complete: bool = True) -> None:
        self.agent_executor = agent_executor
        self.sessions: Dict[str, List[BaseMessage]] = {}
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

    def _postprocess_output(self, raw_output: str) -> Tuple[str, bool, bool]:
        """
        Возвращает:
        - clean_output: текст без <think> и служебных маркеров,
        - had_end_token: был ли <END_OF_SUGGESTION>,
        - had_reset_token: был ли <RESET_CONTEXT>.
        """
        without_think = _strip_think_blocks(raw_output)

        cleaned, had_reset = _strip_token(without_think, _RESET_TOKEN)
        cleaned, had_end = _strip_token(cleaned, _END_TOKEN)

        return cleaned, had_end, had_reset

    async def invoke(self, query: str, session_id: str) -> Dict[str, Any]:
        """Синхронный (не-стриминговый) вызов агента."""
        try:
            chat_history = self._get_session_history(session_id)

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.agent_executor.invoke(
                    {
                        "input": query,
                        "chat_history": chat_history,
                    }
                ),
            )

            raw_output = result.get("output", "") if isinstance(result, dict) else str(result)
            clean_output, had_end, had_reset = self._postprocess_output(raw_output)

            if query:
                chat_history.append(HumanMessage(content=query))
            if clean_output:
                chat_history.append(AIMessage(content=clean_output))

            is_task_complete = bool(had_end or had_reset)
            require_user_input = (not is_task_complete) and bool(clean_output and clean_output.strip())

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

            stop_tokens = (_END_TOKEN, _RESET_TOKEN)

            # carry держит только минимальный суффикс, который может быть началом стоп-токена
            carry = ""
            kept_raw = ""  # именно это станет "полным ответом" (без текста после END/RESET)

            stop_seen_end = False
            stop_seen_reset = False

            async for chunk in self.agent_executor.astream(
                {
                    "input": query,
                    "chat_history": chat_history,
                }
            ):
                if not isinstance(chunk, dict):
                    continue
                delta = chunk.get("output")
                if not isinstance(delta, str) or not delta:
                    continue

                combined = carry + delta

                # 1) Если в combined уже есть полный стоп-токен — режем по нему и завершаем стрим.
                pos, tok = _find_earliest_token(combined, stop_tokens)
                if tok is not None and pos is not None:
                    before = combined[:pos]
                    if before:
                        kept_raw += before
                        yield {
                            "is_task_complete": False,
                            "require_user_input": False,
                            "content": before,
                            "is_error": False,
                            "is_event": True,  # промежуточный стрим-ивент
                        }

                    if tok == _END_TOKEN:
                        stop_seen_end = True
                    elif tok == _RESET_TOKEN:
                        stop_seen_reset = True

                    carry = ""
                    break

                # 2) Полного токена нет — можно стримить "безопасную" часть.
                k = _longest_suffix_prefix_len(combined, stop_tokens)
                if k > 0:
                    emit = combined[:-k]
                    carry = combined[-k:]
                else:
                    emit = combined
                    carry = ""

                if emit:
                    kept_raw += emit
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": emit,
                        "is_error": False,
                        "is_event": True,  # промежуточный стрим-ивент
                    }

            # Если стоп-токена не было — дописываем остаток carry (он не содержит полного токена).
            if carry and not (stop_seen_end or stop_seen_reset):
                kept_raw += carry
                carry = ""

            # Финальная пост-обработка
            clean_full, had_end, had_reset = self._postprocess_output(kept_raw)

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

            is_task_complete = bool(had_end or had_reset or stop_seen_end or stop_seen_reset)
            require_user_input = (not is_task_complete) and bool(clean_full and clean_full.strip())

            if self.auto_reset_on_complete and is_task_complete:
                self._reset_session(session_id)

            # ВАЖНО: финальный payload всегда содержит ПОЛНЫЙ clean_full (без "remaining"),
            # чтобы клиенты, которые отображают только финальный ответ, не теряли начало текста.
            yield {
                "is_task_complete": is_task_complete,
                "require_user_input": require_user_input,
                "content": clean_full,
                "is_error": False,
                "is_event": False,
            }

        except Exception as e:
            logger.exception("Error in LangChainA2AWrapper.stream")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"Ошибка: {str(e)}",
                "is_error": True,
                "is_event": False,
            }
