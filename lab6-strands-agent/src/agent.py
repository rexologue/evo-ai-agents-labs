"""Определение Strands Agents агента с meta-tooling и MCP интеграцией."""
import os
from typing import Optional, List
from strands import Agent
from strands.tools import load_tool, editor, shell
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client


# Системный промпт для создания инструментов
TOOL_BUILDER_SYSTEM_PROMPT = """
Ты агент, который может создавать новые инструменты на лету и использовать инструменты из MCP серверов.

Когда пользователь просит создать инструмент:
1. Определи следующую доступную версию инструмента (custom_tool_0, custom_tool_1, и т.д.)
2. Создай файл tools/custom_tool_X.py с правильной структурой
3. Используй инструмент load_tool для загрузки нового инструмента
4. Сообщи пользователю, что инструмент создан и готов к использованию

Структура инструмента должна следовать формату:
- TOOL_SPEC с описанием инструмента
- Функция с именем custom_tool_X, принимающая ToolUse и возвращающая ToolResult

Всегда создавай инструменты в директории tools/ и используй load_tool для их загрузки.

Также у тебя есть доступ к инструментам из MCP серверов - используй их для решения задач пользователя.
"""


def create_mcp_transport(mcp_url: str):
    """Создает транспорт для подключения к MCP серверу."""
    # Убеждаемся, что URL заканчивается на /mcp/ для streamable HTTP
    if not mcp_url.endswith('/'):
        mcp_url = mcp_url.rstrip('/')
    if not mcp_url.endswith('/mcp'):
        mcp_url = f"{mcp_url}/mcp"
    return streamablehttp_client(f"{mcp_url}/")


def get_mcp_tools(mcp_urls: Optional[str]) -> tuple[List, List[MCPClient]]:
    """Получает инструменты из MCP серверов и возвращает их вместе с клиентами.
    
    Returns:
        tuple: (список инструментов, список MCP клиентов для последующего использования)
    """
    tools = []
    mcp_clients = []
    
    if not mcp_urls:
        return tools, mcp_clients
    
    for mcp_url in mcp_urls.split(','):
        mcp_url = mcp_url.strip()
        if mcp_url:
            try:
                transport = create_mcp_transport(mcp_url)
                mcp_client = MCPClient(transport)
                
                # Используем контекстный менеджер для получения инструментов
                with mcp_client:
                    mcp_tools = mcp_client.list_tools_sync()
                    tools.extend(mcp_tools)
                    mcp_clients.append(mcp_client)
            except Exception as e:
                # Логируем ошибку, но продолжаем работу
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load tools from MCP server {mcp_url}: {e}")
    
    return tools, mcp_clients


def create_strands_agent(mcp_urls: Optional[str] = None):
    """Создает Strands Agents агента с meta-tooling и MCP интеграцией."""
    from litellm import completion
    
    # Настройка LLM через LiteLLM
    def llm_call(messages, **kwargs):
        """Обертка для вызова LLM через LiteLLM."""
        response = completion(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            messages=messages,
            api_base=os.getenv("LLM_API_BASE"),
            api_key=os.getenv("LLM_API_KEY"),
            **kwargs
        )
        return response.choices[0].message.content
    
    # Системный промпт
    system_prompt = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        TOOL_BUILDER_SYSTEM_PROMPT
    )
    
    # Базовые инструменты для meta-tooling
    tools = [load_tool, editor, shell]
    
    # Получаем инструменты из MCP серверов
    mcp_tools, mcp_clients = get_mcp_tools(mcp_urls)
    tools.extend(mcp_tools)
    
    # Создаем агента с инструментами
    agent = Agent(
        system_prompt=system_prompt,
        tools=tools,
        llm=llm_call,
    )
    
    # Сохраняем MCP клиенты для последующего использования (если нужно)
    # Примечание: для вызова инструментов может потребоваться контекстный менеджер
    agent._mcp_clients = mcp_clients
    
    return agent
