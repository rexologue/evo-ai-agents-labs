"""Обработчики Mattermost событий."""
import json
import logging
from typing import Optional, Callable, Any
from opentelemetry import trace

from mattermostdriver import Driver
from mattermostdriver.exceptions import ResourceNotFound

from a2a_client import A2AClientWrapper
from commands import CommandHandler
from telemetry import get_tracer, set_span_attribute

logger = logging.getLogger(__name__)


class MattermostHandler:
    """Обработчик событий Mattermost."""

    def __init__(
        self,
        driver: Driver,
        a2a_client: A2AClientWrapper,
        command_handler: CommandHandler,
        bot_user_id: Optional[str] = None,
    ):
        """
        Инициализация обработчика.

        Args:
            driver: Mattermost Driver instance
            a2a_client: A2A клиент
            command_handler: Обработчик команд
            bot_user_id: ID пользователя бота (опционально, будет получен автоматически)
        """
        self.driver = driver
        self.a2a_client = a2a_client
        self.command_handler = command_handler
        self.bot_user_id = bot_user_id
        self.bot_username: Optional[str] = None

    async def initialize(self) -> None:
        """Инициализировать обработчик, получить информацию о боте."""
        tracer = get_tracer()
        with tracer.start_as_current_span("mattermost_handler.initialize") as span:
            try:
                # Получаем информацию о текущем пользователе (боте)
                user = self.driver.users.get_user(user_id="me")
                self.bot_user_id = user["id"]
                self.bot_username = user["username"]
                set_span_attribute(span, "bot.user_id", self.bot_user_id)
                set_span_attribute(span, "bot.username", self.bot_username)
                logger.info(f"Бот инициализирован: {self.bot_username} (ID: {self.bot_user_id})")
            except Exception as e:
                logger.error(f"Ошибка инициализации обработчика: {e}")
                set_span_attribute(span, "error", True)
                set_span_attribute(span, "error.message", str(e))
                raise

    def _is_mention(self, message: str) -> bool:
        """
        Проверить, упоминается ли бот в сообщении.

        Args:
            message: Текст сообщения

        Returns:
            True если бот упомянут
        """
        if not self.bot_username:
            return False

        # Проверяем упоминание по username
        mentions = [f"@{self.bot_username}", f"@{self.bot_user_id}"]
        return any(mention in message for mention in mentions)

    def _extract_message_text(self, message: str) -> str:
        """
        Извлечь текст сообщения, убрав упоминания бота.

        Args:
            message: Исходное сообщение

        Returns:
            Очищенный текст сообщения
        """
        if not self.bot_username:
            return message.strip()

        # Убираем упоминания бота
        text = message
        text = text.replace(f"@{self.bot_username}", "").strip()
        text = text.replace(f"@{self.bot_user_id}", "").strip()
        return text

    async def handle_post_event(self, event_data: dict[str, Any]) -> None:
        """
        Обработать событие поста.

        Args:
            event_data: Данные события от Mattermost
        """
        tracer = get_tracer()
        with tracer.start_as_current_span("mattermost_handler.handle_post_event") as span:
            try:
                # Парсим данные поста
                post_data = json.loads(event_data.get("data", {}).get("post", "{}"))
                post_id = post_data.get("id")
                channel_id = post_data.get("channel_id")
                user_id = post_data.get("user_id")
                message = post_data.get("message", "").strip()

                set_span_attribute(span, "mattermost.post_id", post_id)
                set_span_attribute(span, "mattermost.channel_id", channel_id)
                set_span_attribute(span, "mattermost.user_id", user_id)

                # Игнорируем сообщения от самого бота
                if user_id == self.bot_user_id:
                    logger.debug("Игнорируем сообщение от самого бота")
                    return

                # Игнорируем пустые сообщения
                if not message:
                    logger.debug("Игнорируем пустое сообщение")
                    return

                # Проверяем, является ли это прямым сообщением
                try:
                    channel = self.driver.channels.get_channel(channel_id)
                    is_dm = channel.get("type") == "D"
                    set_span_attribute(span, "mattermost.is_dm", is_dm)
                except ResourceNotFound:
                    logger.warning(f"Канал {channel_id} не найден")
                    return

                # Проверяем, нужно ли обрабатывать это сообщение
                is_mention = self._is_mention(message)
                is_command = self.command_handler.is_command(message)

                if not (is_mention or is_dm or is_command):
                    logger.debug("Сообщение не требует обработки")
                    return

                # Извлекаем текст сообщения
                message_text = self._extract_message_text(message)
                if not message_text:
                    logger.debug("Пустое сообщение после извлечения")
                    return

                set_span_attribute(span, "mattermost.message_type", "command" if is_command else "message")
                set_span_attribute(span, "mattermost.is_mention", is_mention)

                # Обрабатываем сообщение
                await self._process_message(
                    message_text=message_text,
                    channel_id=channel_id,
                    post_id=post_id,
                    is_command=is_command,
                    span=span,
                )

            except Exception as e:
                logger.error(f"Ошибка обработки события поста: {e}")
                set_span_attribute(span, "error", True)
                set_span_attribute(span, "error.message", str(e))

    async def _process_message(
        self,
        message_text: str,
        channel_id: str,
        post_id: str,
        is_command: bool,
        span: trace.Span,
    ) -> None:
        """
        Обработать сообщение и отправить ответ.

        Args:
            message_text: Текст сообщения
            channel_id: ID канала
            post_id: ID поста
            is_command: Является ли сообщение командой
            span: Текущий span для телеметрии
        """
        try:
            # Если это команда, обрабатываем через command_handler
            if is_command:
                command_prefix, command, args = self.command_handler.parse_command(message_text)
                if command_prefix == "a2a" and command:
                    response = await self.command_handler.handle_command(command, args)
                    if response:
                        await self._send_response(channel_id, post_id, response)
                        return

            # Иначе отправляем в A2A агент с streaming
            await self._send_to_a2a_with_streaming(
                message_text=message_text,
                channel_id=channel_id,
                post_id=post_id,
                span=span,
            )

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            set_span_attribute(span, "error", True)
            set_span_attribute(span, "error.message", str(e))
            error_message = f"❌ Произошла ошибка при обработке сообщения: {str(e)}"
            await self._send_response(channel_id, post_id, error_message)

    async def _send_to_a2a_with_streaming(
        self,
        message_text: str,
        channel_id: str,
        post_id: str,
        span: trace.Span,
    ) -> None:
        """
        Отправить сообщение в A2A агент с streaming ответом.

        Args:
            message_text: Текст сообщения
            channel_id: ID канала
            post_id: ID поста
            span: Текущий span для телеметрии
        """
        try:
            # Создаем начальное сообщение "печатает..."
            typing_post_id = None
            full_response = ""

            async for chunk in self.a2a_client.send_streaming_message(message_text):
                # Извлекаем текст из chunk
                chunk_text = self._extract_text_from_chunk(chunk)
                if chunk_text:
                    full_response += chunk_text

                    # Обновляем или создаем сообщение
                    if typing_post_id:
                        # Обновляем существующее сообщение
                        try:
                            self.driver.posts.update_post(
                                post_id=typing_post_id,
                                options={
                                    "id": typing_post_id,
                                    "message": full_response,
                                },
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось обновить сообщение: {e}")
                    else:
                        # Создаем новое сообщение
                        try:
                            response_post = self.driver.posts.create_post(
                                options={
                                    "channel_id": channel_id,
                                    "message": full_response,
                                    "root_id": post_id,
                                }
                            )
                            typing_post_id = response_post.get("id") or response_post.get("post", {}).get("id")
                        except Exception as e:
                            logger.error(f"Ошибка создания сообщения: {e}")

            # Финальное обновление если нужно
            if typing_post_id and full_response:
                try:
                    self.driver.posts.update_post(
                        post_id=typing_post_id,
                        options={
                            "id": typing_post_id,
                            "message": full_response,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Не удалось обновить финальное сообщение: {e}")

            set_span_attribute(span, "a2a.response_length", len(full_response))

        except Exception as e:
            logger.error(f"Ошибка streaming ответа: {e}")
            set_span_attribute(span, "error", True)
            set_span_attribute(span, "error.message", str(e))
            error_message = f"❌ Ошибка при получении ответа от A2A агента: {str(e)}"
            await self._send_response(channel_id, post_id, error_message)

    def _extract_text_from_chunk(self, chunk: dict[str, Any]) -> str:
        """
        Извлечь текст из chunk ответа A2A.

        Args:
            chunk: Chunk от A2A агента

        Returns:
            Извлеченный текст
        """
        try:
            # Пытаемся извлечь текст из различных возможных структур
            if isinstance(chunk, dict):
                # Проверяем различные возможные пути к тексту
                if "message" in chunk:
                    message = chunk["message"]
                    if isinstance(message, dict):
                        if "parts" in message:
                            parts = message["parts"]
                            if isinstance(parts, list) and parts:
                                text_parts = [
                                    p.get("text", "")
                                    for p in parts
                                    if isinstance(p, dict) and p.get("kind") == "text"
                                ]
                                return "".join(text_parts)
                        elif "content" in message:
                            return str(message["content"])
                    elif isinstance(message, str):
                        return message
                elif "text" in chunk:
                    return str(chunk["text"])
                elif "content" in chunk:
                    return str(chunk["content"])
            elif isinstance(chunk, str):
                return chunk

            return ""
        except Exception as e:
            logger.warning(f"Ошибка извлечения текста из chunk: {e}")
            return ""

    async def _send_response(
        self, channel_id: str, post_id: str, message: str
    ) -> None:
        """
        Отправить ответ в канал.

        Args:
            channel_id: ID канала
            post_id: ID исходного поста
            message: Текст ответа
        """
        try:
            self.driver.posts.create_post(
                options={
                    "channel_id": channel_id,
                    "message": message,
                    "root_id": post_id,
                }
            )
        except Exception as e:
            logger.error(f"Ошибка отправки ответа: {e}")

    def create_event_handler(self) -> Callable:
        """
        Создать обработчик событий для Mattermost WebSocket.

        Returns:
            Функция-обработчик событий
        """
        async def event_handler(event: dict[str, Any]) -> None:
            """Обработчик событий WebSocket."""
            event_type = event.get("event")
            if event_type == "posted":
                await self.handle_post_event(event)

        return event_handler

