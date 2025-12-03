"""Определение SmolAgents агента с поддержкой MCP инструментов."""
import os
from typing import Optional
from smolagents import CodeAgent, Tool
import httpx
import asyncio


def create_mcp_tool(mcp_url: str, tool_name: str, tool_description: str) -> Tool:
    """Создает SmolAgents Tool из MCP инструмента."""
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
        function=mcp_tool_func
    )


def get_mcp_tools(mcp_urls: Optional[str]):
    """Получает список инструментов из MCP серверов."""
    tools = []
    
    if not mcp_urls:
        return tools
    
    # Для упрощения, создаем базовые инструменты
    # В реальности нужно получать список инструментов через MCP протокол
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


def create_smolagents_agent(mcp_urls: Optional[str] = None):
    """Создает SmolAgents агента с инструментами."""
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
    
    # Получаем инструменты из MCP
    tools = get_mcp_tools(mcp_urls)
    
    # Системный промпт
    system_prompt = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        "Ты полезный AI-ассистент. Используй доступные инструменты для решения задач пользователя."
    )
    
    # Создаем агента
    agent = CodeAgent(
        tools=tools,
        llm=llm_call,
        system_prompt=system_prompt,
        max_iterations=15,
    )
    
    return agent


