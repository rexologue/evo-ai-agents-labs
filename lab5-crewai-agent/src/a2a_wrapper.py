"""Обертка CrewAI crew для A2A протокола."""
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)


class CrewAIA2AWrapper:
    """Обертка для преобразования CrewAI crew в A2A-совместимый интерфейс."""
    
    def __init__(self, crew):
        self.crew = crew
        self.sessions: Dict[str, list] = {}  # Хранение истории сессий
    
    def _get_session_history(self, session_id: str) -> list:
        """Получает историю сессии."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]
    
    async def invoke(self, query: str, session_id: str) -> Dict[str, Any]:
        """Выполняет запрос к crew и возвращает результат."""
        try:
            # Получаем историю сессии
            chat_history = self._get_session_history(session_id)
            
            # Выполняем crew в отдельном потоке
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.crew.kickoff(inputs={"query": query})
            )
            
            # Извлекаем результат из crew output
            output = str(result) if result else "Нет результата"
            
            # Обновляем историю
            chat_history.append(("user", query))
            chat_history.append(("assistant", output))
            
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": output,
                "is_error": False,
                "is_event": False
            }
        except Exception as e:
            logger.error(f"Error in invoke: {e}", exc_info=True)
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"Ошибка: {str(e)}",
                "is_error": True,
                "is_event": False
            }
    
    async def stream(self, query: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Потоковое выполнение запроса к crew."""
        try:
            # Получаем историю сессии
            chat_history = self._get_session_history(session_id)
            
            # CrewAI может поддерживать streaming через kickoff_stream
            loop = asyncio.get_event_loop()
            
            # Проверяем, есть ли метод kickoff_stream
            if hasattr(self.crew, 'kickoff_stream'):
                # Используем streaming если доступен
                full_response = ""
                async for chunk in self.crew.kickoff_stream(inputs={"query": query}):
                    if chunk:
                        chunk_str = str(chunk)
                        if chunk_str and chunk_str != full_response:
                            new_part = chunk_str[len(full_response):]
                            full_response = chunk_str
                            
                            yield {
                                "is_task_complete": False,
                                "require_user_input": False,
                                "content": new_part,
                                "is_error": False,
                                "is_event": False
                            }
                
                # Обновляем историю
                chat_history.append(("user", query))
                chat_history.append(("assistant", full_response))
            else:
                # Эмулируем streaming для совместимости
                result = await loop.run_in_executor(
                    None,
                    lambda: self.crew.kickoff(inputs={"query": query})
                )
                
                output = str(result) if result else "Нет результата"
                
                # Отправляем результат по частям для имитации streaming
                chunk_size = 50
                for i in range(0, len(output), chunk_size):
                    chunk = output[i:i+chunk_size]
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": chunk,
                        "is_error": False,
                        "is_event": False
                    }
                
                # Обновляем историю
                chat_history.append(("user", query))
                chat_history.append(("assistant", output))
            
            # Финальный чанк
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "",
                "is_error": False,
                "is_event": False
            }
            
        except Exception as e:
            logger.error(f"Error in stream: {e}", exc_info=True)
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"Ошибка: {str(e)}",
                "is_error": True,
                "is_event": False
            }
    
    # Для совместимости с A2A
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]


