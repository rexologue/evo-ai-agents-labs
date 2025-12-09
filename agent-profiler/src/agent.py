"""Определение LangChain агента с поддержкой MCP инструментов и классификацией по ОКПД2."""

import asyncio
from typing import List, Optional, Dict

from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_mcp_adapters.client import MultiServerMCPClient  # MCP <-> LangChain

from config import get_settings
from base_prompt import BASE_SYSTEM_PROMPT
from tools.okpd2_tool import build_okpd2_tool

settings = get_settings()


def _normalize_mcp_url(raw: str) -> str:
    """Нормализует URL MCP сервера к виду .../mcp."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Пустой MCP URL")

    # уже /mcp или /mcp/
    if raw.rstrip("/").endswith("/mcp"):
        return raw.rstrip("/")

    return raw.rstrip("/") + "/mcp"


def _build_mcp_client(mcp_urls: Optional[str]) -> Optional[MultiServerMCPClient]:
    """
    Создаёт MultiServerMCPClient по строке с MCP URL-ами.

    Поддерживаем форматы:
      - "http://db-mcp:28001/mcp"
      - "http://db-mcp:28001"
      - "finance=http://db-mcp:28001/mcp"
      - "finance=http://db-mcp:28001,gosplan=http://gosplan-mcp:28002/mcp"
    """
    if not mcp_urls:
        return None

    servers: Dict[str, dict] = {}

    for idx, item in enumerate(mcp_urls.split(",")):
        item = item.strip()
        if not item:
            continue

        if "=" in item:
            name, url = item.split("=", 1)
            name = name.strip() or f"mcp_{idx}"
            url = url.strip()
        else:
            name = f"mcp_{idx}"
            url = item.strip()

        if not url:
            continue

        url = _normalize_mcp_url(url)

        servers[name] = {
            "transport": "streamable_http",  # streamable HTTP поверх FastMCP
            "url": url,
        }

    if not servers:
        return None

    return MultiServerMCPClient(servers)


async def _get_mcp_tools_async(mcp_urls: Optional[str]) -> List[BaseTool]:
    """Асинхронная загрузка всех тулов со всех MCP-серверов."""
    client = _build_mcp_client(mcp_urls)
    if client is None:
        return []

    tools = await client.get_tools()
    return list(tools)


def get_mcp_tools(mcp_urls: Optional[str]) -> List[BaseTool]:
    """Синхронная обёртка над асинхронной загрузкой MCP-тулов."""
    if not mcp_urls:
        return []
    return asyncio.run(_get_mcp_tools_async(mcp_urls))


def create_langchain_agent(mcp_urls: Optional[str] = None) -> AgentExecutor:
    """Создает LangChain агента с MCP инструментами"""
    # LLM
    llm = ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        temperature=0.2,
    )

    # Инструменты MCP (db-mcp и др.)
    mcp_tools = get_mcp_tools(mcp_urls)

    # Локальный инструмент для ОКПД2
    okpd2_tool = build_okpd2_tool()

    tools: List[BaseTool] = [*mcp_tools, okpd2_tool]

    # Системный промпт задается статически через base_prompt
    system_prompt = BASE_SYSTEM_PROMPT

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    ).partial(
        # ⬇️ А здесь один раз подмешиваем сам текст промпта
        system_prompt=system_prompt
    )

    agent = create_openai_tools_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=20,
    )

    return agent_executor
