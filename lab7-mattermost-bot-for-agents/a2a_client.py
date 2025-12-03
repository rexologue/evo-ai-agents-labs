"""Обертка для A2A клиента с телеметрией и streaming поддержкой."""
import logging
import httpx
from typing import Any, AsyncIterator, Optional
from uuid import uuid4
from opentelemetry import trace

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)

from config import config
from telemetry import get_tracer, set_span_attribute

logger = logging.getLogger(__name__)


class A2AClientWrapper:
    """Обертка для A2A клиента с телеметрией."""

    def __init__(self):
        """Инициализация A2A клиента."""
        self.httpx_client: Optional[httpx.AsyncClient] = None
        self.resolver: Optional[A2ACardResolver] = None
        self.client: Optional[A2AClient] = None
        self.agent_card: Optional[AgentCard] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Инициализировать A2A клиент и получить agent card."""
        if self._initialized:
            return

        tracer = get_tracer()
        with tracer.start_as_current_span("a2a_client.initialize") as span:
            try:
                # Настройка httpx клиента с таймаутами
                timeout_config = httpx.Timeout(5 * 60.0)  # 5 минут
                self.httpx_client = httpx.AsyncClient(timeout=timeout_config)
                self.httpx_client.headers["Authorization"] = f"Bearer {config.A2A_TOKEN}"

                # Инициализация resolver и получение agent card
                self.resolver = A2ACardResolver(
                    httpx_client=self.httpx_client,
                    base_url=config.A2A_BASE_URL,
                )

                logger.info(f"Получение agent card с {config.A2A_BASE_URL}")
                self.agent_card = await self.resolver.get_agent_card()

                # Создание A2A клиента
                self.client = A2AClient(
                    httpx_client=self.httpx_client,
                    agent_card=self.agent_card,
                )

                self._initialized = True
                set_span_attribute(span, "a2a.agent_id", self.agent_card.agent_id if hasattr(self.agent_card, 'agent_id') else None)
                logger.info("A2A клиент успешно инициализирован")

            except Exception as e:
                logger.error(f"Ошибка инициализации A2A клиента: {e}")
                set_span_attribute(span, "error", True)
                set_span_attribute(span, "error.message", str(e))
                raise

    async def send_message(
        self, message_text: str, message_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Отправить сообщение в A2A агент и получить ответ.

        Args:
            message_text: Текст сообщения
            message_id: ID сообщения (если не указан, будет сгенерирован)

        Returns:
            Ответ от A2A агента в виде словаря
        """
        if not self._initialized:
            await self.initialize()

        tracer = get_tracer()
        with tracer.start_as_current_span("a2a_client.send_message") as span:
            try:
                if message_id is None:
                    message_id = uuid4().hex

                set_span_attribute(span, "a2a.message_id", message_id)
                set_span_attribute(span, "a2a.message_length", len(message_text))

                send_message_payload: dict[str, Any] = {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": message_text}],
                        "messageId": message_id,
                    },
                }

                request = SendMessageRequest(
                    id=str(uuid4()), params=MessageSendParams(**send_message_payload)
                )

                logger.debug(f"Отправка сообщения в A2A: {message_text[:100]}...")
                response = await self.client.send_message(request)
                result = response.model_dump(mode="json", exclude_none=True)

                # Добавляем метаданные в span
                if isinstance(result, dict):
                    set_span_attribute(span, "a2a.response_received", True)
                    # Пытаемся извлечь информацию о токенах если доступна
                    if "usage" in result:
                        usage = result.get("usage", {})
                        if "input_tokens" in usage:
                            set_span_attribute(span, "a2a.input_tokens", usage["input_tokens"])
                        if "output_tokens" in usage:
                            set_span_attribute(span, "a2a.output_tokens", usage["output_tokens"])

                logger.debug("Ответ от A2A получен")
                return result

            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в A2A: {e}")
                set_span_attribute(span, "error", True)
                set_span_attribute(span, "error.message", str(e))
                raise

    async def send_streaming_message(
        self, message_text: str, message_id: Optional[str] = None
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Отправить сообщение в A2A агент и получить streaming ответ.

        Args:
            message_text: Текст сообщения
            message_id: ID сообщения (если не указан, будет сгенерирован)

        Yields:
            Части ответа от A2A агента в виде словарей
        """
        if not self._initialized:
            await self.initialize()

        tracer = get_tracer()
        with tracer.start_as_current_span("a2a_client.send_streaming_message") as span:
            try:
                if message_id is None:
                    message_id = uuid4().hex

                set_span_attribute(span, "a2a.message_id", message_id)
                set_span_attribute(span, "a2a.message_length", len(message_text))
                set_span_attribute(span, "a2a.streaming", True)

                send_message_payload: dict[str, Any] = {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": message_text}],
                        "messageId": message_id,
                    },
                }

                request = SendStreamingMessageRequest(
                    id=str(uuid4()), params=MessageSendParams(**send_message_payload)
                )

                logger.debug(f"Отправка streaming сообщения в A2A: {message_text[:100]}...")
                chunk_count = 0

                async for chunk in self.client.send_streaming_message(request):
                    chunk_count += 1
                    result = chunk.model_dump(mode="json", exclude_none=True)
                    set_span_attribute(span, "a2a.chunks_received", chunk_count)
                    yield result

                set_span_attribute(span, "a2a.streaming_complete", True)
                set_span_attribute(span, "a2a.total_chunks", chunk_count)
                logger.debug(f"Streaming завершен, получено {chunk_count} chunks")

            except Exception as e:
                logger.error(f"Ошибка streaming сообщения в A2A: {e}")
                set_span_attribute(span, "error", True)
                set_span_attribute(span, "error.message", str(e))
                raise

    async def close(self) -> None:
        """Закрыть httpx клиент."""
        if self.httpx_client:
            await self.httpx_client.aclose()
            self._initialized = False
            logger.info("A2A клиент закрыт")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def get_agent_skills(self) -> list[dict[str, Any]]:
        """
        Получить список skills агента из agent card.

        Returns:
            Список skills агента
        """
        if not self.agent_card:
            return []

        try:
            # Пытаемся получить skills из agent_card
            # Структура может различаться, проверяем различные варианты
            if hasattr(self.agent_card, "skills"):
                skills = self.agent_card.skills
                if isinstance(skills, list):
                    return [skill.model_dump() if hasattr(skill, "model_dump") else skill for skill in skills]
                elif isinstance(skills, dict):
                    return [skills]
            elif hasattr(self.agent_card, "capabilities"):
                capabilities = self.agent_card.capabilities
                if isinstance(capabilities, list):
                    return [cap.model_dump() if hasattr(cap, "model_dump") else cap for cap in capabilities]
                elif isinstance(capabilities, dict):
                    return [capabilities]

            # Пытаемся получить из model_dump если доступно
            if hasattr(self.agent_card, "model_dump"):
                card_dict = self.agent_card.model_dump(mode="json", exclude_none=True)
                if "skills" in card_dict:
                    skills = card_dict["skills"]
                    if isinstance(skills, list):
                        return skills
                    elif isinstance(skills, dict):
                        return [skills]
                if "capabilities" in card_dict:
                    capabilities = card_dict["capabilities"]
                    if isinstance(capabilities, list):
                        return capabilities
                    elif isinstance(capabilities, dict):
                        return [capabilities]

            return []
        except Exception as e:
            logger.warning(f"Ошибка получения skills агента: {e}")
            return []

    def get_agent_info(self) -> dict[str, Any]:
        """
        Получить информацию об агенте.

        Returns:
            Словарь с информацией об агенте
        """
        if not self.agent_card:
            return {}

        try:
            info = {}
            if hasattr(self.agent_card, "model_dump"):
                info = self.agent_card.model_dump(mode="json", exclude_none=True)
            else:
                # Пытаемся получить основные поля
                for attr in ["agent_id", "name", "description", "version"]:
                    if hasattr(self.agent_card, attr):
                        info[attr] = getattr(self.agent_card, attr)

            return info
        except Exception as e:
            logger.warning(f"Ошибка получения информации об агенте: {e}")
            return {}

