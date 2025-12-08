"""Общие утилиты для MCP инструментов agent-service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import Content


@dataclass
class ToolResult:
    """Стандартный контейнер ответа MCP инструмента."""

    content: list[Content]
    structured_content: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


def _require_env_vars(names: list[str]) -> dict[str, str]:
    """Проверяет наличие обязательных переменных окружения."""

    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Отсутствуют обязательные переменные окружения: "
                + ", ".join(missing),
            )
        )
    return {name: os.getenv(name, "") for name in names}
