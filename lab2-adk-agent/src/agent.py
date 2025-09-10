from __future__ import annotations
import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import SseConnectionParams, McpToolset

llm_model = LiteLlm(
    model=os.getenv("LLM_MODEL"),
    api_base=os.getenv("LLM_API_BASE"),
    api_key=os.getenv("LLM_API_KEY")
)

worker_agent = Agent(
    model=llm_model,
    name=os.getenv('AGENT_NAME', 'Work Agent').replace(" ", '_'),
    description=os.getenv('AGENT_DESCRIPTION', 'This agent do work'),
    instruction=os.getenv("AGENT_SYSTEM_PROMPT"),
    tools=[McpToolset(
        connection_params=SseConnectionParams(
            url=url
        )
    ) for url in os.getenv("MCP_URL").split(',')],
)

root_agent = worker_agent
