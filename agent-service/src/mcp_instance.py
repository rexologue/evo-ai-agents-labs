"""Единый экземпляр FastMCP для agent-service."""

from fastmcp import FastMCP

mcp = FastMCP(
    "agent-service",
    version="0.1.0",
    description="Profile agent MCP server",
)
