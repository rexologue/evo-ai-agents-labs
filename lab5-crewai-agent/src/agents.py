"""Определение агентов для CrewAI crew."""
import os
from crewai import Agent
from crewai_tools import BaseTool
import httpx
import asyncio


class MCPTool(BaseTool):
    """CrewAI Tool для работы с MCP инструментами."""
    name: str
    description: str
    mcp_url: str
    tool_name: str
    
    def _run(self, input_text: str) -> str:
        """Синхронный вызов MCP инструмента."""
        async def async_call():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.mcp_url}/tools/{self.tool_name}/invoke",
                    json={"input": input_text},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()
                return str(result.get("content", result))
        
        return asyncio.run(async_call())


def get_mcp_tools(mcp_urls: str):
    """Получает список инструментов из MCP серверов."""
    tools = []
    
    if not mcp_urls:
        return tools
    
    # Для упрощения, создаем базовые инструменты
    for mcp_url in mcp_urls.split(','):
        mcp_url = mcp_url.strip()
        tools.append(MCPTool(
            name="loan_schedule_annuity",
            description="Расчет графика аннуитетного кредита",
            mcp_url=mcp_url,
            tool_name="loan_schedule_annuity"
        ))
        tools.append(MCPTool(
            name="loan_schedule_differential",
            description="Расчет графика дифференцированного кредита",
            mcp_url=mcp_url,
            tool_name="loan_schedule_differential"
        ))
        tools.append(MCPTool(
            name="deposit_schedule_compound",
            description="Расчет графика вклада с капитализацией",
            mcp_url=mcp_url,
            tool_name="deposit_schedule_compound"
        ))
    
    return tools


def create_crew_agents(mcp_urls: str = None):
    """Создает агентов для crew."""
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
    
    # Получаем инструменты
    tools = get_mcp_tools(mcp_urls) if mcp_urls else []
    
    # Системный промпт
    system_prompt = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        "Ты полезный AI-ассистент. Используй доступные инструменты для решения задач пользователя."
    )
    
    # Создаем агентов
    # Агент-координатор
    coordinator = Agent(
        role='Координатор',
        goal='Координировать работу команды и распределять задачи',
        backstory='Опытный координатор, который умеет эффективно распределять задачи между специалистами.',
        verbose=True,
        allow_delegation=True,
        llm=llm_call,
    )
    
    # Агент-исполнитель
    executor = Agent(
        role='Исполнитель',
        goal='Выполнять задачи используя доступные инструменты',
        backstory='Квалифицированный специалист, который умеет использовать инструменты для решения задач.',
        tools=tools,
        verbose=True,
        allow_delegation=False,
        llm=llm_call,
    )
    
    return [coordinator, executor]


