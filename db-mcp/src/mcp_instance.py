"""Единый экземпляр FastMCP для всего приложения."""

from fastmcp import FastMCP

mcp = FastMCP(
    "PostgreSQL-backed MCP for company profiles",
)
