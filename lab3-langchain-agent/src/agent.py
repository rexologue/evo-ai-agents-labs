"""Определение LangChain агента с поддержкой MCP инструментов."""
import os
import asyncio
from typing import List, Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
import httpx


def create_mcp_tool(mcp_url: str, tool_name: str, tool_description: str) -> Tool:
    """Создает LangChain Tool из MCP инструмента."""
    def mcp_tool_func(input_text: str) -> str:
        """Вызывает MCP инструмент через SSE."""
        async def async_call():
            async with httpx.AsyncClient(timeout=30.0) as client:
                # MCP через SSE использует POST запросы
                response = await client.post(
                    f"{mcp_url}/tools/{tool_name}/invoke",
                    json={"input": input_text},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()
                return str(result.get("content", result))
        
        return asyncio.run(async_call())
    
    return Tool(
        name=tool_name,
        description=tool_description,
        func=mcp_tool_func
    )


def get_mcp_tools(mcp_urls: Optional[str]) -> List[Tool]:
    """Получает список инструментов из MCP серверов."""
    tools = []
    
    if not mcp_urls:
        return tools
    
    # Для упрощения, создаем базовые инструменты
    # В реальности нужно получать список инструментов через MCP протокол
    # Здесь используем примеры инструментов из lab1
    for mcp_url in mcp_urls.split(','):
        mcp_url = mcp_url.strip()
        # Примеры инструментов из finance MCP
        tools.append(create_mcp_tool(
            mcp_url,
            "loan_schedule_annuity",
            "Расчет графика аннуитетного кредита. Принимает сумму кредита, годовую ставку в процентах и срок в месяцах."
        ))
        tools.append(create_mcp_tool(
            mcp_url,
            "loan_schedule_differential",
            "Расчет графика дифференцированного кредита. Принимает сумму кредита, годовую ставку в процентах и срок в месяцах."
        ))
        tools.append(create_mcp_tool(
            mcp_url,
            "deposit_schedule_compound",
            "Расчет графика вклада с капитализацией. Принимает начальную сумму, годовую ставку в процентах, срок в месяцах и ежемесячные взносы."
        ))
    
    return tools


def create_langchain_agent(mcp_urls: Optional[str] = None):
    """Создает LangChain агента с инструментами."""
    
    # Создаем LLM через LiteLLM для унификации
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4"),
        base_url=os.getenv("LLM_API_BASE"),
        api_key=os.getenv("LLM_API_KEY"),
        temperature=0.7,
    )
    
    # Получаем инструменты из MCP
    tools = get_mcp_tools(mcp_urls)
    
    # Системный промпт
    system_prompt = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        "Ты полезный AI-ассистент. Используй доступные инструменты для решения задач пользователя."
    )
    
    # Создаем промпт для агента
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Создаем агента
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # Создаем executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=15,
    )
    
    return agent_executor


