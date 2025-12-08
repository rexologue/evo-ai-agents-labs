"""Единый экземпляр FastMCP для всего приложения."""

from fastmcp import FastMCP

mcp = FastMCP(
    "db-mcp",
    version="0.1.0",
    description="PostgreSQL-backed MCP for company profiles",
)
