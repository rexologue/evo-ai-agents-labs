"""Определение LangChain агента с поддержкой MCP инструментов и классификацией по ОКПД2."""

import asyncio
from typing import List, Optional, Dict

from langchain_core.tools import BaseTool, Tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_mcp_adapters.client import MultiServerMCPClient  # MCP <-> LangChain

from config import get_settings
from okpd2_index import OKPD2_INDEX

settings = get_settings()

# Поведенческий промпт, описывающий полную задачу агента
BASE_BEHAVIOR_PROMPT = """
Ты агент-профайлер компаний (CompanyProfiler).

Твоя задача:
1) На основе естественного описания от пользователя собрать СТРУКТУРИРОВАННЫЙ профиль компании.
2) При необходимости задавать уточняющие вопросы, чтобы заполнить все обязательные поля профиля и инструмента БД.
3) Обязательно классифицировать компанию по ОКПД2 (несколько наиболее подходящих кодов) с помощью инструмента `classify_okpd2`.
4) Сохранить профиль в БД через MCP-инструмент (обычно `create_company_profile`) и вернуть пользователю:
   • краткое резюме профиля;
   • список кодов ОКПД2;
   • ID созданного профиля из ответа инструмента.

Правила диалога:
- Спрашивай только то, чего не хватает для вызова инструмента сохранения профиля (см. схему его аргументов).
- Задавай вопросы блоками (например: сначала про базовое описание и отрасль, потом про регионы и бюджет).
- Если пользователь не знает точные цифры, можно зафиксировать диапазон или приблизительное значение.
- Не делай вызов инструмента сохранения, пока не собраны все обязательные поля.

Структура профиля, на которую ты ориентируешься:
- name — краткое имя/название компании или направления.
- description — краткое деловое описание (что делает компания, для кого, чем отличается).
- regions — список регионов, в которых компания реально готова работать.
- min_contract_price / max_contract_price — типичный диапазон стоимости одного контракта.
- industries — ключевые отрасли/сферы, с которыми работает компания.
- resources — ключевые ресурсы (команда, экспертиза, мощности, технологии и т.п.).
- risk_tolerance — отношение к риску: 'low', 'medium' или 'high'.
- okpd2_codes — список кодов ОКПД2 (code, title), которые ты подбираешь через `classify_okpd2`.

Перед вызовом инструмента сохранения профиля (например, `create_company_profile`):
- Убедись, что все поля, отмеченные как required в схеме инструмента, заполнены.
- В аргументах инструмента строго следуй JSON-схеме: не придумывай дополнительные поля.
"""


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
      - "finance=http://db-mcp:28001/mcp"
      - "finance=http://db-mcp:28001,gosplan=http://gosplan-mcp:28002/mcp"
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
            "transport": "streamable_http",  # streamable HTTP поверх FastMCP
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


def build_okpd2_tool() -> BaseTool:
    """Строит LangChain Tool для классификации по ОКПД2."""
    import json
    from rapidfuzz import process, fuzz

    def _classify_okpd2(text: str) -> str:
        """
        На вход принимает подробное описание компании.
        Возвращает JSON-массив объектов {code, title, score}, отсортированный по убыванию score.
        Score в диапазоне [0, 1].
        """
        query = (text or "").strip()
        if not query:
            return "[]"

        # каждый элемент: "код название"
        choices = [f"{item.code} {item.title}" for item in OKPD2_INDEX]

        matches = process.extract(
            query,
            choices,
            scorer=fuzz.WRatio,
            limit=5,
        )

        result = []
        for _, score, idx in matches:
            item = OKPD2_INDEX[idx]
            result.append(
                {
                    "code": item.code,
                    "title": item.title,
                    "score": round(float(score) / 100.0, 3),
                }
            )

        return json.dumps(result, ensure_ascii=False)

    return Tool(
        name="classify_okpd2",
        description=(
            "Подбирает наиболее подходящие коды ОКПД2 по текстовому описанию компании. "
            "Вход: подробное описание компании, её продуктов/услуг, отрасли и клиентов. "
            "Выход: JSON-массив объектов {code, title, score}, где score∈[0,1]. "
            "Используй этот инструмент перед сохранением профиля, чтобы заполнить поле okpd2_codes."
        ),
        func=_classify_okpd2,
    )


def create_langchain_agent(mcp_urls: Optional[str] = None) -> AgentExecutor:
    """Создает LangChain агента с MCP инструментами и классификатором ОКПД2."""
    # LLM
    llm = ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        temperature=0.2,
    )

    # Инструменты MCP (db-mcp и др.)
    mcp_tools = get_mcp_tools(mcp_urls)

    # Локальный инструмент для ОКПД2
    okpd2_tool = build_okpd2_tool()

    tools: List[BaseTool] = [*mcp_tools, okpd2_tool]

    # Системный промпт: env + поведенческий
    system_prompt = (settings.agent_sys_prompt or "").strip()
    if system_prompt:
        system_prompt = system_prompt + "\n\n" + BASE_BEHAVIOR_PROMPT
    else:
        system_prompt = BASE_BEHAVIOR_PROMPT

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_tools_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=20,
    )

    return agent_executor
