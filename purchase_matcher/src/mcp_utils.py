"""Утилиты для работы с MCP-серверами через MultiServerMCPClient."""
from __future__ import annotations

import asyncio
from typing import Dict, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool


def _normalize_mcp_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Пустой MCP URL")
    if raw.rstrip("/").endswith("/mcp"):
        return raw.rstrip("/")
    return raw.rstrip("/") + "/mcp"


def _build_client(mcp_urls: str | list[str] | None) -> Optional[MultiServerMCPClient]:
    if not mcp_urls:
        return None

    servers: Dict[str, dict] = {}
    iterable = mcp_urls if isinstance(mcp_urls, list) else str(mcp_urls).split(",")

    for idx, item in enumerate(iterable):
        item = (item or "").strip()
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
        servers[name] = {
            "transport": "streamable_http",
            "url": _normalize_mcp_url(url),
        }

    if not servers:
        return None
    return MultiServerMCPClient(servers)


async def load_mcp_tools_async(mcp_urls: str | list[str] | None) -> Dict[str, BaseTool]:
    """Загружает все инструменты MCP и возвращает словарь по имени инструмента."""
    client = _build_client(mcp_urls)
    if client is None:
        return {}
    tools = await client.get_tools()
    return {tool.name: tool for tool in tools}


def load_mcp_tools(mcp_urls: str | list[str] | None) -> Dict[str, BaseTool]:
    if not mcp_urls:
        return {}
    return asyncio.run(load_mcp_tools_async(mcp_urls))
