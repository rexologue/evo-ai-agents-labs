"""Определение LangChain агента с поддержкой MCP инструментов.

Фикс:
- Если один из MCP серверов недоступен/не резолвится (DNS), MultiServerMCPClient.get_tools()
  падает ExceptionGroup и валит запуск всего агента.
- Здесь мы грузим тулзы ПО ОДНОМУ серверу, собираем ошибки, и выдаём понятное сообщение:
  какой URL упал и почему.

Важно: это НЕ про LLM. Ошибка происходит ещё до старта агента, на этапе list_tools().
"""

from __future__ import annotations

import asyncio
import socket
import sys
import types
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple, Any

from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# В вашем проекте используется классический tool-calling агент
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import get_settings, logger
from base_prompt import BASE_SYSTEM_PROMPT

settings = get_settings()


def _ensure_langchain_content_module() -> None:
    """Ensure langchain-mcp-adapters can import `langchain_core.messages.content`."""
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


def _normalize_mcp_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Пустой MCP URL")
    if raw.rstrip("/").endswith("/mcp"):
        return raw.rstrip("/")
    return raw.rstrip("/") + "/mcp"


def _dns_sanity_check(url: str) -> None:
    """Ранняя диагностика: если хост не резолвится — упадём с понятной ошибкой."""
    p = urlparse(url)
    host = p.hostname
    if not host:
        raise ValueError(f"Некорректный MCP URL (не удалось извлечь hostname): {url}")

    # port по умолчанию
    if p.port:
        port = p.port
    else:
        port = 443 if p.scheme == "https" else 80

    try:
        socket.getaddrinfo(host, port)
    except socket.gaierror as e:
        raise RuntimeError(
            "MCP hostname не резолвится из контейнера агента.\n"
            f"URL: {url}\n"
            f"Host: {host}:{port}\n"
            f"Причина: {e}\n\n"
            "Типовые причины:\n"
            "- Вы указали docker-compose service name (например, db-mcp), но агент НЕ в той же docker-сети.\n"
            "- Вы используете --network host, но оставили service name вместо localhost/127.0.0.1.\n"
            "- В Cloud/remote среде указали внутренний hostname, который не существует снаружи.\n"
        ) from e


def _flatten_exc(exc: BaseException) -> List[str]:
    """Собрать сообщения из ExceptionGroup (Python 3.11+)."""
    # ExceptionGroup / BaseExceptionGroup существуют в 3.11+
    if isinstance(exc, BaseExceptionGroup):  # type: ignore[name-defined]
        out: List[str] = []
        for sub in exc.exceptions:  # type: ignore[attr-defined]
            out.extend(_flatten_exc(sub))
        return out
    return [f"{type(exc).__name__}: {exc}"]


async def _load_tools_from_one_mcp(url: str, server_name: str) -> List[BaseTool]:
    """Грузим tools с одного MCP сервера. Если сервер недоступен — тут и упадём."""
    url = _normalize_mcp_url(url)
    _dns_sanity_check(url)

    client = MultiServerMCPClient(
        {
            server_name: {
                "transport": "streamable_http",
                "url": url,
            }
        }
    )
    tools = await client.get_tools()
    return list(tools)


async def _load_tools_from_many(urls: List[str]) -> Tuple[List[BaseTool], List[str]]:
    """Загружает тулзы с нескольких MCP URL, не валя всё из-за одного."""
    tasks: List[asyncio.Task[Any]] = []
    for i, u in enumerate(urls):
        u = (u or "").strip()
        if not u:
            continue
        tasks.append(asyncio.create_task(_load_tools_from_one_mcp(u, f"mcp_{i}")))

    if not tasks:
        return [], ["Не переданы MCP URL (пусто)."]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    tools: List[BaseTool] = []
    errors: List[str] = []

    for u, r in zip([x for x in urls if (x or "").strip()], results):
        if isinstance(r, BaseException):
            msgs = _flatten_exc(r)
            errors.append(f"Не удалось подключиться к MCP: {u}\n- " + "\n- ".join(msgs))
        else:
            tools.extend(list(r))

    return tools, errors


def create_langchain_agent(mcp_urls: Optional[List[str]] = None) -> AgentExecutor:
    """Создаёт LangChain tool-calling агента + MCP инструменты."""
    logger.info("LLM: model=%s base_url=%s", settings.llm_model, settings.llm_api_base)

    # иногда у вас префикс hosted_vllm/
    model_name = (settings.llm_model or "").replace("hosted_vllm/", "").strip()

    llm = ChatOpenAI(
        model=model_name,
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        temperature=0.1,
    )

    urls: List[str] = []
    if mcp_urls:
        urls = [u for u in mcp_urls if (u or "").strip()]

    # Грузим MCP tools (не валим весь процесс из-за одного URL без объяснения)
    try:
        mcp_tools, mcp_errors = asyncio.run(_load_tools_from_many(urls))
    except RuntimeError as e:
        # это наши понятные ошибки (DNS etc.)
        raise
    except BaseException as e:
        # на всякий случай — тоже внятно
        msgs = _flatten_exc(e)
        raise RuntimeError("Ошибка при загрузке MCP инструментов:\n- " + "\n- ".join(msgs)) from e

    tool_names = [getattr(t, "name", "") for t in mcp_tools]
    logger.info("MCP tools loaded: %s", ", ".join([n for n in tool_names if n]) or "<empty>")

    if mcp_errors:
        logger.error("MCP load errors:\n%s", "\n\n".join(mcp_errors))

    # Если обязательные тулзы не загружены — не стартуем (иначе модель начнёт фантазировать).
    required = {"create_company_profile", "get_regions_codes", "get_okpd2_codes"}
    missing = sorted([r for r in required if r not in set(tool_names)])
    if missing:
        msg = (
            "Не загружены обязательные MCP инструменты: " + ", ".join(missing) + ".\n"
            "См. ошибки подключения выше (скорее всего один из MCP URL недоступен/не резолвится).\n"
            "Проверьте DB_MCP_URL / CODES_MCP_URL в окружении агента."
        )
        if mcp_errors:
            msg += "\n\nОшибки MCP:\n" + "\n\n".join(mcp_errors)
        raise RuntimeError(msg)

    # Prompt (как раньше)
    system_prompt = BASE_SYSTEM_PROMPT
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    ).partial(system_prompt=system_prompt)

    agent = create_tool_calling_agent(llm, mcp_tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=mcp_tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=20,
        return_intermediate_steps=True,
    )

    return agent_executor
