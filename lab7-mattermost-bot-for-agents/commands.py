"""Обработка команд бота."""
import logging
from typing import Optional, Tuple
from opentelemetry import trace

from a2a_client import A2AClientWrapper
from telemetry import get_tracer, set_span_attribute

logger = logging.getLogger(__name__)


class CommandHandler:
    """Обработчик команд бота."""

    def __init__(self, a2a_client: A2AClientWrapper):
        """
        Инициализация обработчика команд.

        Args:
            a2a_client: Экземпляр A2A клиента
        """
        self.a2a_client = a2a_client

    async def handle_command(
        self, command: str, args: list[str]
    ) -> Optional[str]:
        """
        Обработать команду бота.

        Args:
            command: Название команды
            args: Аргументы команды

        Returns:
            Ответ на команду или None если команда не распознана
        """
        tracer = get_tracer()
        with tracer.start_as_current_span("commands.handle_command") as span:
            set_span_attribute(span, "command.name", command)
            set_span_attribute(span, "command.args_count", len(args))

            command_lower = command.lower()

            if command_lower == "help":
                return await self._handle_help()
            elif command_lower == "status":
                return await self._handle_status()
            else:
                # Неизвестная команда
                set_span_attribute(span, "command.unknown", True)
                logger.warning(f"Неизвестная команда: {command}")
                return None

    async def _handle_help(self) -> str:
        """Обработать команду help."""
        # Получаем skills агента
        skills = self.a2a_client.get_agent_skills()
        agent_info = self.a2a_client.get_agent_info()

        help_text = "**Доступные команды:**\n\n"
        help_text += "`/a2a help` - Показать эту справку\n"
        help_text += "`/a2a status` - Проверить статус подключения к A2A агенту\n\n"

        # Добавляем информацию об агенте если доступна
        if agent_info:
            if "name" in agent_info:
                help_text += f"**Агент:** {agent_info['name']}\n"
            if "description" in agent_info:
                help_text += f"**Описание:** {agent_info['description']}\n"
            help_text += "\n"

        # Добавляем skills если они доступны
        if skills:
            help_text += "**Доступные навыки (skills) агента:**\n\n"
            for skill in skills:
                skill_name = skill.get("name") or skill.get("id") or "Неизвестный навык"
                skill_desc = skill.get("description") or skill.get("summary") or ""
                
                help_text += f"• **{skill_name}**"
                if skill_desc:
                    help_text += f" - {skill_desc}"
                help_text += "\n"
            
            help_text += "\n"
            help_text += "Вы можете использовать эти навыки, упомянув бота или отправив ему сообщение.\n\n"
        else:
            help_text += "**Использование:**\n\n"

        help_text += "Вы также можете упомянуть бота в сообщении:\n"
        help_text += "```\n@bot_name Ваш вопрос здесь\n```\n\n"
        help_text += "Или отправить прямое сообщение боту."

        return help_text

    async def _handle_status(self) -> str:
        """Обработать команду status."""
        tracer = get_tracer()
        with tracer.start_as_current_span("commands.handle_status") as span:
            try:
                # Проверяем, что клиент инициализирован
                if not self.a2a_client._initialized:
                    await self.a2a_client.initialize()

                # Пытаемся отправить тестовое сообщение
                test_message = "test"
                try:
                    await self.a2a_client.send_message(test_message)
                    status = "✅ Подключение к A2A агенту работает"
                    set_span_attribute(span, "a2a.status", "connected")
                except Exception as e:
                    status = f"❌ Ошибка подключения к A2A агенту: {str(e)}"
                    set_span_attribute(span, "a2a.status", "error")
                    set_span_attribute(span, "error.message", str(e))
                    logger.error(f"Ошибка проверки статуса: {e}")

                return status

            except Exception as e:
                logger.error(f"Ошибка при проверке статуса: {e}")
                set_span_attribute(span, "error", True)
                set_span_attribute(span, "error.message", str(e))
                return f"❌ Ошибка при проверке статуса: {str(e)}"

    @staticmethod
    def parse_command(message: str) -> Tuple[Optional[str], Optional[str], list[str]]:
        """
        Распарсить команду из сообщения.

        Args:
            message: Текст сообщения

        Returns:
            Tuple (command_prefix, command, args) или (None, None, []) если это не команда
        """
        message = message.strip()

        # Проверяем, начинается ли сообщение с /
        if not message.startswith("/"):
            return None, None, []

        # Разбиваем на части
        parts = message.split()
        if not parts:
            return None, None, []

        # Первая часть - это команда (может быть /a2a или /command)
        full_command = parts[0][1:]  # Убираем /

        # Если команда вида /a2a help, то разбиваем дальше
        if full_command.startswith("a2a"):
            command_parts = full_command.split()
            if len(command_parts) > 1:
                # /a2a help -> command_prefix="a2a", command="help"
                command_prefix = "a2a"
                command = command_parts[1] if len(command_parts) > 1 else None
                args = parts[1:] if len(parts) > 1 else []
            else:
                # /a2a без дополнительных аргументов
                command_prefix = "a2a"
                command = None
                args = []
        else:
            # Простая команда /command
            command_prefix = None
            command = full_command
            args = parts[1:] if len(parts) > 1 else []

        return command_prefix, command, args

    def is_command(self, message: str) -> bool:
        """
        Проверить, является ли сообщение командой.

        Args:
            message: Текст сообщения

        Returns:
            True если это команда, False иначе
        """
        command_prefix, command, _ = self.parse_command(message)
        return command is not None or command_prefix == "a2a"

