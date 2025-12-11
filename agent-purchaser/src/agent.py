######################
# FILE: src/agent.py #
######################

"""Определение LangChain агента PurchaseMatcher с поддержкой MCP инструментов (classic API)."""

from __future__ import annotations

import asyncio
import sys
import types
from typing import List, Optional, Dict

from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ВАЖНО: классический AgentExecutor и tool-calling агент
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

# Хак для langchain_mcp_adapters (как в профайлере)
def _ensure_langchain_content_module() -> None:
    """Ensure langchain-mcp-adapters can import ``langchain_core.messages.content``."""
    if "langchain_core.messages.content" in sys.modules:
        return

    try:
        from langchain_core.messages import content_blocks
    except Exception:
        return

    shim = types.ModuleType("langchain_core.messages.content")
    shim.__dict__.update(content_blocks.__dict__)
    sys.modules["langchain_core.messages.content"] = shim


_ensure_langchain_content_module()

from langchain_mcp_adapters.client import MultiServerMCPClient  # MCP <-> LangChain

from config import get_settings, logger
from base_prompt import BASE_SYSTEM_PROMPT

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
      - "db=http://db-mcp:28001/mcp"
      - "db=http://db-mcp:28001,gosplan=http://gosplan-mcp:28002/mcp"
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
            "transport": "streamable_http",
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


def create_langchain_agent(
    mcp_urls: str | list[str] | None = None,
) -> AgentExecutor:
    """
    Создаёт классический LangChain-агент PurchaseMatcher с MCP инструментами.

    Возвращаем именно AgentExecutor:
    - astream_events / ainvoke / invoke
    - return_intermediate_steps и т.д.
    Это совместимо с твоей A2A-обёрткой (как в профайлере).
    """
    logger.info("LLM: model=%s base_url=%s", settings.llm_model, settings.llm_api_base)

    # защита от префикса hosted_vllm/ (как в профайлере)
    settings.llm_model = settings.llm_model.replace("hosted_vllm/", "")

    # LLM
    llm = ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        temperature=0.1,
    )

    # Инструменты MCP (db-mcp, gosplan-mcp и др.)
    mcp_tools: List[BaseTool] = []

    if isinstance(mcp_urls, list):
        for url in mcp_urls:
            mcp_tools.extend(get_mcp_tools(url))
    elif isinstance(mcp_urls, str):
        mcp_tools.extend(get_mcp_tools(mcp_urls))
    else:
        # MCP не настроены
        pass

    logger.info("Loaded %d MCP tools", len(mcp_tools))

    # Системный промпт (как ты его уже прописал под PurchaseMatcher)
    system_prompt = BASE_SYSTEM_PROMPT

    # ВАЖНО: структура промпта под классический tool-calling агент
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    ).partial(system_prompt=system_prompt)

    # Классический tool-calling агент
    agent = create_tool_calling_agent(
        llm=llm,
        tools=mcp_tools,
        prompt=prompt,
    )

    # Классический Executor (как раньше)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=mcp_tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=24,
        return_intermediate_steps=True,
    )

    return agent_executor
